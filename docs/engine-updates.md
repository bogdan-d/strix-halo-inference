# Engine updates

## October 27 update

`bin/update.sh` pulled all three new images by digest and atomically updated their image and version pins. Model revisions, live Pi files and host settings remain unchanged. The release notes were printed by the updater and are publisher claims; the [local checks](#october-27-local-checks) follow.

| Engine | Previous | Current | Current image digest |
|---|---|---|---|
| Halogen | 0.18.14 | 0.18.17 | `sha256:e30d6bf9a325d75fb4904c108745df7d77dc8e25ae3b2ce9b9007e55d70757d7` |
| Gufo | 0.23.0 | 0.25.0 | `sha256:27552f26358eb6e245d8f8d060ff91793a34df0db8af708265e024abe79cba44` |
| Strixite | 0.4.0 | 0.5.0 | `sha256:f0d3211f05c65036673d00bcf9daa69e83fe7ea12018c9b4810cd57ba7568293` |

The images advertise revisions Halogen `8a87b980bf0d`, Gufo `16e8ed477710914481d65702acc1e67a86aede32` and Strixite `b175d27`; none was compared with public source.

### What changed upstream

- **Halogen 0.18.15** turns on the reply-end keep (`HALOGEN_FORK_MAP=auto`) and short NPU requests between a long NPU job's steps (`HALOGEN_NPU_SPLICE`) by default. It adds an answer guard that keeps long answers from ending inside a code block or on a heading (`HALOGEN_ANSWER_GUARD`), an out-of-memory score of 500 for its processes, a startup count of NPU model host memory and a 4 GiB host-memory floor for the NPU engine. A client that leaves while queued is no longer prefilled (#204), a speech request the NPU cannot fit no longer stops every NPU model, and `/detokenize` no longer stalls the server. **0.18.16** turns the automatic keep off by default again after a stall of up to ten minutes (#207) and a fault in sliding a conversation aside (#208). **0.18.17** stops a full KV pool from writing one conversation's turn over rows another kept, which with any keep in use could answer with another conversation's turn (#208), stops a resumed conversation waiting on its own kept reply (#207), accepts Claude Code's `tool_reference` blocks on `/v1/messages`, parses tool-call markup inside string arguments as written and reports input modalities on `/v1/models`. The Flash checkpoints are unchanged.
- **Gufo 0.24.0** accepts image inputs for embeddings and repeated `--served-model-name`, accepts neutral llama.cpp sampler fields and runs EmbeddingGemma 2 attention on matrix cores. **0.25.0** bounds Qwen image resolution for `detail: low`, truncates over-length embedding inputs on request, batches concurrent embeddings and fills Qwen's device-resident weights from the shard file (#794). A Qwen cache-boundary change was added and reverted in the same release. None mentions a cache format change.
- **Strixite 0.5.0** serves several conversations at once (`--total-slots`, default 2) with batched decode, maps K/V pages as conversations grow and never releases them before restart, and states 10 to 12% faster prefill and flat to 4% faster decode. It adds `--chunk-shared` and `--log-level` and states that prompt-cache entries from 0.4 stay valid.

### Launch and model changes

- **Strixite slots.** The launcher now passes `--total-slots 1`, keeping one conversation at a time as on 0.4.0 and as Halogen's `HALOGEN_KV_SLOTS=1` and Gufo's `--sessions 1`. `env SLOTS=2`, up to 8, changes it per start. `tests/run.py` checks the default, the override and the refusal of values outside 1 to 8.
- **Halogen keep.** The launcher still sets `HALOGEN_FORK=1` and `HALOGEN_FORK_MAP=auto`, so 0.18.15's and 0.18.16's default changes do not apply here, and 0.18.17's two keep fixes do. The log confirms at most four automatic keeps. The answer guard and NPU splice keep their new upstream defaults.
- **NPU models.** `bin/npu-manifest.sh` reran against the 0.18.17 image; `config/npu-files.tsv` is unchanged. The fabric-clock script at `v0.18.17` is byte-identical to the installed one.
- **Dashboard.** All allowlisted metric names are still exported. Strixite adds `strix_slots`, `strix_verify_batches_total` and `strix_verify_batch_runs_total`, which the allowlist drops.

### Cache compatibility

- **Halogen** 0.18.17 opened new cache directories. 0.18.14's, about 0.2 GiB, remain on disk.
- **Gufo** cache reuse across the upgrade was not checked.
- **Strixite** started with an empty cache directory, so the stated 0.4 compatibility was not exercised.

### October 27 local checks

Each engine was started alone at native 262144 context with MTP on, then stopped. MemAvailable was 108 GiB before the first start. After each stop it was 114 to 115 GiB, Unevictable at most 0.3 MiB and kernel GTT about 1.6 GiB, and the fabric clock was back on `auto`.

| Check | Halogen 0.18.17 | Gufo 0.25.0 | Strixite 0.5.0 |
|---|---|---|---|
| Ready and a chat generation | Pass | Pass | Pass |
| `tests/live.py` or `tests/strixite_live.py` | Pass, 4 fragments | Pass, 4 fragments | Pass, 22 fragments, release 0.252 s |
| Allowlisted names on `/metrics` | 31 of 31 | 15 of 15 | 33 of 33 |
| Startup allocation | 78.3 GiB | 89.09 GiB on the GPU | 79.3 GiB of GPU buffers |

- **Halogen NPU.** Halogen started with `qwen3-tts-1.7b-customvoice`, `decider-0.8b` and `d3-lite`, checked their files against the image's record and stated up to about 12.2 GiB of host memory for them, with no warning that the host could not hold them. The 1.7B spoke 7.7 s of 24 kHz audio with `instructions` in 7.0 s. A `decider-0.8b` choice through `/v1/chat/completions` took 0.88 s alone and 0.11 s while a 13 s speech request ran, so the splice let it in. It routed a cracked phone screen to `technical`, not `repairs`; the prompt differed from October 24's. A decision without a question in the system message or schema description gets a 400.
- **Strixite slots.** With `SLOTS=2` the server reported `strix_slots 2` and 80.2 GiB of GPU buffers, 0.9 GiB more than one slot, and MemAvailable after loading fell from 27.1 to 26.2 GiB. Two concurrent requests both completed in two batched verify runs.
- **Host memory.** Halogen warned that 14 to 17 GiB of host RAM was in use before it started and that only 237 to 274 contiguous 2 MiB blocks were free. Startup took about 28 s and the checks were unaffected.
- **Gufo** still logs `option_ignored` for `--cache-disk-staging-bytes`.

Not exercised: Strixite image input; Pi sessions on the new versions; prompt-cache restoration across the upgrade; Prometheus scrapes and the rendered dashboard, as monitoring was stopped; Halogen's answer guard reaching its case, the keep under a full KV pool and the out-of-memory path; Gufo's embedding changes; two Strixite slots at depth; prefill or decode benchmarks.

Sources: [Halogen changelog at v0.18.17](https://github.com/peonist-ai/halogen-flash-server/blob/v0.18.17/CHANGELOG.md), [Gufo 0.24.0](https://github.com/gufo-org/gufo/releases/tag/v0.24.0) and [0.25.0](https://github.com/gufo-org/gufo/releases/tag/v0.25.0), [Strixite 0.5.0](https://github.com/shawnshekari/strixite/releases/tag/v0.5.0).

## October 24 update

`bin/update.sh` pulled the new Halogen and Gufo images by digest and atomically updated their image and version pins. Strixite `latest` still resolves to the pinned 0.4.0 digest. Model revisions, launch settings, live Pi files and host settings remain unchanged. The release notes were printed by the updater and are publisher claims; the [local checks](#october-24-local-checks) follow.

| Engine | Previous | Current | Current image digest |
|---|---|---|---|
| Halogen | 0.18.13 | 0.18.14 | `sha256:e0c1d1b48e07c8acdd204fbdbafbb421a395a73cf704271845a1846ad1fd767f` |
| Gufo | 0.20.0 | 0.23.0 | `sha256:ec8c3f0bf06100304f5105590cfe98d62bf21ff133e8c2dea95955eb4028ddb2` |
| Strixite | 0.4.0 | 0.4.0 | `sha256:34c7fdd7253456aa39920f7bf074b87e08ab8663c8c6da5bac1f4a7813ebf191` |

The images advertise revisions Halogen `9a80df1a2e68` and Gufo `1fafd5ad633a2934d32a2c227aa8951fa5ab22bf`; neither was compared with public source.

### What changed upstream

- **Halogen 0.18.14** adds text to speech on the NPU with Qwen3-TTS-12Hz CustomVoice 0.6B and 1.7B on `/v1/audio/speech`; other NPU requests wait while one speaks. When the prompt cache lowered a request's `max_tokens`, the answer can now grow into free or idle cached memory (`HALOGEN_POOL_GROW`, on by default). Opt-in `HALOGEN_NPU_SPLICE=1` runs short NPU requests between a long one's steps. Generation is stated to be a little faster, the Flash checkpoints are unchanged and temperature 0 output is byte-identical to 0.18.13. The `decider-0.8b`, `d3-lite` and `d3-nano` sets were republished.
- **Gufo 0.21.0** adds opt-in YaRN context extension for qwen-flash and cheaper Flash-Next sampled decoding. **0.22.0** frees RAM before writing oversized cache checkpoints to disk, gives each HIP stream its own qfn_mmq scratch arena, fixes the BF16 indexer sum order and accepts standard image `detail` values. **0.23.0** serves EmbeddingGemma 2 on `/v1/embeddings`, maps weights through a new file layer and lets lone or constrained greedy requests use the small MTP draft head. None mentions a cache format change.

### Launch and model changes

- **No launcher change.** The launcher sets neither `HALOGEN_POOL_GROW` nor `HALOGEN_NPU_SPLICE`, keeping upstream defaults. Gufo's YaRN and embedding features are unused.
- **NPU models.** `bin/npu-manifest.sh` reran against the 0.18.14 image, dropping `d3-nano` and adding `qwen3-tts-0.6b-customvoice` and `qwen3-tts-1.7b-customvoice`, 26 files each. The `d3-lite`, `d3-nano` and `decider-0.8b` directories, 8.0 GiB, were deleted, then `bin/models.sh download npu` fetched and verified `d3-lite`, `decider-0.8b` and both speech models, 15.7 GiB together. The fabric-clock script at `v0.18.14` is byte-identical to the installed one.
- **Fabric-clock sudoers rule.** The rule now names the script without arguments, so `status` also runs without a password. The script accepts only `hold`, `release` and `status`.
- **Dashboard.** Neither engine exports a new metric name, so the allowlists and panels are unchanged.

### Cache compatibility

- **Halogen** 0.18.14 opened new cache directories. 0.18.13's held only its fingerprint and was deleted.
- **Gufo** cache reuse across the upgrade was not checked.

### October 24 local checks

Each engine was started alone at native 262144 context with MTP on, then stopped. After each stop MemAvailable was about 115 GiB and Unevictable 0.1 MiB, and the fabric clock was back on `auto`.

| Check | Halogen 0.18.14 | Gufo 0.23.0 |
|---|---|---|
| Ready and a chat generation | Pass | Pass |
| `tests/live.py` | Not run | Pass |
| Allowlisted names on `/metrics` | 31 of 31 | 15 of 15 |

- **NPU.** Halogen started with `qwen3-tts-1.7b-customvoice`, `decider-0.8b` and `d3-lite`, then again with `qwen3-tts-0.6b-customvoice` alone, and checked their files against the image's record. Both deciders routed a cracked-screen question to `repairs`, in 0.64 s and 0.36 s. The 1.7B spoke 9.4 s of 24 kHz audio with `instructions` in 8.6 s and streamed 3.0 s of `pcm` in 2.8 s; the 0.6B spoke 9.8 s in 6.5 s and refused `instructions` with a 400, as documented.
- **Host memory fragmentation.** Halogen warned at start that the host had only 327 contiguous 2 MiB blocks free (654 MiB). Start-up and the checks were unaffected.
- **Gufo** still logs `option_ignored` for `--cache-disk-staging-bytes`. Its readiness route is `/ready` on port 8080; a check polling Halogen's port mistook a healthy start for a hang.

Not exercised: Strixite, already current; Prometheus scrapes and the rendered dashboard, as monitoring was stopped; Pi sessions on the new versions; `HALOGEN_POOL_GROW` reaching its case; `HALOGEN_NPU_SPLICE`; speech beside a streaming guard; Gufo YaRN and embeddings; prefill or decode benchmarks.

### Image cleanup

The superseded Halogen 0.18.13 and Gufo 0.20.0 images were removed by ID without force. No container used them. Podman's image store fell from 18.86 GB to 15.34 GB. Rolling back requires pulling the previous digests in the October 21 table again.

Sources: [Halogen changelog at v0.18.14](https://github.com/peonist-ai/halogen-flash-server/blob/v0.18.14/CHANGELOG.md), [Halogen NPU documentation at v0.18.14](https://github.com/peonist-ai/halogen-flash-server/blob/v0.18.14/docs/NPU.md#text-to-speech), [Gufo 0.21.0](https://github.com/gufo-org/gufo/releases/tag/v0.21.0), [0.22.0](https://github.com/gufo-org/gufo/releases/tag/v0.22.0) and [0.23.0](https://github.com/gufo-org/gufo/releases/tag/v0.23.0).

## October 21 update

`bin/update.sh` pulled the new Halogen and Gufo images by digest and atomically updated their image and version pins. Strixite `latest` still resolves to the pinned 0.4.0 digest. Model revisions, launch settings, live Pi files and host settings remain unchanged. The release notes were printed by the updater and are publisher claims; the [local checks](#october-21-local-checks) follow.

| Engine | Previous | Current | Current image digest |
|---|---|---|---|
| Halogen | 0.18.11 | 0.18.13 | `sha256:2e98dc53ed4a43b5600b11a80852eedfa573f4ffc3f10c64da01245f2a3217fc` |
| Gufo | 0.18.0 | 0.20.0 | `sha256:7d634b171e67dbe4377655b514aa4828dd36e137d187804e11a049bacd8bfd07` |
| Strixite | 0.4.0 | 0.4.0 | `sha256:34c7fdd7253456aa39920f7bf074b87e08ab8663c8c6da5bac1f4a7813ebf191` |

The images advertise revisions Halogen `a00875cbb6d1` and Gufo `0c03748a271eab895befc0d2343aa50ca4b6d836`; neither was compared with public source.

### What changed upstream

- **Halogen 0.18.12** states faster prefill on both checkpoints, cheaper multi-draft verification and read-ahead on hosts with the IOMMU off. It adds `/v1/images/edits` with up to four pictures, the `halogen:gpu_queues_evicted_seconds_total` metric and `evicted_ms` on each request log line, and copies prompt-cache data through a pinned staging buffer (`HALOGEN_CACHE_STAGE=2`, default), which upstream says halves the time lost when the driver evicts GPU queues.
- **Halogen 0.18.13** turns on `HALOGEN_ADMIT_SPLICE_MS=500`, so streaming replies keep moving while a long prompt is read in, and `HALOGEN_ADMIT_NEST=1`, so a request of up to 1,024 new tokens starts during another request's long prompt. Nesting holds about 0.33 GiB more pinned host memory and 32 MiB of GPU memory from start-up. An NPU fault now answers 503 and restarts the NPU engine, up to `HALOGEN_NPU_RESTARTS` times (default 3), instead of refusing later requests or stopping the container. Both releases state the Flash checkpoints are unchanged and temperature 0 output is byte-identical to the previous release.
- **Gufo 0.19.0** adds `/props` with model, build, context, sessions and vision, lets sampled requests use the small MTP draft head on multi-session servers and fixes the q8_1 block sum in qwen-flash (#667). **0.20.0** adds Qwen 27B AR and DFlash2 cache continuation, answers `Expect: 100-continue` before reading the body, no longer reports whitespace between parallel tool calls as content and speeds up cache lookups and Flash-Next projections. Neither mentions a cache format change.

### Launch and model changes

- **No launcher change.** The admission defaults suit this launcher's single slot and need no setting; `HALOGEN_ADMIT_SPLICE_MS=0` and `HALOGEN_ADMIT_NEST=0` would restore 0.18.11's behavior. Gufo's sampled MTP change applies to multi-session servers; this launcher runs one session.
- **NPU model sets republished.** `bin/npu-manifest.sh` reran against the 0.18.13 image with the same seven models. 103 files changed contents at unchanged paths, 4 were added (`consts.hnpb` files for `d3-lite`, `d3-nano`, `embeddinggemma-2` and `wemm-embedding-4b`) and 27 are unchanged. The 103 superseded files, 1.7 GB, were deleted after each matched its previous SHA-256, then `bin/models.sh download npu` fetched and verified the new ones. `HALOGEN_DOWNLOAD` stays unset. The fabric-clock script at `v0.18.13` is byte-identical to the installed one.
- **Dashboard.** `halogen:gpu_queues_evicted_seconds_total` joined the Halogen allowlist, with a stall-share chart and a since-start total; see [Halogen monitoring](halogen-monitoring.md#what-each-measurement-means). The other new or still-excluded Halogen names, including `halogen:build_info`, stay out. Gufo exports no new metric names.

### Cache compatibility

- **Halogen** 0.18.13 opened a new cache directory. 0.18.11's, 2.3 GiB, was then deleted with the engine stopped.
- **Gufo** cache reuse across the upgrade was not checked.

### October 21 local checks

Each engine was started alone at native 262144 context with MTP on, then stopped. After Halogen stopped, MemAvailable was 115 GiB and Unevictable 0.1 GiB with the fabric clock released; after Gufo stopped, MemAvailable was 116 GiB and GTT 1.5 GiB with monitoring running.

| Check | Halogen 0.18.13 | Gufo 0.20.0 |
|---|---|---|
| Ready and `smoke` | Pass | Pass |
| `tests/live.py` | Pass | Pass |
| Allowlisted metrics stored by Prometheus | 31 of 31 | 15 of 15 |

- **GPU queue stalls.** The new counter read 30.9 s at the first scrape after start-up and 36.0 s after the live tests, so this host does evict the engine's GPU queues, mostly while loading.
- **NPU.** Halogen started with `decider-0.8b`, `embeddinggemma-2` and `qwen3guard-stream-0.6b`, checked their republished files and that of their `qwen3-embedding-0.6b` devices against the image's record and held and released the fabric clock. A two-input `embeddinggemma-2` request returned 768-dimension vectors in 0.25 s.
- **Gufo** still logs `option_ignored` for `--cache-disk-staging-bytes`. `/props` reported `0.20.0 (0c03748)`, one slot, 262144 context and no vision.

Not exercised: Strixite, already current; Pi sessions on the new versions; concurrent requests that would use splicing and nesting; the NPU restart path; multi-picture image edits; a decider request; the rendered dashboard; prefill or decode benchmarks.

### Image cleanup

The superseded Halogen 0.18.11 and Gufo 0.18.0 images were removed by ID without force. No container used them. Podman's image store fell from 16.38 GB to 12.86 GB, as the new images share most layers. Rolling back requires pulling the previous digests in the October 19 table again.

Sources: [Halogen changelog at v0.18.13](https://github.com/peonist-ai/halogen-flash-server/blob/v0.18.13/CHANGELOG.md), [Gufo 0.19.0](https://github.com/gufo-org/gufo/releases/tag/v0.19.0) and [0.20.0](https://github.com/gufo-org/gufo/releases/tag/v0.20.0), [Gufo server documentation at v0.20.0](https://github.com/gufo-org/gufo/blob/v0.20.0/docs/SERVER.md).

## October 19 update

`bin/update.sh` pulled all three new images by digest and atomically updated their image and version pins. The Strixite model revision moved to add its vision files. Halogen and Gufo model revisions and host settings remain unchanged. In the live Pi `models.json`, only the Strixite model's `input` changed, to text and image, with a backup beside it. The release notes were printed by the updater and are publisher claims; the [local checks](#october-19-local-checks) follow.

| Engine | Previous | Current | Current image digest |
|---|---|---|---|
| Halogen | 0.18.3 | 0.18.11 | `sha256:a5797467d2bff173e0c661d9700292bd55eac305faff68c86261ae35385ad6ad` |
| Gufo | 0.15.0 | 0.18.0 | `sha256:4d784ef0043efe8ca07b8e7d519903a14345b068be2b4762c4896eb449704e81` |
| Strixite | 0.2.4 | 0.4.0 | `sha256:34c7fdd7253456aa39920f7bf074b87e08ab8663c8c6da5bac1f4a7813ebf191` |

The images advertise revisions Halogen `44d9515841f5`, Gufo `6c682a2b79109591bc57b1b951f1a2413a549723` and Strixite `62ef009`; none was compared with public source.

### Launch changes

- **8-bit KV cache by default.** Halogen gets `HALOGEN_KV8=1` (new in 0.18.9, opt-in upstream) and Strixite `--kv-cache q8` (its own default since 0.4.0). `env KV8=off` selects the 16-bit cache on both. Halogen's notes state perplexity moved by -0.3% to +0.5%, planted-fact retrieval at 128k and 250k matched, and decode is 0.2 to 1.9% slower; with drafting on, greedy text can differ from the 16-bit cache's. It cannot be combined with `HALOGEN_COMPOSABLE_CONTEXT=1`, which the launcher does not set.
- **Strixite images on by default.** The launcher passes `--vision on`; `env VISION=off` turns it off. `STRIXITE_REVISION` moved from `e0be897` to `b64f3a6`, which adds `vision.strixw` (898,331,648 bytes) and `Qwen3.8-Flash-Next/preprocessor_config.json`. The hashes of the six existing files are unchanged. The Strixite Pi profile now lists `image` input.
- **NPU models recorded.** `bin/npu-manifest.sh` reran against the 0.18.11 image. The five existing models' records are unchanged, and `d3-lite` and `d3-nano` (vLLM Semantic Router's Decision 3.0 models, 21 files each, 5.9 GB together) were added and downloaded. Neither is in the dashboard's NPU set; their use is undecided.
- **Not adopted.** Halogen's vision tower and Gufo's projector remain undownloaded. Halogen's grammar drafter, MTP gate, sampled-depth and cache-eviction changes are defaults and need no launcher setting. The `UD-Q4_K_XL` concurrency issue Halogen lists affects GGUF files on Halogen only; this launcher gives Halogen its native checkpoint and Gufo one slot. The fabric-clock script at `v0.18.11` is byte-identical to the installed one.

### Cache compatibility

- **Halogen** 0.18.4 changed the prompt computation order, so disk entries from 0.18.3 are not reused. 0.18.11 opened a new cache directory; four older configurations' directories, 34.0 GiB, were left in place. `HALOGEN_CACHE_PRUNE_OLD=1` would remove them at the next start.
- **Strixite** 0.4.0 dropped its 0.2.4 prompt-cache entries at startup, logging one `prompt cache: dropping` line each, because their fingerprint lacks `kv8`.
- **Gufo** 0.18.0 notes mention no cache format change. Reuse across the upgrade was not checked.

### October 19 local checks

Each engine was started alone at native 262144 context with MTP on, then stopped; afterward MemAvailable returned to about 119 GiB and GTT to 0.7 GiB.

| Check | Halogen 0.18.11 | Gufo 0.18.0 | Strixite 0.4.0 |
|---|---|---|---|
| Ready and `smoke` | Pass | Pass | Pass |
| `tests/live.py` or `tests/strixite_live.py` | Pass | Pass | Pass, disconnect release 0.253 s |
| Allowlisted metrics still exported | 30 of 30 | 14 of 14 | 33 of 33 |
| Image request | Not enabled | Not enabled | Pass: read a 640x200 card in 0.53 s, 147 prompt tokens, answering `Strix 4217` for `STRIX 4217` |

- **Halogen memory.** With the 8-bit cache, startup reported a 4.1 GiB KV pool and 78.3 GiB in all, against 7.2 and 81.4 GiB on 0.18.3 with the 16-bit cache, leaving 39.9 GiB of host memory instead of 30.6. The template check still reports 6 of 6 turn shapes and the model's own reply in 4.
- **Strixite memory.** 83.3 GiB of GPU buffers and 31.4 GiB MemAvailable after loading with vision on and the 8-bit cache, against 84.6 and 29.3 GiB on 0.2.3.
- **Gufo** still logs `option_ignored` for `--cache-disk-staging-bytes`, as on 0.15.0.
- **NPU.** Halogen started with `decider-0.8b`, `embeddinggemma-2`, `qwen3guard-stream-0.6b`, `d3-lite` and `d3-nano`, checked all their files and held and released the fabric clock; Unevictable fell back to 0.1 GiB after stop. A `/v1/systemone` choice from `d3-lite` took 0.66 s on its first call but routed a double-charge complaint to `technical` over `billing`, 0.47 against 0.45. `d3-nano` named a solid red picture red at 0.999 in 1.02 s.

Not exercised: Pi sessions on the new versions, images through Pi, larger or multi-image Strixite requests, `VISION=off` and `KV8=off` starts, long-context quality with the 8-bit caches, prefill or decode benchmarks, Halogen's new concurrent-request drafting and dashboard rendering.

### Image cleanup

The superseded Halogen 0.18.3, Gufo 0.15.0 and Strixite 0.2.4 images were removed by ID without force. No containers existed. Podman's image store fell from 21.28 GB to 12.25 GB. Rolling back requires pulling the previous digests in the October 14 table again.

Sources: [Halogen changelog at v0.18.11](https://github.com/peonist-ai/halogen-flash-server/blob/v0.18.11/CHANGELOG.md), [Halogen NPU guide](https://github.com/peonist-ai/halogen-flash-server/blob/v0.18.11/docs/NPU.md), [Gufo releases 0.15.1 to 0.18.0](https://github.com/gufo-org/gufo/releases), [Strixite 0.3.0](https://github.com/shawnshekari/strixite/releases/tag/v0.3.0), [0.3.1](https://github.com/shawnshekari/strixite/releases/tag/v0.3.1) and [0.4.0](https://github.com/shawnshekari/strixite/releases/tag/v0.4.0).

## October 14 update

`bin/update.sh` pulled the new Halogen and Gufo images by digest and atomically updated their image and version pins. Strixite `latest` still resolves to the pinned 0.2.4 digest. Model revisions, weight files, launch settings, live Pi files and host settings remain unchanged. The updater printed only the selected releases' notes during this run, so the Halogen 0.18.2 and Gufo 0.14.0 notes below were read from the publishers separately. The updater now prints the notes of every stable release after the pin, and a `--check` from the October 12 pins reproduced all four sections.

| Engine | Previous | Current | Current image digest |
|---|---|---|---|
| Halogen | 0.18.1 | 0.18.3 | `sha256:b5c28a27c11af02fc907c9c263522f2fc9ad1bd27b470adceca081175952de32` |
| Gufo | 0.13.0 | 0.15.0 | `sha256:451341e2249d72c04f8ef159aebacbe3d14e0591888c19c77a26f3d183961936` |
| Strixite | 0.2.4 | 0.2.4 | `sha256:23411d0de807055c97ce885b0ac60cfe17609836bb0d5a5c39d3cbb891a34876` |

The release notes below are publisher claims. The [local checks](#october-14-local-checks) that follow them ran after the update, from a session not served by Halogen. The images advertise image revisions Halogen `293c940b140e` and Gufo `89d6185532ff6d5de0336000fc6ad62e869b82b6`; neither was compared with public source.

### Halogen 0.18.2 and 0.18.3

- **End-of-text handling (#173).** The model declares two end-of-text tokens and 0.18.1 stopped on one, so an affected reply ran on to `max_tokens` and returned empty or with text after the end. 0.18.3 stops on either. Nothing of that shape was seen in local sessions.
- **Queue visibility and abandoned requests.** A client that disconnects while its request is queued now leaves the queue instead of taking a slot when its turn arrives, and a request waiting more than 30 seconds logs what it waits for, again every five minutes. `/health` adds `longest_wait_s` beside `queued`, and `/metrics` adds `halogen:queue_waited_total`, `halogen:queue_wait_seconds_total`, `halogen:queue_wait_longest_seconds` and `halogen:queue_gave_up_total`, none of which the current relabel allowlist collects. The dashboard treats `/health` as a boolean only, so the added field changes nothing there.
- **Startup memory reading.** The budget now counts kernel `CmaFree` as unavailable on hosts that reserve it, so a post-restart `host memory left` figure may not be comparable with the October 12 check for that reason alone.
- **New startup line.** `HALOGEN_TEMPLATE_CHECK` defaults to `warn` and reports whether the loaded chat template re-renders a conversation the way the prompt cache needs to reuse earlier turns. The launcher sets nothing, so this line should be read after the first restart on 0.18.3.
- **Strict tool schemas (0.18.2, #147).** A tool declared `strict: true` gets a call that names one of the request's tools with arguments matching its schema, at any temperature; `HALOGEN_STRICT_TOOLS=0` accepts the field without enforcing it. Neither `bin/run.sh` nor the Pi profile sets that variable, and whether the Pi profile sends `strict` on its tools was not checked.
- **Structured output and template parsing (0.18.2).** A `response_format` schema with an open object or an array without `items` no longer stalls the server for about a minute the first time it is sent, a sampled request with a schema and tools starts its JSON as promptly as a greedy one, and chat-template markers typed inside a message, tool result or tool description now reach the model as characters rather than as the template's own markers (`HALOGEN_CLIENT_MARKERS=special` restores the previous behavior).
- **Old GPU firmware (0.18.2).** A host with GPU firmware predating 2026 no longer fails on prompts of about 70 to 2,000 tokens or on images: the server reads the firmware version and logs one line saying it runs as with `HALOGEN_QSA_FORCE_SEL=1`. This host's firmware state was not checked, so that line is worth looking for after the restart.
- **Checkpoints and cache format.** Both Halogen sections state the Flash checkpoints are unchanged and that temperature 0 output stays byte-identical to serial greedy decode. Neither mentions a prompt cache or snapshot format change, and whether the existing `/cache` contents are reused on 0.18.3 was not checked.
- **Not reachable from this launcher.** The NPU features added in 0.18.2 and 0.18.3, namely EmbeddingGemma 2 and WeMM-Embedding-4B on `/v1/embeddings`, `/v1/images/edits` and `/v1/images/variations`, the opt-in streaming guard and the longer decider texts, need NPU model names that `bin/run.sh` does not set. `max_tokens: -1`, the llama.cpp-shaped `/props`, `/slots`, `/tokenize` and `/detokenize` routes, Codex tool namespaces, opt-in `HALOGEN_FORK_MAP=auto` and the second-AMD-GPU selection including `HALOGEN_GPU_DEVICE` are likewise unused here, and the slower default NPU image generation is irrelevant without NPU image models.

### Gufo 0.14.0 and 0.15.0

- **0.14.0** wired Flash-Next serving to the component cache (#573) and added a ROCm managed-alloc fallback (#460).
- **0.15.0** pins Flash-Next cache pages without compacting host memory (#589), accepts response schemas without `additionalProperties`, accepts IPv6 listen addresses, which does not change the localhost-only endpoint used here, and speeds up wide prefill kernels for Qwen Flash (#571), a publisher performance claim that was not benchmarked locally.
- Neither release note mentions a cache or snapshot format change, so whether an existing prompt cache is reused or starts cold on 0.15.0 is unknown, as it already was for 0.13.0.

### October 14 local checks

All three engines were started one at a time at native 262144 context with `/dev/accel/accel0` newly passed in. Each passed the readiness check, `bin/run.sh ENGINE smoke` and its live API test, then released its memory on stop (GTT back to 1.5 GiB). The live tests cover a multi-turn conversation, a forced named tool, a streamed automatic tool, slot release after a short-decode disconnect and generation after that cancellation. No engine used the NPU.

- **Halogen 0.18.3.** Allocation 81.4 GiB: 62.1 GiB weights, 7.2 GiB KV pool, 12.1 GiB working memory, with 30.6 GiB host memory left. The new template check passed: "the history is reusable in 6 of 6 turn shapes and the model's own reply in 4". No old-firmware workaround line appeared. The startup also warned that 12.1 GiB of host RAM was in use before it started, which it says comes out of the file cache that serves the 47.7 GiB lookup table; prefill speed was not measured. Every previously allowlisted metric name is still exported, and the two queue metrics now collected were checked through a real scrape (see [Halogen dashboard](halogen-monitoring.md)). A request queued behind a running one, whose client hung up after six seconds, left the queue as 0.18.3 claims.
- **Halogen prompt cache.** 0.18.3 opened a new, empty cache directory under `/cache`. Earlier releases' directories, about 24 GB in four directories, are not reused and were left in place.
- **Gufo 0.15.0.** First start on this host, loading in 62 seconds. Metrics and readiness scrapes were up. 0.15.0's component cache ignores `--cache-disk-staging-bytes` and logs `option_ignored` with a 1 MiB staging capacity. The launcher still passes the flag.
- **Strixite 0.2.4.** Unchanged image, rechecked only because the launcher now passes the NPU device.

Not exercised: Pi sessions on the new versions, strict tool schemas, structured output, long-context quality, deep-prefill cancellation, prompt-cache reuse across a restart, dashboard rendering in a browser and any NPU workload.

Sources: [Halogen 0.18.2 changelog](https://github.com/peonist-ai/halogen-flash-server/blob/v0.18.2/CHANGELOG.md), [Halogen 0.18.3 changelog](https://github.com/peonist-ai/halogen-flash-server/blob/v0.18.3/CHANGELOG.md), [Gufo 0.14.0 release](https://github.com/gufo-org/gufo/releases/tag/v0.14.0) and [Gufo 0.15.0 release](https://github.com/gufo-org/gufo/releases/tag/v0.15.0).

### Reply-end reuse

After these checks, Halogen was switched to `HALOGEN_FORK=1` with `HALOGEN_FORK_MAP=auto`, new in 0.18.3. Without it, each turn reused the previous prompt from cache but processed the model's own previous reply again, reasoning included. In a recorded Pi session that was up to about 7,500 tokens per turn.

[`.scratch/fork-map/bench.py`](../.scratch/fork-map/bench.py) replays a Pi-shaped conversation at temperature 0, with tool calls, reasoning sent back and two follow-up questions, from an empty cache for each configuration. At `xhigh` effort, a follow-up question after a 1,396-token reply processed 1,430 tokens again and took 1.13 seconds to its first token without the setting. With it, a follow-up after a 1,970-token reply processed 35 tokens and took 0.23 seconds. Uncached tokens after the first request fell from 9,534 to 6,324; the remainder is new tool output. Greedy replies were not identical between the two configurations, so the turns differ in length. The two configurations were compared turn by turn rather than with a single throughput figure.

Startup allocation is unchanged at 81.4 GiB. Health, smoke, the live API test and stop passed with the setting, and `GET /halogen/handles` listed the kept `auto` states. Up to four states are kept, using about 0.9 GiB of host memory plus the pool positions they hold, at most half the pool. The startup template check reports the model's own reply as reusable in 4 of its 6 turn shapes, so some reply shapes may still be processed again. A real Pi session with the setting was not measured. Kept states are shared by every client of the port, which stays bound to localhost.

### NPU host setup

XRT was installed from the CachyOS repositories: `xrt 1:2.21.75-14.1` and `xrt-plugin-amdxdna 1:2.21.75-2.1`. Halogen names AMD's XRT 2.25 and Ubuntu's 2.21 as tested, not Arch builds. Checked before installing, the three libraries the container loads need at most `GLIBC_2.38` and `GLIBCXX_3.4.32`, within the image's glibc 2.41 and `GLIBCXX_3.4.33`, and their other dependencies are in the image. The image itself carries no XRT.

Halogen's `halogen-fabric-clock` script was taken from its `v0.18.3` tag (`deploy/host/halogen-fabric-clock`, SHA-256 `0dbd47c15f1002e0a8997ec7070e96f3e009125068eab8eccbbd49424a594f5a`). It only sets the GPU's `power_dpm_force_performance_level` to `manual` and `pp_dpm_fclk` to its top level, 2000 MHz here, or sets the level back to `auto`. Halogen says holding costs about a watt. Idle package power (`amdgpu` `PPT`, which includes the CPU), averaged over 60 seconds after 10 seconds of settling, measured 16.21 W held against 13.56 W on `auto`, then 15.35 W against 13.36 W: about 2.3 W. The boot unit was therefore not enabled; `bin/run.sh` holds the clock only while Halogen runs NPU models, through a sudoers rule for that script alone, which accepts only `hold`, `release` and `status`.

### First NPU run

The first start with NPU models exited because the container could lock only 8 MiB and the small set needs 5.2 GiB. The desktop session inherits `LimitMEMLOCK=8M` from `user@1000.service`, which also capped the launcher's `--ulimit memlock=-1:-1`. A drop-in at `/etc/systemd/system/user@1000.service.d/memlock.conf` raised it to 32 GiB, effective after a reboot. The launcher now refuses NPU models below 4 GiB, because `--rm` discards the container's own error.

Halogen 0.18.3 then started at native 262144 context with each set below, accepted the host XRT libraries and the held clock, checked every NPU file against its record and listed the NPU models in `/v1/models`. The Flash allocation stayed 81.4 GiB. `bin/run.sh halogen stop` released the clock, GTT returned to 0.5 GiB and locked memory to 0.1 GiB. A start without `NPU_MODELS` left the clock on `auto`. The kernel log showed no `amdxdna` errors. Requests came from [`.scratch/npu/routes.py`](../.scratch/npu/routes.py).

| Set | Host RAM used beyond Halogen without NPU | Route checks |
|---|---|---|
| `decider-0.8b`, `embeddinggemma-2`, `qwen3guard-stream-0.6b` | about 6.2 GiB, 3.4 GiB of it locked | Spam decision yes 0.992 in 0.58 s on the first call. `/v1/systemone` picked billing 0.994 in 0.11 s. Text embeddings, 768 dimensions, scored a related pair 0.87 and an unrelated one 0.60 in 0.15 s. A solid red image was closer to "a plain red picture" than to blue, 0.72 against 0.62. The streaming guard labelled the user message and six reply chunks and sent its end summary. |
| `decider-4b`, `wemm-embedding-4b` | about 8.9 GiB, 8.8 GiB of it locked | Spam decision yes 0.987 in 1.65 s. Text embeddings, 2560 dimensions, related 0.72 and unrelated 0.14. Red image closer to red, 0.44 against 0.31. Times are first calls. |

Host RAM was compared as `free` used after the route checks against a start without NPU models. Halogen's own "host memory left" figure barely changed with NPU models (37.6 and 38.1 against 38.7 GiB), so it does not show their cost.

[`.scratch/npu/slowdown.py`](../.scratch/npu/slowdown.py) alternates an uncached 26,150-token Flash prompt with a 1,024-token greedy reply, thinking off, with the NPU idle and while another client keeps it busy:

| NPU load | Rounds | NPU requests per Flash run | Flash prefill | Flash decode |
|---|---|---|---|---|
| idle | 9 | | 1,659 to 1,677 tok/s | 72.0 to 72.3 tok/s |
| `embeddinggemma-2`, 8 short texts per request | 3 | 97 to 101 | 1,624 to 1,631 (about -2%) | 68.5 to 68.8 (about -5%) |
| `decider-0.8b`, 1,500-token text | 3 | 103 to 104 | 1,609 to 1,612 (about -4%) | 67.4 to 67.5 (about -7%) |
| `decider-4b`, same text | 2 | 28 | 1,570 to 1,571 (about -6%) | 64.1 to 64.6 (about -11%) |
| `wemm-embedding-4b`, 8 short texts | 1 | 22 | 1,546 (about -7%) | 63.6 (about -12%) |

These are worst cases: the NPU never rested. Occasional helper requests cost proportionally less. Not exercised: loading both sets at once, audio embeddings, larger images, NPU memory contention between `embeddinggemma-2` and `wemm-embedding-4b`, the guard on a flagged reply, and agent or Pi workloads.

## October 12 update

`bin/update.sh` pulled the new Halogen and Gufo images by digest and atomically updated their image and version pins. Strixite `latest` still resolves to the pinned 0.2.4 digest. Model revisions, weight files, launch settings, live Pi files and host settings remain unchanged.

| Engine | Previous | Current | Current image digest |
|---|---|---|---|
| Halogen | 0.18.0 | 0.18.1 | `sha256:f0b39c8908f9897f27ab0a64e964c775e136a7cf7a1bafeb4de0c6d5d1e07e29` |
| Gufo | 0.12.0 | 0.13.0 | `sha256:e03e006da8485314e2440acbce5167c4659ef853af64ed339337f29fe43bd3b4` |
| Strixite | 0.2.4 | 0.2.4 | `sha256:23411d0de807055c97ce885b0ac60cfe17609836bb0d5a5c39d3cbb891a34876` |

Halogen 0.18.1 passed a short check at a reduced 32768 context, described below. Gufo 0.13.0 has not been started on this host: its health, generation, tools, cancellation, metrics, stop and memory release are all unexercised. Everything from the October 11 update onward describes the previous images and must not be read as results for these pins. Unless a point below says it was checked, it comes from the publishers' release notes only.

- **Halogen disconnect handling:** a reply now pauses for 20 seconds when its client disconnects, instead of stopping, and resumes if the same request is retried. `HALOGEN_RETRY_GRACE_S=0` restores the previous behavior. The launcher does not set it, keeping the upstream default. Checked locally: a paused reply keeps `/health` `in_flight` at 1 for the full 20.0 seconds when nothing else arrives, and a new request sent during the pause took the slot and answered in 0.15 seconds. The 20-second bound in `tests/live.py` therefore failed on this release and is now 30 seconds.
- **Halogen scheduling:** a short request now runs between pieces of a long prompt, and a request from a person goes ahead of queued agent turns. The Flash checkpoint is explicitly unchanged, and temperature 0 output is stated to stay byte-identical to serial greedy decode.
- **Halogen additions left off:** `prompt_cache_policy: "no_store"`, structured output above temperature 0 and the opt-in Claude Code sessions (`HALOGEN_FORK`, `HALOGEN_FORK_MAP`) are not used by the launcher or the Pi profile. The `/v1/messages` output-cap and `/v1/responses` history fixes do not touch the Chat Completions route Pi uses.
- **Gufo stall handling:** the server now exits as `device_lost` when generation stops making progress. A stall therefore ends the container instead of leaving it hung. How the launcher's status, logs and the dashboard present that exit is unverified.
- **Gufo fixes:** compatibility routes accept a boolean or null `stream`, and raw completion routes honor `cache_prompt`. The documented 128 n-gram readers for Qwen Flash are a publisher performance change, not benchmarked locally.
- **Cache compatibility:** neither release note mentions a cache or snapshot format change. Whether existing prompt caches are reused or start cold was not checked.
- **Image revisions:** Halogen advertises `b540030f8abf` and Gufo `fcf8bf706f31da3d5c79a3a7da402354cde308a7`. Neither was compared with public source.

### Halogen 0.18.1 check

Halogen was started alone with `CONTEXT=32768` rather than the native 262144, because other applications held about 25 GiB of host RAM. A fresh temporary cache kept synthetic requests out of the normal conversation cache and was removed afterward. Monitoring was not running.

| Check | Halogen 0.18.1, 32768 context |
|---|---|
| Ready, MTP on, API and engine both report 0.18.1 | Pass, engine listening after 34 seconds |
| Bounded non-thinking `ready` generation | Pass |
| Multi-turn recall | Pass |
| Forced named tool | Pass |
| Automatic streamed tool, strict assembled JSON | Pass, 4 fragments |
| Short decode disconnect and generation afterward | Pass with the 30-second bound; slot read idle at 20.0 seconds |
| Native metrics endpoint | Answers; all 28 allowlisted metric names are still exported |
| Stop and host memory release | Pass |

Halogen reported 27.4 GiB of host memory left at this context. After the stop, MemAvailable returned to about 103 GiB, above its pre-start reading, and kernel GTT to about 2.5 GiB, its level with the other applications open. About 3.9 GiB of other processes' memory was in swap afterward.

Not exercised on 0.18.1: native 262144 startup and its allocation, a Prometheus scrape through the monitoring stack, dashboard rendering, metric wire types and semantics, prompt-cache reuse from the normal cache, retry resumption of a paused reply, the new scheduling under concurrent load, and any Pi session. The endpoint also exports `halogen:build_info`, `halogen:structured_requests_total`, `halogen:draft_list_tokens_total` and `halogen:draft_list_misses_total`, which the allowlist drops; whether these are new in 0.18.1 was not checked.

### Image cleanup

The superseded Halogen 0.18.0 and Gufo 0.12.0 images were removed by ID without force. No containers existed. Rolling back requires pulling the previous digests in the October 11 table again.

Sources: [Halogen 0.18.1 changelog](https://github.com/peonist-ai/halogen-flash-server/blob/v0.18.1/CHANGELOG.md) and [Gufo 0.13.0 release](https://github.com/gufo-org/gufo/releases/tag/v0.13.0).

## October 11 update

All three upstream images were pulled by digest through `bin/update.sh`, and image and version pins were atomically updated. Model revisions, weight files, launch settings, live Pi files and host settings remain unchanged. Basic checks passed one engine at a time with native 262144 context and MTP enabled. All engines and monitoring are stopped afterward.

| Engine | Previous | Selected | Selected image digest |
|---|---|---|---|
| Halogen | 0.17.5 | 0.18.0 | `sha256:de3b47d2e5f24f98a38ba5fb66b0075b0cd8a3219c38917c78fb4bbeb42b88d9` |
| Gufo | 0.11.0 | 0.12.0 | `sha256:25c52218f494f9c35fab96184b813576d4f1e71cbe025631b106360a1d420206` |
| Strixite | 0.2.3 | 0.2.4 | `sha256:23411d0de807055c97ce885b0ac60cfe17609836bb0d5a5c39d3cbb891a34876` |

## Local adaptations

No launcher or Pi-profile migration was required. Existing localhost endpoints, supported thinking choices, sampling settings, read-only model mounts, separate caches and single-engine startup lock remain appropriate. New speech, vision, named-session and Messages features were not enabled.

`tests/live.py` now also checks an automatic streamed tool call for Halogen and Gufo, assembling argument deltas by tool index and requiring strict JSON, a successful tool-call finish and stream completion. It never executes returned calls. The existing named-tool requirement and 20-second decode-disconnect assertion remain intact. This covers Gufo's changed incremental argument delivery without a lengthy coding test. Dashboard version descriptions were refreshed; existing queries and metric allowlists remain unchanged.

### Halogen

The release fixes cache reuse when clients change or drop part of the newest message, including disk cut-back instead of writing another conversation copy. The Flash checkpoint is explicitly unchanged. Disk state uses separate engine-build namespaces, so an upgrade starts cold while previous namespaces remain on disk. The 16 GiB limit applies to the active namespace, not the whole cache directory. Normal caches were not pruned or rotated.

The new scalar counters `halogen:cache_last_message_rewrites_total` and `halogen:cache_disk_cut_back_total` were verified as counters on the real endpoint. They count resumed rewrite requests and disk cut-back events respectively, not bytes saved. Both were zero in this short check. Existing allowlists intentionally drop these optional additions; the current dashboard remains compatible without new panels.

The image advertises revision `c31448922f6e`, which was not resolvable in the public source repository during review. Public v0.18.0 resolves to `9b12eadaef73475aa77ec82122474690707c92b6`. Public release documentation and the actual image's version, health, metrics and generation were checked, but source equivalence to the advertised binary revision is not established.

### Gufo

Native tool arguments now stream incrementally. Pi already assembles OpenAI tool deltas, so no profile change was necessary. The new Flash-Next continuation adapter is not yet attached to HTTP serving; the legacy serving cache identity and snapshot payload version remain unchanged. Existing same-settings snapshots are structurally compatible, but cross-version restoration was not tested.

Snapshot capture now preserves HIP headroom and can fall back to already-budgeted host payloads. This is not a new memory-limit flag or a guarantee against host memory pressure. Retain the conservative 2 GiB RAM-cache and disk-staging limits. Upstream recommends 8 GiB staging for full-depth MTP snapshots if RAM permits. Larger budgets and full-depth restart persistence remain separate, deferred memory-policy work. Serving native context does not require changing those limits.

### Strixite

The release defaults to seven MTP drafts instead of five. Think-close-on-call is on independently of our disabled thinking nudge: it can inject a thinking closure before a tool call begun inside reasoning. This is a serving-policy change, not a replacement for strict tool-argument validation or the test sandbox. Historical coding comparisons used five drafts and no close-on-call intervention; they must not be relabeled as measurements of this release. Publisher speedup claims were not benchmarked locally.

Prefill progress is opt-in through `return_progress: true`. The Pi profile does not request it, and Pi progress rendering was not evaluated. Disk cache format and state fingerprints remain compatible with the unchanged model, MTP and YaRN baseline. Eviction writes release RAM progressively. No cache rotation is required by the source changes, and successful restoration remains unvalidated.

The real endpoint exports the additive scalar counter `strix_think_closed_for_call_total`, zero in this non-thinking API check. Existing metrics keep their accounting semantics. The current allowlist intentionally drops this optional counter. No dashboard query migration is needed.

## Basic runtime checks

Fresh temporary SSD caches kept synthetic requests out of the normal conversation caches. The model presence and size check ran at launch. The previously completed full weight hashes were not repeated. The optional existing monitoring stack ran during the checks.

| Check | Halogen 0.18.0 | Gufo 0.12.0 | Strixite 0.2.4 |
|---|---|---|---|
| Ready, native 262144, MTP on | Pass | Pass | Pass, YaRN 1 and no degradation |
| Bounded non-thinking `ready` generation | Pass | Pass | Pass |
| Multi-turn recall | Pass | Pass | Pass |
| Forced named tool | Pass | Pass | Unsupported, unchanged |
| Automatic streamed tool, strict assembled JSON | Pass, 4 fragments | Pass, 4 fragments | Pass, 22 literal-tag argument fragments |
| Short decode disconnect and generation afterward | Pass, within existing 20-second bound | Pass, within existing 20-second bound | Pass, 0.253 seconds |
| Native Prometheus scrape | Pass | Pass | Pass |
| Independent readiness probe | Not configured | Pass | Pass |
| Stop and host memory-release gate | Pass | Pass | Pass |

Strixite also passed its existing automatic tool-result follow-up and deliberate 12-token truncation inspection. The incomplete arguments were not repaired or executed. Halogen reported 81.4 GiB startup allocation, Gufo 88.48 GiB GPU allocation. These are historical startup reports, not workload peaks or additive host-memory measurements. After every stop, MemAvailable returned to approximately 119 GiB and kernel GTT to approximately 0.64 GiB before the next engine started.

At the user's request, no Pi coding loop, coding matrix, long-context request, benchmark, deep-prefill cancellation, cache-restoration test, GPU-fault test or new-feature exercise was run. The thinking-enabled Strixite close-on-call intervention was source-reviewed, not deliberately triggered. Older coding and monitoring-overhead results remain historical. Short successful operation does not establish near-capacity memory safety or unrestricted real-project tool safety.

## Podman cleanup

After successful checks and shutdown, removed the three superseded engine images, unused browser build branches and intermediates and the hello-world image. In total 23 image records were removed without force. Podman's reported shared image-store size fell from 17.62 GB to 13.66 GB, approximately 3.96 GB reclaimed. No stopped containers existed before the update, and test and monitoring containers were auto-removed on stop. Zero containers remain.

All seven current engine and monitoring pins remain locally available. The maintained Pi browser image and its required base/ancestor images remain, for 18 total image records including build ancestry. Named monitoring volumes, normal conversation caches and weights were retained. Do not blanket-prune untagged images. Digest-pinned current images also appear untagged and reclaimable. Rolling back now requires pulling the previous digest again.

## Sources

- [Halogen 0.18.0 changelog](https://github.com/peonist-ai/halogen-flash-server/blob/v0.18.0/CHANGELOG.md), [cache namespaces](https://github.com/peonist-ai/halogen-flash-server/blob/v0.18.0/README.md#L2183-L2228) and [new counters](https://github.com/peonist-ai/halogen-flash-server/blob/v0.18.0/README.md#L559-L576).
- [Gufo 0.12.0 release](https://github.com/gufo-org/gufo/releases/tag/v0.12.0), [continuation adapter scope](https://github.com/gufo-org/gufo/blob/v0.12.0/docs/models/qwen3.8-flash-next/CONTINUATION-ADAPTER.md) and [snapshot staging](https://github.com/gufo-org/gufo/blob/v0.12.0/docs/SERVER.md#L218-L233).
- [Strixite 0.2.4 release](https://github.com/shawnshekari/strixite/releases/tag/v0.2.4), [exact source comparison](https://github.com/shawnshekari/strixite/compare/dbe7b66ed620d392d0b3b6a8a6e836f9907ffea6...06e45551558b1d541c59c831041f7a52468d2c52) and [close-on-call implementation](https://github.com/shawnshekari/strixite/blob/06e45551558b1d541c59c831041f7a52468d2c52/serve/engine.cpp#L510-L539).
