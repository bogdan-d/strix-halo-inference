# 10: Maybe revisit the other two adapter routes for Qwen3.8 27B UD-Q4_K_XL

Status: ready-for-agent

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
