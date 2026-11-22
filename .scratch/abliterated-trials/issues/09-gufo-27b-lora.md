# 09: Add load-time LoRA support for Qwen3.8 27B in Gufo

Status: ready-for-agent

Gufo can now merge a llama.cpp GGUF LoRA at load for Qwen3.8 Flash-Next ([gufo-org/gufo#1320](https://github.com/gufo-org/gufo/pull/1320), ticket [08](08-gufo-native-lora.md)). Do the same for Gufo's Qwen3.8 27B provider (`qwen27-q4`, in the fork at `src/models/qwen/`), and prove it with an abliterated adapter. Neither the 27B weights nor an adapter for it are on this host, so the work starts with downloads.

## What is known

Checked on November 21 from the Gufo fork at `452c7c0d`, the Hugging Face API and GGUF headers read over HTTP range requests. Nothing was downloaded.

- **Not on this host:** `unsloth/Qwen3.8-27B-GGUF` is absent from `/home/bogdan/models`. The directory `Jackrong/Qwen3.8-27B-MTP-GGUF` exists but is empty. The Qwen3.6 27B folders there are a different model.
- **What Gufo serves:** `unsloth/Qwen3.8-27B-GGUF` pinned at `ce331efc48d5722b4b8041f72793e530eae18d9b`, as `Qwen3.8-27B-UD-Q4_K_XL.gguf` (16.45 GiB) or `Qwen3.8-27B-UD-Q8_K_XL.gguf` (29.30 GiB), with the drafter `z-lab/Qwen3.8-27B-DFlash2-GGUF` at `2d9571f8ce46e151f61c6499c99dee6079e1d610` (`Qwen3.8-27B-DFlash2-Q4_K_M.gguf`, 1.06 GiB) and an optional `mmproj-BF16.gguf` (0.87 GiB). The unsloth repository has moved past the pinned revision, so take sizes and hashes from the pinned revision, not from `main`.
- **Adapter:** [nchapman/Qwen3.8-27B-Heretic-LoRA](https://huggingface.co/nchapman/Qwen3.8-27B-Heretic-LoRA) at `dbbad6028a589c99a5316cc4c565c991c6f585c7`, file `Qwen3.8-27B-Heretic-LoRA.gguf`, 12,994,528 bytes, SHA-256 `0affed41898a25e8f196cd5461d9ec2d1590e3b905bdb86b1693a62e40936544`, Apache-2.0. It is the abliteration adapter named for this model in [gufo-org/gufo#1247](https://github.com/gufo-org/gufo/issues/1247). The repository also holds three `pareto/` variants; start with the main file.
- **Adapter contents:** `general.architecture=qwen35`, `adapter.type=lora`, `adapter.lora.alpha=3.0`, 128 pairs of rank 3 with **F16** factors, in layers 0 to 63: 48 × `blk.N.ssm_out.weight` (6144 × 5120), 16 × `blk.N.attn_output.weight` (6144 × 5120) and 64 × `blk.N.ffn_down.weight` (17408 × 5120). That is 7,717,519,360 weights.
- **Target formats in the base model, at the pinned revision:**

  | Quant | Formats of the 128 target tensors | Stock size of the targets | As Q8_0 |
  |---|---|---:|---:|
  | UD-Q8_K_XL | all Q8_0 | 7,820 MiB | 7,820 MiB |
  | UD-Q4_K_XL | Q5_K (70), IQ4_XS (21), Q6_K (28), IQ4_NL (4), Q4_K (3), Q8_0 (2) | 4,901 MiB | 7,820 MiB |

- **Gufo code:** tensors are bound in `src/models/qwen/weights.cpp` and uploaded from `src/models/qwen/hip/model_loader.cpp`. `src/models/qwen/continuation_identity.cpp:67` writes `adapters=none`. The provider declares only `--dflash-model`.

## What differs from the Flash-Next work

- **Factor type:** the existing reader accepts only F32 factors. This adapter is F16.
- **UD-Q8_K_XL is the direct case.** Every target is Q8_0, so the reviewed merge applies as is: dequantize, add the update in float32, encode Q8_0, same size and kernels.
- **UD-Q4_K_XL needs a design decision.** Its targets are low-bit K and IQ formats. The options are: store merged tensors as Q8_0 (about 2.9 GiB more device memory, and every kernel route for these three tensor kinds must accept Q8_0, as was done for 12 tensors in the IQ4_XS extension); re-encode in the source formats, which needs Q4_K, Q5_K, Q6_K and IQ4 encoders; or apply the update at inference as a low-rank side path, which leaves the base weights untouched but changes the kernels.
- **Shared code:** the adapter reader and Q8_0 encoder live in `src/models/qwen38_flash_next/lora.{hpp,cpp}`, private to that model. Decide whether 27B copies them or both models share one implementation, without changing the versioned extension API if that can be avoided.
- **Drafting:** 27B uses DFlash2, not MTP. Check which tensors the drafter borrows from the trunk and whether any of them is an adapter target.

## Tasks

1. **Download and pin.** Fetch into `/home/bogdan/models`, each from its pinned revision, with sizes and SHA-256 recorded in a manifest: the adapter, the DFlash2 drafter, and UD-Q8_K_XL. Add UD-Q4_K_XL when step 4 is taken. Confirm first that `/home` has room (about 31 GiB for the Q8 set, 48 GiB with Q4). Existing files are never overwritten.
2. **Baseline.** Run stock 27B UD-Q8_K_XL on the fork image and confirm readiness, a real generation and DFlash2 drafting before changing anything.
3. **Implement for UD-Q8_K_XL** in the Gufo fork, on a branch from `feat/flash-next-lora`: F16 factors, `--lora` and `--lora-scale` for the 27B provider, the upload hook, the cache identity, tests and docs, following the conventions of commit `452c7c0d`.
4. **Decide UD-Q4_K_XL.** Report the options above with measured memory and what each needs in the 27B kernels, recommend one, and wait for the user's choice before building it.
5. **Verify** in three tiers, as for Flash-Next: CPU unit tests; a real-weight comparison of every merged tensor against an independent offline merge of the same files; and a GPU run covering stock against adapter, drafting, disk-cache isolation across stock, adapter and a second scale, cancellation and a tool call. Run comparisons without a disk cache or from an empty one ([cache-restore ticket](../../gufo-cache-restore/issues/01-partial-restore-changes-greedy-output.md)).
6. **Review** the change independently before committing, then decide with the user whether to add it to the open pull request or open a second one.
7. **Launcher.** `bin/run.sh` serves only Flash-Next through Gufo today. Adding a 27B engine or profile is a separate decision for the user; record what it would need.

## Constraints

- Nothing is installed on the host. Build and test in the containers under `/var/mnt/xdata/code/strix-halo/gufo-build/`.
- One heavy GPU workload at a time; stop each server and confirm memory release.
- Weights stay in `/home/bogdan/models`, mounted read-only for inference.

## Comments

November 22: tasks 1, 2, 3, 5 and 6 are done for UD-Q8_K_XL; the change is uncommitted on local branch `feat/qwen27-lora` in the Gufo fork (from `452c7c0d`). Task 4 is reported below and waits for the user's choice. Scripts, logs and merged copies are under `/var/mnt/xdata/code/strix-halo/gufo-build/` (`qwen27/`, `logs/q27-*`).

- **Downloads:** adapter (GGUF and safetensors), DFlash2 drafter, UD-Q8_K_XL and UD-Q4_K_XL, each from its pinned revision and SHA-256 verified; manifest in `gufo-build/qwen27/models.tsv`.
- **Implementation:** the reader, Q8_0 encoder and cache identity moved to a shared library `src/families/qwen/lora/` that Flash-Next now uses too. Factors may be F32, F16 or BF16. The 27B loader overwrites the 128 targets in place after the stock upload, so no device memory is added. `--lora` and `--lora-scale` work on serve, bench, prompt and chat; the CPU path refuses an adapter.
- **Verification:** CPU tests pass. The production merge equals an independent Python merge for all 128 tensors (8,199,864,320 bytes) at scales 1 and 0.5. On the GPU, stock plus `--lora` gives the same greedy output as the offline-merged file loaded as a plain model, in AR and DFlash2. Disk-cache entries stay separate for stock, adapter and scale 0.5. Cancellation and a tool call work with the adapter.
- **Measured (balanced profile, one session, 32k context, DFlash2):** the merge adds about 2.2 s to the load and no device memory (38,363 MiB with and without). Stock refuses the lock-picking prompt and the adapter answers it. Draft acceptance was 34 %, 93 % and 30 % with the adapter against 39 %, 75 % and 39 % for stock.
- **Review:** the main agent and an independent reviewer read the change. Fixed afterwards: a target whose bytes another tensor shares is refused, a model opened from memory is refused with an adapter, and weight regions are released on every failure path.
- **Not exercised on this host:** the registered host-clone placement and the Windows deferred upload; only the direct device copy ran.
- **Finding:** in a llama.cpp qwen35 adapter, `ssm_out` `lora_a` columns follow llama.cpp's reordered value-head layout, which matches the base GGUF, so no permutation is needed when merging.

### Task 4: UD-Q4_K_XL options

The update is small against 4-bit steps: its RMS is 0.05 to 0.15 of a quantization step in the Q4 file's formats, against 0.16 to 0.30 in Q8_0 (`logs/q27-retention.log`).

| Option | Device memory (DFlash2) | AR decode | What it needs |
|---|---:|---:|---|
| Stock UD-Q4_K_XL, no adapter | 24,623 MiB | 12.2 tok/s | reference |
| Merged targets stored as Q8_0 | 27,547 MiB | 10.5 tok/s | loader lays out 128 larger tensors; no kernel change |
| Re-encode in the source formats | as stock | as stock | K and IQ encoders; adds rounding noise several times the update's size, or keeps only 7 to 25 % of it on the existing grid |
| Low-rank side path at inference | about 12 to 25 MiB more | not measured | new kernel work on decode, verification and prefill routes |
| UD-Q8_K_XL with the adapter | 38,363 MiB | 7.2 tok/s | done |

The Q8_0 row was measured with a Q4 copy whose targets were re-encoded offline (`qwen27/q4_q8_targets.py`), loaded as a plain model: it runs on the existing kernels, answers the lock-picking prompt, and with DFlash2 decodes 27, 53 and 23 tok/s on the three prompts against 32, 65 and 32 for stock Q4.

### Task 7: launcher

`bin/run.sh` still serves only Flash-Next through Gufo. A 27B profile would need the fork image, the weights and drafter in the model manifest, `--speculative dflash2 --dflash-model`, `--lora` for the adapter, and the usual tests. Not started.

November 22, later: the Flash-Next merge left the patched tensors' file pages mapped in the process, about 0.7 to 0.8 GiB of extra RSS with an adapter (reclaimable page cache, not a leak; device memory was unaffected). Fixed by releasing each target's mapped pages after its merge, uncommitted, in the Gufo fork (`src/models/qwen38_flash_next/kernels/rocm/device_model.cpp`) and in the IQ4_XS extension fork (`src/kernels/rocm/device_model.cpp`). Measured RSS at load, stock against adapter: Gufo fork 2,790 against 2,797 to 2,804 MiB (was 3,482 to 3,581); extension 2,744 against 2,752 MiB (was 3,436 to 3,554). Greedy outputs are unchanged in both. Both fixes were then committed and pushed as follow-ups to the open pull requests (`d77c890f` on `feat/flash-next-lora`, `d7794c4` on the extension's `feat/lora`), the fork image and the module were rebuilt, and `lora`, `iq4-xs-lora` and `iq4-xs` passed the usual checks ([update record](../../../docs/engine-updates.md#november-22-gufo-lora-loaders-release-the-pages-they-read)). The pin and doc changes in this repository are not committed. `feat/qwen27-lora` now sits on `d77c890f`.

November 22, decision: the user chose to store merged targets as Q8_0 for UD-Q4_K_XL. The other two routes, a low-rank side path at inference and an offline quantization of merged full-precision weights, are filed as ticket [10](10-gufo-27b-q4-adapter-routes.md).
