# 10: Maybe revisit the other two adapter routes for Qwen3.8 27B UD-Q4_K_XL

Status: resolved

**What to build:** Nothing yet. Ticket [09](09-gufo-27b-lora.md) applies the Heretic adapter to UD-Q4_K_XL by storing the 128 merged tensors as Q8_0, the route the user chose on November 22. That costs 2.9 GiB of device memory and about 14 % of AR decode speed against stock UD-Q4_K_XL (measured on an offline copy). Two other routes keep stock memory and speed. Revisit them if that cost matters, or if per-request adapter switching is wanted.

## Why merging into Q4 tensors was dropped

The adapter is made for the full-precision `Qwen/Qwen3.8-27B` and does not depend on a quantization. A merge has to store stock weight plus update in the tensor's format. The update's RMS is 0.05 to 0.15 of one quantization step in the Q4 file's formats (Q4_K, Q5_K, Q6_K, IQ4_XS, IQ4_NL), against 0.16 to 0.30 in Q8_0. Re-rounding on each tensor's existing grid keeps 7 to 25 % of it in the 4-bit formats; a full re-encode adds rounding noise several times its size (estimated from step sizes, not measured with a real encoder). Measurements: `/var/mnt/xdata/code/strix-halo/gufo-build/logs/q27-retention.log`, script `qwen27/retention.py` beside it.

## Route A: low-rank side path at inference

Leave the Q4 weights untouched and compute `W·x + scale · alpha / rank · B·(A·x)` whenever a patched matrix runs. This is how vLLM (`--enable-lora`) and llama.cpp (`--lora`) apply the same adapter, per its [model card](https://huggingface.co/nchapman/Qwen3.8-27B-Heretic-LoRA/tree/dbbad6028a589c99a5316cc4c565c991c6f585c7).

- **Gain:** exact update, stock Q4 memory plus 12 MiB (F16 factors) or 25 MiB (F32), no load-time merge, and a path to switching adapters per request.
- **Cost:** new GPU code in Gufo for three tensor kinds (`ssm_out`, `attn_output`, `ffn_down`) on three routes, checked against the fork at `452c7c0d`:
  - single-token decode (`src/models/qwen/hip/decode_step.cpp`, `LaunchGEMV`);
  - batched decode and speculative verification (`src/models/qwen/hip/batched_decode.cpp`, `LaunchProjection`);
  - prompt prefill (`src/models/qwen/hip/prefill_chunk.cpp`), where the projections are fused with residual writes, SSM gating and the SwiGLU activation.
- **Unknown:** the speed cost. The arithmetic is small, about 6.5 million extra multiply-adds per token, but a plain implementation adds 256 kernel launches per decoded token.
- **Also needs:** a cache identity that names the side path, since its numerics differ from a merge, and a check that DFlash2 drafting still verifies against the adapted target.

## Route B: quantize a merged full-precision model once, offline

Merge the adapter into the BF16 weights, then quantize to the UD-Q4_K_XL layout. The result is an ordinary Q4 file that runs on stock Gufo with stock memory and speed.

- **Inputs:** `unsloth/Qwen3.8-27B-GGUF` at `ce331efc48d5722b4b8041f72793e530eae18d9b` has `BF16/Qwen3.8-27B-BF16-00001-of-00002.gguf` and `-00002-of-00002.gguf` (54.7 GB together) and `imatrix_unsloth.gguf`. The per-tensor formats can be read from the published UD-Q4_K_XL file.
- **Cost:** the 54.7 GB download, a llama.cpp build in a container, reproducing Unsloth's per-tensor recipe (not published as a script; untested whether llama-quantize's per-tensor overrides cover it), and a 17.7 GB merged copy on disk per adapter and scale.
- **Trade-off:** no engine change and no load-time work, but it gives up serving stock files plus an adapter, which is why the Flash-Next profiles moved to merging at load.
- **Unknown:** whether the result matches the published UD-Q4_K_XL closely enough outside the 128 targets to count as the same model. Compare a no-adapter rebuild with the published file first.

## Before choosing

- Check whether upstream Gufo has gained runtime adapters since ([gufo-org/gufo#1247](https://github.com/gufo-org/gufo/issues/1247), [#1320](https://github.com/gufo-org/gufo/pull/1320)).
- Measure the Q8_0-storage route as built in ticket 09 on real work, and decide whether 2.9 GiB and the decode cost are worth removing.

## Comments

November 23, decision: the user chose Route A, the low-rank side path at inference, because the 14 % AR decode loss of the Q8_0 route is not acceptable. gufo-org/gufo#1323 is considered unfinished until then; the user prefers upstream to review #1320 (Flash-Next) on its own first. The reply on #1320 is drafted but not posted, and #1323 stays ready for review for now. The next step is a plan for the side path covering the decode, batched-decode/verification and prefill routes, plus the cache identity and DFlash2 checks listed above.

November 23, later: #1320 now carries the shared adapter library and both branches are rebased on upstream `e7e38411`. The reply on #1320 was posted and gufo-org/gufo#1323 is a draft until this route is tried. The launcher pins the fork image at `b7b34b90` ([update record](../../../docs/engine-updates.md#november-23-gufo-fork-image-on-the-rebased-lora-branches)).

## Route A plan (November 23)

Merged from two independent plans (main agent and Astra 6.2 xhigh). Develop from `d4a1f96e` (27B options, target enumeration, adapter validation); `b7b34b90`'s resized Q8_0 layout is dropped.

- **Device data:** the reader's widened factors as one model-owned FP32 allocation (24.75 MiB for Heretic), two optional descriptors per layer (attention-or-SSM output, FFN down) with pointers, dimensions, rank and the per-patch multiplier. Counted in resident bytes. Per-executor scratch of `max_batch × max_rank` floats, allocated before graph capture.
- **Arithmetic:** `y[row] += m · B·(A·x[row])` added to the projection's FP32 output before the residual. The reduction order for a row must not depend on the batch width, so single-token decode and verification stay bit-identical and greedy DFlash2 output equals AR output.
- **Decode and batched routes:** F32 inputs already exist (`ssm_scratch.out`, FFN activation); call sites in `decode_step.cpp` before the residual adds and in both layer loops of `batched_decode.cpp` (use the flattened token-row count). Decode is graph-captured, so the launches are baked in.
- **Prefill:** FP16 route reads the actual half activation and adds into the FP32 hidden after the fused residual, following the base projection's rows and final 256-row tile. Non-half attention has FP32 input. Where only Q8_1 is produced (row-split SSM epilogue, fused SwiGLU), add an optional FP32 store at the quantizer for patched layers (`d_ffn_act` exists), starting with the standalone SwiGLU quantizer.
- **Cache identity:** `CacheIdentity` takes the algorithm, default unchanged (`q8-requant-v1`); the side path uses a distinct value such as `low-rank-fp32-v1` with the adapter SHA-256 and scale bits.
- **DFlash2:** the drafter shares only the embedding and output head; the target applies the update before hidden taps, verification logits and replay after rejection.

| Stage | Deliverable and check | Main risk | Chance |
|---|---|---|---:|
| 1. Decode speed | Factors uploaded, single-token decode wired, interleaved warmed stock/adapter decode benchmark on the balanced profile. Gate: ≥95 % of same-day stock AR throughput, target ≥97 %. | Rank-3 reduction under-uses the GPU, or launch overhead (about 17 µs per extra launch fits the 5 % budget) | 75–80 % |
| 2. Loader, identity, CPU tests | Mode selection, descriptors, cleanup, resident accounting, cache identity; tests for mixed formats, ranks, factor types, scales | Changing the existing Q8 or Flash-Next identity | 95 % |
| 3. Batched decode, real-weight oracle | Both loops wired; independent gguf-py/NumPy FP64 reference of `m·B·(A·x)` for every pair at scales 1 and 0.5 (relative RMS ≤ 1e-5 per delta), crossed-scale control, bitwise equality of a row across scalar and batched kernels | An omitted or transposed update hidden in full outputs | 90–95 % |
| 4. Prefill | Both prefill families, a short Q8_1 chunk, 1,024 and 1,025 rows, hidden capture; prefill throughput short and long | A stale activation, a double-applied residual, rows outside the final tile | 65–85 % |
| 5. Serving acceptance | Exact greedy token IDs AR vs DFlash2, two concurrent sessions, stock vs adapter behaviour, scales 0/0.5/1, cache isolation, cancellation, tool call, final speed and memory | Harness assumes one session and compares rendered text | 90 % |

Decided by the user on November 23: when every target in the trunk is Q8_0 (UD-Q8_K_XL), keep the in-place merge from `d4a1f96e`; on a mixed trunk (UD-Q4_K_XL) use the side path for every target, including its Q8_0 ones. Speed gate: at most 5 % AR decode loss against same-day stock, 3 % as the target.

November 23, stage 1: passed. On local fork branch `exp/qwen27-lora-sidepath` (from `d4a1f96e`), single-token decode with the side path runs at 98.8 % of same-day stock in the implementer's interleaved `gufo bench` runs (12.12 against 12.26 tok/s medians) and about 99 % in the main agent's re-run (11.95 and 12.10 against 12.13). Device memory grows by 26 MiB (22,249 to 22,275 MiB at 32768 context). One 1024-thread block per row; 256 threads gave 96.6 %. The kernel matches an FP64 CPU computation to a relative RMS of about 1e-7 on three layers, and a row is bit-identical whatever the row count. UD-Q8_K_XL still merges. Stages 2–5 started.

November 23, stages 2–5: implemented on local fork branch `feat/qwen27-lora-sidepath` (`63f3d7d6` shared-library defaults and algorithm name, `f571909d` the side path; on `d4a1f96e`), not pushed. Implementer's measurements, UD-Q4_K_XL with Heretic, stock against side path: AR decode 12.37 against 12.18 tok/s (98.4 %), prefill 97.1 % (512 tokens, Q8_1 route) and 97.8 % (2,048 tokens, FP16 route), device memory +26 MiB. Greedy token IDs equal with and without DFlash2 (16 of 16); scale 0 gives stock token IDs; disk-cache isolation, cancellation and a tool call pass; UD-Q8_K_XL still merges with unchanged output. The kernel matches an FP64 NumPy reference for all 128 pairs. Open in review: the prefill-vs-decode check on the Q8_1 route (under 1,024 rows) cannot separate the update from that route's own noise at scale 0.5. Reviews by the main agent and Astra 6.2 xhigh are running.

November 23, review: the main agent re-ran the CPU tests, kernel checks and token-ID comparison on `f571909d` (all reproduced) and read the diff; Astra 6.2 xhigh reviewed independently. Fixed in `0d2e2359` (amended; `63f3d7d6` unchanged): patches bind to layers by tensor name instead of data pointer, a non-finite effective multiplier is refused at load, factor ownership survives a throwing `make_shared`, the prefill check is now exact per route (adapter minus stock equals `m·B·(A·x)` from the same-route input, with a control that must fail), rank 7 and 64 run through the GPU kernel check, and the harness script reports failed stages. Declined: adding the update before rather than after the fused residual on the FP16 prefill route (FP32 rounding order only, and it would cost prefill speed). Not covered exactly: `ssm_out` and `attn_output` on the FP16 prefill route (same kernel and input pattern as the checked `ffn_down`). After the fixes: DFlash2 = AR 16/16, scale 0 = stock, AR decode 98.4 %, prefill 97.2 % (512) and 97.6 % (2,048), `nix flake check` 211/211. Not pushed; replacing `b7b34b90` in #1323 and moving the launcher pin wait for the user.

November 23, side path on UD-Q8_K_XL (measurement, asked by the user to decide whether the in-place merge can go): measured on `0d2e2359` with a local switch that forces the side path when every target is Q8_0 (`gufo-build/qwen27/q8-sidepath-experiment.patch`, not committed; the fork tree is clean again). Logs: `gufo-build/logs/q8sp-*`, `sp-q8-*`.

- **Correctness:** the exact checks pass on UD-Q8_K_XL. Decode and verification are bit-identical to single-token decode, all 128 pairs match the FP64 reference at scales 1 and 0.5, and the crossed-scale controls fail. The exact prefill check passes for `ssm_out`, `attn_output` and `ffn_down` at 64, 1,024 and 1,025 rows, since an all-Q8_0 FFN keeps the Q8_1 prefill route at every length (`UseQwen27bFp16Prefill` needs a low-bit FFN). The committed oracle assumes the FP16 route from 1,024 rows on and has to pick the route the same way before UD-Q8_K_XL can use the side path; its control caught the wrong read. Greedy token IDs equal between AR and DFlash2 on four prompts, and between the merge and the side path on three of four (the lock-picking answer diverges after the same opening).
- **Speed, interleaved `gufo bench` (stock, merge, side, side, merge, stock; balanced profile):** tg256 7.21 / 7.19 / 7.07 tok/s (side path 98.3 % of the merge), pp512 458 / 458 / 445 (97.1 %), pp2048 447 / 447 / 431 (96.6 %). The side path also turns off the Q8_1 prefill fusions for patched layers (dual-projection SwiGLU epilogue, SSM epilogue), which a Q8 trunk uses in every layer.
- **Speed, `gufo prompt` (two repetitions, merge against side):** AR 99.0–99.3 % on short prompts and 98.8 % on the 2k prompt; DFlash2 99.2 % and 99.3 % on two short prompts and 97.7 % on the 2k prompt (the third short prompt generates different tokens, so it is not comparable).
- **Load and memory:** load 1.8 s against 3.75 s with the merge (stock 1.8 s); device memory +26 MiB.

November 23, decision: the user keeps the in-place merge for all-Q8_0 trunks for now. The #1323 description should ask the maintainers whether they prefer one route (side path everywhere) or the current split, with the measurements above.

November 23, published: on the user's word, `feat/qwen27-lora` of bogdan-d/gufo was force-pushed from `b7b34b90` to `18503d9c` (`0d2e2359` with the 27B `--lora` help text corrected to "applied to the weights at load"), and gufo-org/gufo#1323 was retitled "feat(qwen27b): apply llama.cpp GGUF LoRA adapters at load", given the new description (asking the maintainers about one route) and marked ready for review. `nix flake check` passes on `18503d9c` (211 of 211), as do `check-format.py`, `check-extension-api.py` (0.3.40), `check-extension-isolation.py`, `check-docs.py` and `generate-infrastructure.py --check`. Upstream CI waits for a maintainer to approve the workflows. The launcher still pins `b7b34b90`, kept locally as tag `pinned-b7b34b90` in the fork checkout.

November 23, closing: Route A is deployed. `config/pins.env` pins the fork at `18503d9c` (image `sha256:1de9f539…05c6`), and `27b-heretic` and `lora` passed the launcher checks ([update record](../../../docs/engine-updates.md#november-23-gufo-27b-adapter-on-the-side-path)). Route B is not needed. Open upstream: the maintainers' answer on one route for the Q8 target in #1323.
