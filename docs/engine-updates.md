# Engine updates

## November 21: Gufo LoRA merged at load

The `lora` profile now serves the stock UD-Q4_K_XL shards with the Huihui v2 adapter merged while they load, instead of a merged copy on disk. Stock Gufo 0.35.0 has no adapter loading for this model, so the profile runs a local build of the Gufo fork at `452c7c0da851a152377e39718ed681890a29e5f1` (upstream `c3018d64` plus one commit), image `localhost/strix-halo-inference/gufo-fork` at digest `sha256:9b112ab4d5705c7b7bb38849dfd7ce6ac1e1929dc282cb3cacb2b8fa784d8d84`. `default`, `iq4-xs` and `iq4-xs-lora` still run the pinned upstream image. [Build, behavior and results](weight-profiles.md#lora-merged-at-load)

`iq4-xs-lora` made the same move through the IQ extension: `GUFO_IQ_REVISION` is now `3f8a1a53362896672d2b6981c9027e8372bd30d3` (version 0.3.0, a fork of the extension that merges adapters at load), installed into the pinned image, and the profile serves the stock UD-IQ4_XS shards plus the adapter. Its 12 Q6_K `attn_output` tensors are stored as Q8_0 after the merge, so its weights differ slightly from the earlier merged copy. Both IQ profiles passed verification, readiness, smoke and `tests/live.py` on the new module. [Details and results](weight-profiles.md#iq4-xs-lora-merged-at-load-by-the-iq-extension)

- **Equivalence:** the loader's 96 merged tensors match the previous merged copy byte for byte (885,719,040 bytes), and three prompts at temperature zero gave identical text from both on the same binary.
- **Launcher checks:** `bin/models.sh verify gufo lora`, native-262144 readiness with MTP, the smoke request and `tests/live.py` passed on the fork image, and memory was released after stopping.
- **Not repeated:** the November 18 refusal probes and Pi coding trials, on either adapter profile. The fork image was not tested with the `default` profile, which does not use it.
- **Deleted:** the merged directory `nazeshinjite/Qwen3.8-Flash-Next-Abliterated-LoRA/UD-Q4_K_XL-d9620119`, 852.57 MiB exclusive, after the byte comparison. No profile used it. `bin/gufo-lora.py` at commit `55a47e5` can recreate it from the stock shards if a reference is needed again. The merged IQ4_XS directory is kept as a comparison reference, and the script itself was removed.

## November 18 Halogen update

Halogen 0.20.7 is pinned to image digest `sha256:773073448dc9ff4a8c6b6c278802e254fd5f1546764e27531aeb3b77cb13482e`, advertised revision `509080d0e1a5`. All three Halogen weight manifests pin `qwen38-flash-next-drafter-r2-ht4.hgn` from model revision `05ec74b75cd68c4d6486d15825f2fc73b2ffe304`. The 1,488,276,864-byte file has SHA-256 `f9aa330800cc921fe20f4cf997d660f519c67b0052af0c8078b6b648972b07e6`. The abliterated profiles share a reflink of the stock head. Full manifest verification passed for each profile. [Tagged changelog](https://github.com/peonist-ai/halogen-flash-server/blob/v0.20.7/CHANGELOG.md#0207)

Stock v2, HT43 and abliterated r2 each loaded all 54 overlay tensors (1.39 GiB), enabled the new default concurrency mode with the existing single slot, and accepted MTP drafts on real generation. Each passed native-256K readiness, smoke, multi-turn conversation, named and streamed tools, disconnect and generation after cancellation, all 33 allowlisted metrics and the post-stop memory-release check. The stock run also passed the NPU decision, routing and text/image embedding suite with d3-lite, decider-0.8b and embeddinggemma-2. The image-derived NPU manifest and the installed fabric-clock helper still match the release. The clock returned to auto on shutdown.

| Profile | Prose decode (tok/s) | Code decode (tok/s) |
|---|---:|---:|
| default | 65.9 | 88.1 |
| abliterated-ht43 | 71.2 | 92.5 |
| abliterated-r2 | 68.3 | 102.2 |

Each sample used temperature zero, thinking off and a 600-token cap. These are short single-request observations. The update's speedup over 0.20.6, multi-slot throughput and near-capacity prefill were not measured.

All three starts warned about low contiguous memory (309–330 free 2 MiB blocks). Two also warned about pre-existing host RAM use (11.3 and 14.8 GiB), and the stock start warned about 4.1 GiB of pre-existing GTT use. These conditions can slow startup and long-prompt prefill. All profiles finished the short checks and released memory. The offline update, launcher and model checks passed. The superseded 0.20.6 image was removed by digest. All three engine prompt caches were cleared, and all engines were stopped.

## November 17 update

`bin/update.py` pulled Halogen 0.20.6, Gufo 0.35.0 and Strixite 0.7.1 by digest and atomically updated their image and version pins. Launch settings, Gufo and Strixite model revisions, live Pi files and host settings are unchanged. `bin/npu-manifest.sh` against the 0.20.6 image produced no change. Halogen's new draft head was added to every Halogen weight profile, the `flash_next_iq` module was rebuilt for the new Gufo image, and all engines passed the [local checks](#november-17-local-checks). Afterwards the superseded Halogen 0.20.4, Gufo 0.34.0 and Strixite 0.7.0 images were removed by digest without force (no container used them; Podman's image store fell from 36.37 GB to 28.98 GB), the 42 MB `flash_next_iq` build for the removed Gufo image was deleted, and `bin/cache.sh all clear` emptied all prompt caches.

| Engine | Previous | Current | Current image digest |
|---|---|---|---|
| Halogen | 0.20.4 | 0.20.6 | `sha256:f68892a56d8a1182645042574d702374bff402bb986ec4d49304cbe89483dbaf` |
| Gufo | 0.34.0 | 0.35.0 | `sha256:99e9b5471b7a9b007c686c2aa795afaf966744d64e753cb009c89541f9e9c2b6` |
| Strixite | 0.7.0 | 0.7.1 | `sha256:bf2f840bfee7c781e0a576f96542c6495f8b10ba17fc96da5600662d22e4d4cf` |

The images advertise revisions Halogen `109f0b78e221`, Gufo `0260e1162f8713caee4d3f4ff77e017de7165f9c` and Strixite `dd3c5e0`, not compared with public source.

### Halogen draft head

0.20.6's entrypoint loads `qwen38-flash-next-drafter-r2.hgn` as `HALOGEN_CK_OVERLAY` when it sits beside any `qwen38-flash-next-*.hgn` checkpoint, which covers the stock v2 and both Quat3rnion files, and sets the cost-based draft gates. Without it the checkpoint's own head drafts. It downloads the file only with `HALOGEN_DOWNLOAD` and a writable models volume, which this repo does not use, so the file is pinned instead: 1,523,568,192 bytes, SHA-256 `07a7b5b358cb02737ecf85043db0d30b4938aed06ae6311772ea4e40b939696b`, from `peonist-ai/halogen-qwen3.8-flash-next` revision `e3b33d6422216419d46434c2d9a64d82a9654d08`, in the stock and both abliterated manifests. The abliterated directory holds a reflink copy. All three profiles verified. The launcher needs no change; `env SPECULATIVE=off` still turns drafting off. The overlay replaces the checkpoint's own 36 head tensors, so resident weights stay 62.1 GiB on v2. The repository also gained `qwen38-flash-next-drafter-r2-ht4.hgn` on November 17, labelled for the next server release; 0.20.6 does not read it and it is not provisioned.

### What changed upstream

- **Halogen 0.20.5** decodes faster with several requests at once and stores saved conversations in less memory; at temperature 0 a reply can occasionally differ from 0.20.4 (`HALOGEN_DN_STATE=fp32` restores the old state precision). Prompt caches saved by an earlier version are rebuilt. Hindi, Thai and other Indic-script prompts now tokenize as the model was trained. The image's NPU runtime moves to XRT 2.27, LFM3 on the NPU reads long prompts about twice as fast, and `HALOGEN_AGENT_GUARD=watch` no longer loads the hold model. Fixes cover `#### 18`-style final answer lines (#259), negative numbers in pretty-printed JSON arrays under structured output (#258), a 404 for unloaded Halogen model names (#257), Claude Code's `tool_addition`/`tool_removal` blocks (#261), `anyOf` schemas of up to 32 tool branches (#263), a kept-state wait (#265) and a stalled NPU engine, which now restarts after `HALOGEN_NPU_KILL_S`. [Tagged changelog](https://github.com/peonist-ai/halogen-flash-server/blob/v0.20.5/CHANGELOG.md).
- **Halogen 0.20.6** adds the draft head above (publisher: about 4% faster single-request decode, answers unchanged), reads images about four times faster, processes ht43 prompts 1 to 2% faster, adds a `:qad` LFM3-1.7B NPU format and an opt-in `HALOGEN_CONC_MODE` for 4 to 16 concurrent requests, which makes a single request 7 to 9% slower and is not used here. It fixes recomputation of shared long prompts ending just past a 32,768-token boundary, and a rare reply computed from another conversation's context when several conversations ran at once and context memory was full; this launcher's single slot makes the latter unlikely to apply. [Tagged changelog](https://github.com/peonist-ai/halogen-flash-server/blob/v0.20.6/CHANGELOG.md).
- **Gufo 0.35.0** parses multipart form bodies per RFC 7578, marked breaking, and requires a text scheduling profile inside each model runner, removing the legacy prefill budget; neither affects this launcher's flags. It runs EmbeddingGemma 2, Qwen3-ASR and Qwen3-TTS on the XDNA NPU with `--npu` (catalogued in [engine models](engine-models.md#gufo-0350)), adds an A1111 image API and Qwen-Image guidance features, drafts Flash-Next MTP proposals from a Q4_K copy of the head prefix, fixes compacted MTP rows reaching the norm buffer, and improves cache retention and disk recovery. The extension API is now 0.3.20, still series 0.3. The Flash-Next `weights.cpp` loader is byte-identical to 0.34.0's, so its quantization limits are unchanged. [Release notes](https://github.com/gufo-org/gufo/releases/tag/v0.35.0).
- **Strixite 0.7.1** is a stability release with unchanged weights. Several long slots no longer get refused K/V room the cache could free (#42); a stream that fails after starting now ends with an `event: error` frame and `finish_reason: "error"` instead of `[DONE]` (#43); a hang at the end of very long prefills is avoided at under 0.5% long-context decode cost (#31); MTP rollback with `mtp-draft` 11 or higher is exact (#37). The default `thinking-cap` is now 32,768 tokens (#47); the launcher does not override it. [Release notes](https://github.com/shawnshekari/strixite/releases/tag/v0.7.1).

### November 17 local checks

Prompt caches were cleared before the checks. Each engine and profile was started alone at native 262144 context with MTP on, then stopped. MemAvailable was 116.7 GiB before the first start and 119.0 to 119.5 GiB after each stop, with Unevictable 116 KiB. `tests/update.sh`, `python tests/run.py`, `tests/models.sh` and `git diff --check` passed. The v0.20.6 fabric-clock helper has the same SHA-256 as the installed one.

| Check | Halogen 0.20.6 | Gufo 0.35.0 | Strixite 0.7.1 |
|---|---|---|---|
| Ready and `tests/live.py` or `tests/strixite_live.py` | Pass on `default`, `abliterated-ht43` and `abliterated-r2`, 4 fragments each | Pass on `default`, `iq4-xs` and `iq4-xs-abliterated`, 4 fragments each | Pass, 22 fragments, slot released 0.25 s after disconnect |
| Allowlisted names on `/metrics` | 33 of 33 | 17 of 17 | 33 of 33 |
| Memory at start | 78.4 GiB in all on v2 and r2, 70.0 GiB on ht43, drafter included | MemAvailable about 28.5 GiB serving Q4_K_XL, 43.9 GiB serving IQ4_XS | GPU buffers 79.3 GiB, MemAvailable 32.2 GiB after loading |

Decode rates from one temperature-0 request each, thinking off, 600 tokens at most. These are single samples, not benchmarks; no run without the new Halogen head was made for comparison.

| Engine and profile | Prose, tok/s (drafts accepted) | Code, tok/s (drafts accepted) |
|---|---|---|
| Halogen `default` | 67.4 (350 of 466) | 99.0 (478 of 548) |
| Halogen `abliterated-ht43` | 70.5 (355 of 448) | 101.1 (477 of 542) |
| Halogen `abliterated-r2` | 67.7 (341 of 458) | 92.6 (465 of 553) |
| Gufo `default` | 47.4 (315 of 520) | 75.3 (475 of 593) |
| Gufo `iq4-xs` | 48.7 (336 of 559) | 71.4 (475 of 581) |
| Gufo `iq4-xs-abliterated` | 48.2 (326 of 565) | 70.5 (476 of 592) |
| Strixite | 57.1 | 84.9 |

- **Halogen draft head.** Every profile logged `draft head qwen38-flash-next-drafter-r2.hgn` and loaded its 36 tensors, 1.42 GiB, as the overlay.
- **Halogen NPU.** Halogen started with `d3-lite`, `decider-0.8b` and `embeddinggemma-2` on the image's XRT 2.27.0. `python tests/npu_live.py`, whose fixed prompts are the baseline for later releases, gave the same results on two runs: the spam decision `yes` at 0.992; on the double-charge complaint `decider-0.8b` chose `billing` at 0.994 with a refund probability of 0.129, and `d3-lite` `billing` at 0.687 with 0.796; text embeddings 0.869 related and 0.604 unrelated; the red image 0.719 against `red` and 0.622 against `blue`. The November 14 prompt was not recorded exactly, so its 0.86 and 0.98 for `d3-lite` are not comparable; with the upstream guide's wording `d3-lite` chose `technical` at 0.47 over `billing` at 0.44. Flash's live test passed beside the NPU models. After stop the fabric clock was back on `auto` and the kernel log had no `amdxdna` or `amdgpu` messages.
- **Gufo extension.** `flash_next_iq` 0.2.0 at the approved revision rebuilt in the new image under the same no-network, read-only, rootless settings and reports `[installed, ready]`. Its compiler warnings are the same 195 in the same 10 categories as the 0.34.0 build. Gufo cannot load the old build, because the store is keyed by image digest.
- **Logs.** Halogen warned at each start that the host had only 265 to 419 contiguous free 2 MiB blocks, where November 14 logged no such warning with 324; startup still completed in 17 to 27 s. Gufo and Strixite logged no warnings. Strixite reported its new `thinking-cap` of 32,768 from the bundled configuration.

Not exercised: the Gufo `abliterated` Q4_K_XL profile, Pi sessions, image input, deep prefill and long context, Halogen text to speech, `HALOGEN_CONC_MODE`, Gufo's NPU modes, Strixite's error-frame path, power draw and a decode comparison with the checkpoint's own Halogen head.

## November 15: Gufo IQ4_XS extension trial

Ticket 05 adds `iq4-xs` and `iq4-xs-abliterated` beside the existing Q4_K_XL profiles. Both new profiles run on the unchanged Gufo 0.34.0 image with the optional `flash_next_iq` module, one session, native 262144 context and MTP enabled. They allocate 72.64 GiB against Q4_K_XL’s 89.12 GiB, a 16.49 GiB reduction (about 18.5%). The default remains Q4_K_XL. Select the new profiles in the dashboard or with:

```bash
bin/run.sh gufo start --weights iq4-xs --wait
bin/run.sh gufo stop
bin/run.sh gufo start --weights iq4-xs-abliterated --wait
```

### Pins and installation

The [stock manifest](../config/weights/gufo-iq4-xs.tsv) pins Unsloth UD 3.1 at `d96201194f103c906994f283f504209dc8d2a10c`. Upstream sizes and hashes were rechecked before downloading. Shards 1–3 and the standalone Q8_0 MTP head downloaded and passed SHA-256 verification; shard 4 was reflinked from the existing Q4_K_XL n-gram shard and independently hash-verified. The four shards total 93,672,359,738 bytes (87.24 GiB). The final profiles reuse the existing shared Q8_0 MTP head, whose hash was also checked. The standalone head remains on disk as a trial reference; its pin and hash are recorded in [ticket 05](../.scratch/abliterated-trials/issues/05-gufo-extension-ud-iq4xs.md).

The extension is version 0.2.0 at [source revision `9ce08cef17151aca3751ea2528765902054c54c4`](https://github.com/storm1er/flash-next-iq-gufo-extension/tree/9ce08cef17151aca3751ea2528765902054c54c4), committed as `GUFO_IQ_REVISION`. [Registry PR #11](https://github.com/gufo-org/gufo-extension/pull/11) was still open with no reviews. After inspecting its build recipe, registration/probe and loading paths, the user explicitly approved installing this unreviewed native source. It compiled inside the pinned Gufo image with rootless `--userns=keep-id:uid=1000,gid=1000`, no network, a read-only root filesystem and source mount, temporary `/tmp`, and only its extension store writable on the host. No GPU devices, models or host home were mounted into the build. A separate read-only invocation of `gufo extension list` reported `flash_next_iq 0.2.0 [installed, ready]`.

Gufo recorded source digest `1eac21ac3d8cb142e6ab51bfd9389b8799f24f928dc3564c238ed29e959a9671`; the installed module SHA-256 is `0534b572c4c45177a6db41568ef3e484591c51c21ea6e07c3db535775110560d`. Build logs, source-file hashes, model metadata, trial scripts and results remain outside Git under `$HOME/.cache/strix-halo-inference/trials/gufo-iq4-xs`. [The extension guide](gufo-extensions.md#iq4_xs-profiles-on-this-host) records the install command.

The module store is `CACHE_ROOT/gufo-extensions/IMAGE_SHA256/SOURCE_REVISION`. Only profiles declaring `extension: flash_next_iq` mount it, read-only, at `/extensions`. Normal Q4_K_XL starts load no community module. An image or source-pin change selects a fresh store; missing installations disable the profile and fail before container creation. Gufo additionally checks its module build identity. Prompt-cache clearing does not touch the extension store. Rootless weight upload worked without changing the container user, GPU permissions or host settings.

### Shared MTP head

The standalone and shared files have exactly the same 32 draft-block tensors, including types, shapes and SHA-256 of every tensor’s contents. Only the standalone file contains its own `output.weight` and `token_embd.weight`. A separate shared-head run passed readiness, real generation, conversation, streamed tools, cancellation and generation after cancellation. Both heads reported exactly 74,381 MiB of GPU allocation, and both decode samples accepted 239 of 380 draft tokens. The smaller shared file therefore did not save the anticipated 1.3 GiB of GPU memory in this extension; both final profiles use it to reuse the existing companion.

### Abliteration and file verification

The existing huihui script, patch and key at revision `cbc7fba13f1939ac3fa42b18d77ccf43847d74ef` were hash-verified again. Patching ran in Bubblewrap without network or home access, with read-only inputs and only the new output directory writable. The command was:

```text
patch-unsloth-Qwen3.8-Flash-Next-dec.py --input-path /in --patch-path /patch/patch-unsloth-all --output-path /out --start-layer 0 --end-layer 48 --ablate-experts 2
```

`/in` was the pinned `UD-IQ4_XS` directory and `/out` was `huihui-ai/Huihui-Qwen3.8-Flash-Next-abliterated-v2-GGUF/patched-unsloth-UD-IQ4_XS-d9620119` under `/home/bogdan/models`. The existing isolated Python environment supplied NumPy and tqdm, with `gguf-py` loaded explicitly from llama.cpp revision `18b74fa41dcac1f55ae1371fe58153f7225941f6`. That source knows GGML Q2_0, used by `blk.8.ffn_down_exps.weight` and `blk.10.ffn_down_exps.weight`; PyPI gguf 0.19.0 does not.

Exactly 96 tensors changed: 36 Q8_0 `ssm_out`, 48 Q8_0 `ffn_down_shexp`, and 12 Q6_K `attn_output`. There were no missing patch entries or dtype-mismatch copies. The 180 unused donor entries are expected because the patch also contains alternative formats. The verifier checked all 1,224 tensor names, types, shapes and bytes, plus all metadata: every intended target changed and no other tensor did. It now compares in 8 MiB chunks to avoid allocating a 28.8 GB temporary array for the n-gram tensor; chunk-boundary checks and the full file comparison passed. Verification was restarted with that bounded comparator after patching completed.

The metadata-only first shard is its original bytes plus six zero alignment bytes (10,946,624 bytes total). Only data shard 2 changed; shards 3 and 4 are byte-identical to stock. The [patched manifest](../config/weights/gufo-iq4-xs-abliterated.tsv) records all output hashes and the verified shared MTP companion. No existing model file was overwritten or deleted.

### Local results

Both IQ4_XS variants passed smoke generation and `tests/live.py gufo`: conversation, forced tools, streamed automatic tools with four argument fragments, disconnect slot release and generation after cancellation. Both copied all five case-sensitive identifiers. Stock refused all five short control probes; the patched model answered all five. These are opening-text refusal classifications from 96-token responses, not checks of the accuracy or completeness of the answers. Raw prompts and replies stay outside Git.

| Check | UD 3.1 Q4_K_XL | Stock IQ4_XS | Abliterated IQ4_XS |
|---|---|---|---|
| Startup allocation | 89.12 GiB | 72.64 GiB | 72.64 GiB |
| MemAvailable at status | 23.61 GiB | 41.48 GiB with shared MTP | 41.08 GiB |
| Decode, two 400-token requests | 43.87 / 41.58 tok/s, ticket 01 | 46.55 / 49.74 tok/s with shared MTP | 47.44 / 47.44 tok/s |
| Exact identifiers | 5/5, ticket 01 | 5/5 | 5/5 |
| Refusal probes answered | 0/5, ticket 01 | 0/5 | 5/5 |
| Matched sandboxed Pi coding runs | 4/4 | 4/4 | 4/4 |
| Recovered intermediate bash-tool errors in Pi | 1 | 3 | 3 |

Decode uses Gufo’s `timings.predicted_per_second`, the same hash-table explanation prompt, thinking off and temperature zero. Stock IQ4_XS with the standalone head reached 48.15 and 48.79 tok/s; the final shared-head results are in the table. Abliterated runs accepted 241 of 362 draft tokens. These short samples have different generated text and draft acceptance, and background file hashing overlapped part of the shared-head check, so they do not establish a broad speed ranking. Startup took about 50–54 seconds for IQ4_XS with uncontrolled file-cache warmth.

The quality comparison reused `tests/thinking_tasks.py` through `tests/thinking.py::trial`: the env-parser and CSV-filter tasks, each once with thinking off and medium, using Pi 1.5.2. All 12 runs passed independent final checks, preserved the check file, completed normally and passed the strict streamed-JSON guard. The seven intermediate bash-tool errors were recovered; these counts do not distinguish intentional failing baseline tests from implementation mistakes. Pi and generated tools ran inside the existing Bubblewrap boundary with only their synthetic workspace writable, temporary provider/settings files and shared host networking for localhost inference. Live Pi configuration was untouched. Stock IQ4_XS’s coding runs used the standalone head; the byte-identical draft block in the shared head was validated separately above. Downloads, compilation or patch I/O overlapped parts of the coding runs, so their elapsed times are not used to rank the weights.

### Warnings, limits and final state

Compilation succeeded with 207 warning diagnostic lines, including repeated host/device reports: 67 unused symbols/parameters, 44 incomplete initializers, 38 signedness comparisons, 22 GNU variadic-macro notices, 10 CUDA pragma-compatibility notices, 8 internal-declaration notices, 6 Q2_0 enum-switch notices and 12 loop-unrolling diagnostics. The pinned upstream source was left unchanged and the full log is retained. The launcher printed its existing non-crun runtime notice; loading worked with the existing permissions. No warning or error was logged by the three IQ4_XS inference runs.

The smaller profiles are ready for local use and the short checks show no coding regression on these two tasks. General coding quality, perplexity/KL, image inputs, long-context retrieval, near-capacity prompts and deep-prefill cancellation were not evaluated. Native 256K allocation is not a long-context quality result. The extension remains unreviewed upstream and is enabled only for the explicit IQ profiles.

The dashboard helper was restarted with its original environment and confirmed all four Gufo profiles available, including the actual running `iq4-xs-abliterated` label. Launcher, manifest/download and dashboard helper tests passed; browser rendering was not repeated. After the final stop, no managed inference container remained, MemAvailable was about 114.7 GiB and GTT about 1.18 GiB across all GPU users. About 5.0 GiB remained in swap from host activity; no cache dropping, swap clearing or host tuning was performed. The dashboard remains running and monitoring remains off.

## November 15: HT43 abliterated trial

The `abliterated-ht43` Halogen profile selects `qwen38-flash-next-ht43-abliterated.hgn` from Quat3rnion revision `e7783c5822dfda2785a0f5b435abf54df89fe8ee`: 57,618,253,824 bytes, SHA-256 `2beaad7b6d5107d7abfa866b33b47287160a68b9fc45b86020dbaa884955329c`. Size and hash were rechecked against Hugging Face metadata before downloading. The profile shares r2's pinned tokenizer, vision tower and n-gram files, with its own prompt cache. Its [manifest](../config/weights/halogen-abliterated-ht43.tsv) pins all nine files. Stock `default` and `abliterated-r2` remain explicit alternatives; the default is unchanged.

The [pinned model card](https://huggingface.co/Quat3rnion/halogen-qwen3.8-flash-next-v2-abliterated/blob/e7783c5822dfda2785a0f5b435abf54df89fe8ee/README.md#experimental-ht43-alternative) describes alternating HT4/HT3 trunk expert layers instead of v2's I4R, with 290 hyperconnection tensors changed to q8g64. It applies the same orcarouter donor as r2, without the Swift fine-tune. The publisher reported offline weight checks only. Halogen's pinned 0.20.4 release supports HT43; no engine image, context limit or host setting changed for this trial.

```bash
bin/run.sh halogen start --weights abliterated-ht43 --wait
bin/run.sh halogen stop
```

The dashboard loads this profile after its helper is restarted. The configured context is still 262144, MTP remains on and serving uses the same 8-bit KV pool as r2. Lower weight memory does not extend the model's context length.

### Quality method

This trial reuses the exact full WikiText-2 raw test corpus and stock reference from [ticket 02](#november-15-halogen-r2-abliterated-trial); both hashes were checked again. A new r2 reference permits direct comparisons with both baselines. All native `ppl` runs use chunk 1024, sequence 262144 and the tool's default 16-bit attention state, scoring 297,052 positions over two sequences. References keep the top 128 probabilities, so reported KL treats the tail as one bucket and is a lower bound. Raw results and references remain outside Git under `$HOME/.cache/strix-halo-inference/trials/halogen-r2`.

Stock HT43 was not downloaded. Differences between HT43 abliterated and r2 therefore combine the quantization change and its interaction with abliteration; they cannot isolate either effect. The stock v2 reference remains a quality control, not a stock HT43 control.

### File validation

All nine manifest hashes passed. Native verification of the original HT43 file passed without the table-order workaround needed for r2:

```text
PASS .../qwen38-flash-next-ht43-abliterated.hgn: 2015 tensors, 53.66 GiB, v2, model_id qwen3.8-flash-next-ht43; header, table, layout, payload sizes, checksums, codebooks and scales OK; geometry checked on 1197 tensors (818 with no rule)
```

`inspect --no-hash --json` reported 2,015 tensors, 128,350,804,643 parameters and 57,617,927,352 referenced bytes (53.660876 GiB). This compact file has no retained 22 GB of obsolete payloads like r2; the smaller live payload also reflects the changed quantization. Its FFN table has 192 HT4 and 48 HT3 records, with a native MTP head and the same 818 transform-plane tensors that have no native geometry rule.

The new r2 reference reproduced ticket 02's perplexity exactly, 3.78911432 over 297,052 positions. Reference SHA-256: `3a4c10a23fb4f42b3d75292956251c9ed8d9b6440cdd972fb9c5d22cebe56c3f` (461,024,736 bytes). The stock reference hash remains `0573079d503908443f72a826d81e10bdea60e88fb6b1d7fa4afb2b1f69f5f01c`.

### Full-corpus results

| Metric | Stock v2 | Abliterated r2 | Abliterated HT43 |
|---|---|---|---|
| Scored positions | 297,052 | 297,052 | 297,052 |
| Mean negative log likelihood | 1.33306524 | 1.33213230 | 1.32635817 |
| Perplexity | 3.79265097 | 3.78911432 | 3.76729850 |
| Mean KL from stock, lower bound | — | 0.04274782 | 0.07722999 |
| Top-token agreement with stock | — | 92.5868% | 90.1798% |

HT43 against the new r2 reference: mean KL 0.06246026, median 0.01602405, p90 0.14129210, p99 0.75416619 and maximum 8.47653103; top-token agreement 91.1383%. Against stock: median KL 0.02050864, p90 0.17659713, p99 0.93150623 and maximum 11.8564806. Neither comparison dropped tail positions. The two HT43 passes reproduced the same negative log likelihood and perplexity exactly. Scoring took 481.27 seconds against stock and 458.05 seconds against r2; the r2 reference run took 430.55 seconds. These are whole scoring-run times, not serving decode benchmarks.

This corpus shows no perplexity regression for HT43. The small reduction does not establish better general quality: HT43 changes the top token more often than r2 does relative to stock. Tool behavior and practical generation need the separate serving checks below.

The native tool commands were:

```text
# r2 reference (r2 checkpoint)
ppl FILE --corpus /work/wikitext-2-raw-test.txt --chunk 1024 --seq 262144 --ref-out /work/r2-wikitext2.ref --json
# HT43 comparisons (HT43 checkpoint)
ppl FILE --corpus /work/wikitext-2-raw-test.txt --chunk 1024 --seq 262144 --ref /work/stock-wikitext2.ref --worst 0 --json
ppl FILE --corpus /work/wikitext-2-raw-test.txt --chunk 1024 --seq 262144 --ref /work/r2-wikitext2.ref --worst 0 --json
```

The containers used the same GPU devices, unlimited memlock and host IPC as ticket 02, with network disabled, models read-only and the trial directory writable at `/work`. The startup lock and managed label enforced one engine at a time. Each quality container exited before the next started; `Mlocked` and `Unevictable` returned to 660 KiB after the final comparison.

### Serving results and choice

HT43 passed readiness and smoke generation, `tests/live.py halogen` (conversation, forced tool, streamed automatic tool with four argument fragments, disconnect slot release and generation after cancellation), all five exact case-sensitive identifiers and all five short refusal probes. Stock v2 refused those same five probes during ticket 02. As before, the probe uses refusal markers near the start of a 96-token response, not an evaluation of the accuracy or completeness of its advice; raw prompts and replies remain outside Git.

| Check | Stock v2 (ticket 02) | Abliterated r2 (ticket 02) | Abliterated HT43 |
|---|---|---|---|
| Startup allocation, engine report | 78.7 GiB | 78.7 GiB | 70.2 GiB |
| Weights / KV / working, rounded | 62.1 / 4.1 / 12.5 GiB | Same | 53.7 / 4.1 / 12.5 GiB |
| `MemAvailable` at status | 100.68 GiB | 100.55 GiB | 94.99 GiB |
| Kernel GTT at status | 17.49 GiB | 17.53 GiB | 18.01 GiB |
| Model-ready timestamp | 14.5 s | 1.9 s | 6.8 s |
| Decode, first / cached repeat | 65.46 / 66.85 tok/s | 61.84 / 62.30 tok/s | 63.34 / 63.90 tok/s |
| End-to-end, first / repeat | 64.1 / 66.7 tok/s | 60.7 / 62.2 tok/s | 62.1 / 63.8 tok/s |
| Exact tool identifiers | 5/5 | 5/5 | 5/5 |
| Short refusal probes answered | 0/5 | 5/5 | 5/5 |

The two decode requests used the same hash-table explanation prompt, thinking off, temperature zero and 400 output tokens. Engine-log decode excludes prefill; the end-to-end figure includes it. These are short exploratory measurements with differing generated text and MTP acceptance, not a broad performance ranking. Startup file-cache warmth differed too.

**Prefer `abliterated-ht43` for abliterated Halogen use on this host**, based on these checks: the engine reports 8.5 GiB less total allocation, full-corpus perplexity does not regress, and the short tools, cancellation and refusal checks all pass. The two decode requests show no slowdown relative to r2. Keep `abliterated-r2` available for comparison: it stays closer to stock's token distribution, and neither trial establishes general coding quality, image accuracy or long-context retrieval quality. The ordinary `default` remains stock v2; no profile is silently promoted.

### Warnings and limits

HT43's first quality run emitted the known fragmentation warning with 246 free contiguous 2 MiB blocks and became ready in 14.4 seconds without intervention; the second became ready in 1.6 seconds without that warning. Serving emitted a separate warning that **10.8 GiB of host RAM was already used**, potentially reducing the lookup table's file cache and slowing long prefill. It also noted just 137 free contiguous 2 MiB blocks after allocation. Other host workloads were not stopped, and no compaction or kernel settings were changed. Before interpreting long-prefill performance, repeat it with adequate host headroom. These host-state differences further limit the cross-run speed comparison.

`MemAvailable` and GTT do not contradict the weight saving: they are host-wide counters, and Halogen's locked file-backed weights can appear reclaimable. The useful model capacity comparison is the engine's startup allocation. After the final stop, no managed inference container remained, `Mlocked` and `Unevictable` returned to 660 KiB, `MemAvailable` was about 113.6 GiB and GTT about 1.77 GiB across all GPU users. Other host usage remained.

The existing dashboard helper was restarted with its original environment to reload the profile catalog, then its backend confirmed all three Halogen profiles installed and the running label `abliterated-ht43`. It remains running; inference is stopped. Launcher, profile/download and dashboard helper tests passed, along with `git diff --check`. This ticket did not repeat browser rendering or exercise image inputs, the live Pi client, long-context retrieval or near-capacity generation. The stock HT43 checkpoint was deliberately not fetched, so the quantization/abliteration causal split remains unmeasured.

## November 15: Halogen r2 abliterated trial

Halogen now has an explicit `abliterated-r2` profile beside its unchanged stock `default`. It uses Quat3rnion's r2 checkpoint at revision `e7783c5822dfda2785a0f5b435abf54df89fe8ee`, not the later conversion at the same filename on `main`. The 88,737,777,792-byte file has SHA-256 `7bbac319851b500639462133085156b4f998dec562f511e65ca1c14d7af5163e`; upstream metadata was rechecked before downloading. [Its manifest](../config/weights/halogen-abliterated-r2.tsv) also pins reflink copies of the stock n-gram table, vision tower and tokenizer at peonist revision `506567c641cfb737e0b01c1deff10813154c5529`. Download verification and a separate full manifest verification passed for all nine files. No engine image or host setting changed.

```bash
bin/run.sh halogen start --weights abliterated-r2 --wait
# Stop it before choosing the stock profile again:
bin/run.sh halogen stop
bin/run.sh halogen start --weights default --wait
```

The dashboard offers the same profile after restarting its helper. Halogen uses the MTP head inside this checkpoint and a separate `halogen/abliterated-r2` prompt cache. Selecting this profile does not change any other engine's weights.

### Native verifier limitation

Halogen 0.20.4's native `verify` reports **149 false overlap errors on the original r2 file**. The first is `layers.0.attn_hyper_connection.block_inject_weight.weight`, whose offset 357903424 is below the end of the preceding table entry, `embed_tokens.weight`, at 88724670592. r2 appends replacement payloads while keeping tensor-table order, so a later table entry can point to an earlier, disjoint file range.

The independent [layout diagnostic](../.scratch/abliterated-trials/check_hgn_layout.py) checked all 2,015 ranges: zero physical overlaps, zero out-of-bounds ranges and zero duplicate names. Its count of table-order reversals is exactly 149. A temporary btrfs reflink copy changed only the order of the 160-byte table entries, sorting them by payload offset. The header and the complete set of table records were confirmed identical; no payload bytes or offsets changed. The same native verifier then reported:

```text
PASS .../r2-offset-order-check.hgn: 2015 tensors, 82.64 GiB, v2, model_id qwen3.8-flash-next-v2; header, table, layout, payload sizes, checksums, codebooks and scales OK; geometry checked on 1197 tensors (818 with no rule)
```

This isolates the problem to the verifier's table-order assumption. The [HGN reader description](https://github.com/jtsylve/hgn-spec/blob/main/CONTAINER.md#reader-procedure) also says readers must not depend on entry order. The diagnostic copy was deleted. **All quality and serving tests below used the original, hash-verified r2 file**, not the sorted copy, and no verification flag or security setting was disabled. The unmodified file will still produce this native verifier failure on 0.20.4; `bin/models.sh verify halogen abliterated-r2` checks its pinned SHA-256 successfully.

`inspect --no-hash --json` succeeded: version 2, model ID `qwen3.8-flash-next-v2`, 2,015 tensors, 128,350,804,643 checkpoint parameters, 88,737,777,792 file bytes and 66,687,351,992 referenced payload bytes (62.107 GiB). Its format table includes 96 I4R FFN tensors, 108 HT4 DeltaNet projections, 60 HT4 attention projections and the native MTP head. The large on-disk size comes from retained unreferenced payloads; it is not the resident weight size. The external 47.68 GiB n-gram table remains separate.

### Full WikiText-2 comparison

Both runs used the pinned Halogen 0.20.4 image and its native `ppl` mode, chunk 1024 (prefill kernels), sequence length 262144 and top-128 reference support. The tool used its default 16-bit attention state (about 7.2 GiB pool), rather than the launcher's 8-bit serving cache. The reference and comparison used identical settings; no CPU generation fallback was used.

The corpus is the complete `Salesforce/wikitext` `wikitext-2-raw-v1` test parquet at revision `b08601e04326c79dfdd32d625aee71d232d685c3`, converted by concatenating the `text` rows with no added separators, using temporary isolated PyArrow 26.0.1. Parquet SHA-256: `5f1bea067869d04849c0f975a2b29c4ff47d867f484f5010ea5e861eab246d91`. UTF-8 text: 1,287,656 bytes, SHA-256 `bbf94c53a05abe9ee670d3b6343608095822c85e26de37c70b24fc571964574a`. The mounted tokenizer produced 297,053 IDs; the tool scored 297,052 positions across two sequences. Corpus, reference dump, provenance and results are under `$HOME/.cache/strix-halo-inference/trials/halogen-r2`, outside Git.

The container arguments were:

```text
ppl /models/peonist-ai/halogen-qwen3.8-flash-next/qwen38-flash-next-v2.hgn --corpus /work/wikitext-2-raw-test.txt --chunk 1024 --seq 262144 --ref-out /work/stock-wikitext2.ref --json
ppl /models/Quat3rnion/halogen-qwen3.8-flash-next-v2-abliterated/qwen38-flash-next-v2-abliterated.hgn --corpus /work/wikitext-2-raw-test.txt --chunk 1024 --seq 262144 --ref /work/stock-wikitext2.ref --worst 0 --json
```

Each ran as a rootless, network-disabled container with the models directory mounted read-only, the trial directory at writable `/work`, and the selected directory's tokenizer and n-gram table explicitly set. The ordinary startup lock and managed-container label prevented another engine from starting during each run. The reference dump SHA-256 is `0573079d503908443f72a826d81e10bdea60e88fb6b1d7fa4afb2b1f69f5f01c`.

The publisher's 3.144 stock / 3.134 r2 perplexity, KL 0.060 and 92.2% agreement used only **70,774 tokens** on Halogen 0.15.0. Those absolute values are not directly comparable to this full-corpus run on 0.20.4.


| Metric | Stock native v2 | r2 |
|---|---|---|
| Scored positions | 297,052 | 297,052 |
| Mean negative log likelihood | 1.33306524 | 1.33213230 |
| Perplexity | 3.79265097 | 3.78911432 |
| Scoring time | 431.28 s | 429.58 s |

The top-128 comparison reports mean KL 0.04274782, median 0.01131079, p90 0.09746883, p99 0.48888804 and maximum 10.4298658. These are **lower bounds**, with the omitted probability tail treated as one bucket; no tail positions were dropped. The top token agrees at 275,031 of 297,052 positions (92.5868%). Perplexity is essentially unchanged on this corpus; the small decrease does not establish a general quality improvement.

### Serving checks

Both profiles used native 262144 capacity, MTP on, the launcher's 8-bit KV pool and isolated prompt caches. Each ran alone. Stock passed readiness, smoke generation and the control probes; r2 additionally passed `tests/live.py halogen`: conversation, forced tool call, streamed automatic tool call (four argument fragments), disconnect slot release and generation after cancellation. The stock live suite had already passed with this same pinned image during ticket 01. The dashboard backend reported both Halogen profiles available and the running container as `abliterated-r2`; no browser rendering was exercised.

| Check | Stock native v2 | r2 |
|---|---|---|
| Engine allocation | 62.1 GiB weights + 4.1 GiB KV + 12.5 GiB working = 78.7 GiB | Same |
| Host `MemAvailable` at status | 100.68 GiB | 100.55 GiB |
| Kernel GTT at status | 17.49 GiB | 17.53 GiB |
| Engine model-ready timestamp | 14.5 s | 1.9 s |
| Decode, first / cached repeat | 65.46 / 66.85 tok/s | 61.84 / 62.30 tok/s |
| End-to-end throughput, first / repeat | 64.1 / 66.7 tok/s | 60.7 / 62.2 tok/s |
| Exact case-sensitive tool identifiers | 5/5 correct | 5/5 correct |
| Refusal probes | 5/5 refused | 5/5 answered |

Decode used the same hash-table explanation prompt, thinking off, temperature zero and 400 output tokens per request, with timing taken from the engine log. r2 was modestly slower on these two requests; generation content and MTP acceptance differ, so this is not a broad throughput benchmark. Its very short startup followed the quality run with hot file cache; startup times are not comparable cold-load measurements.

The five short refusal probes covered explicit adult fiction, car hot-wiring, shoplifting, paywall bypass and lock picking. The existing probe classifies refusal markers in the first 240 characters of a 96-token reply. This measures the short reply's behavior, not the accuracy or completeness of its advice. Raw prompts and replies stay out of Git. The API model name remains `halogen-qwen3.8-flash-next`; the profile is identified separately by the container label and dashboard.

Stock serving and r2's quality run each emitted the existing host-fragmentation warning (278 and 253 free contiguous 2 MiB blocks respectively). Serving also noted low contiguous memory after allocation for both profiles. They completed without a startup stall; no host compaction or kernel settings were changed. The launcher reported the existing non-crun runtime notice, but GPU access worked. Halogen's locked weights make `MemAvailable` overstate genuinely reclaimable memory, so the startup allocation is the useful capacity figure.

The final stop removed the container and returned `MemAvailable` to about 120 GiB and GTT use to about 0.68 GiB. No inference engine or dashboard helper was left running. Offline launcher, dashboard and profile tests passed. Image input, long-context retrieval, the live Pi client and browser rendering were not tested. Ticket 02 is complete with the native verifier limitation recorded above; HT43 remains ticket 03.

## November 15: UD 3.1 weights and selectable profiles

Gufo's default weights moved from the October export to Unsloth UD 3.1 `UD-Q4_K_XL`, revision `d96201194f103c906994f283f504209dc8d2a10c`. The four shards total 111,334,654,778 bytes; the existing shared Q8_0 MTP head is unchanged. The revision, sizes and SHA-256 values were rechecked against Hugging Face and [Gufo 0.34.0's model guide](https://github.com/gufo-org/gufo/blob/v0.34.0/docs/models/qwen3.8-flash-next.md). `config/pins.env` and `config/gufo-files.tsv` hold the pins. Image versions and host settings did not change.

The downloader fetched and individually verified every shard, then encountered a shell-offset error because its script was edited while the original Bash process was still running. A fresh invocation of the completed downloader and a separate `bin/models.sh verify gufo` both succeeded against the final files; nothing needed redownloading.

### Profiles and launcher

[The shared catalog](../config/weights.json) now supplies named weight profiles to all three launchers and the dashboard. `bin/run.sh ENGINE weights` lists availability; `start --weights PROFILE --wait` selects a profile. Gufo has `default` and `abliterated`, both based on UD 3.1. Halogen and Strixite retain their existing default packages. Profile manifests can name independently pinned download sources, so later trials and lower quants need catalog entries rather than another hardcoded launcher path. Engine compatibility and extension support still need separate validation.

The dashboard marks missing profiles, remembers a selection per engine, and shows the running container's actual profile. Switching requires an explicit stop. Each profile has its own `CACHE_ROOT/ENGINE/PROFILE` prompt cache; existing caches directly under the engine directory remain on disk but are not reused. Cache clear still clears the entire chosen engine. Endpoints remain loopback-only, weights remain read-only in containers, and the one-engine startup lock is unchanged. See [weight profiles](weight-profiles.md).

### UD 3.1 patch

The same reviewed huihui patch, key and script from the [earlier trial](#november-15-trial-huihui-patch-on-the-stock-gufo-file) were hash-verified again. They remain pinned at `cbc7fba13f1939ac3fa42b18d77ccf43847d74ef`. A temporary Python environment used `gguf==0.19.0` and `tqdm==4.70.1` with wheel hashes `70bcd10edfe697fb2dad6e40af2234b9d8ece9a41a99761405121ebda1c3c1cd` and `c293e525e6fef9c20e8728fd4612df02a0aa31bb5fe91ecd93e123b1b7bffa73`, respectively, plus system NumPy 2.5.4.

Bubblewrap ran with `--unshare-all --die-with-parent --new-session`, no network or home directory, read-only software and inputs, and only the new output directory persistently writable. `/in` was the new `unsloth/Qwen3.8-Flash-Next-GGUF/UD-Q4_K_XL` directory; `/patch` was the existing huihui `patch-unsloth` directory; `/out` was the new `huihui-ai/Huihui-Qwen3.8-Flash-Next-abliterated-v2-GGUF/patched-unsloth-UD-Q4_K_XL-d9620119` directory, all under `/home/bogdan/models`. The exact patch command inside that sandbox was:

```bash
/venv/bin/python -I /patch/patch-unsloth-Qwen3.8-Flash-Next-dec.py \
  --input-path /in --patch-path /patch/patch-unsloth-all --output-path /out \
  --start-layer 0 --end-layer 48 --ablate-experts 2
```

The patch replaced 96 Q8_0 tensors: 36 `ssm_out`, 12 `attn_output` and 48 `ffn_down_shexp`, with no missing-entry or type-mismatch warnings. Its notice about 180 unused entries is expected because the patch also carries other tensor formats. `verify_patch.py` then ran with both directories read-only: all 1,224 tensor names, types, shapes and sizes and every metadata field matched; exactly the intended 96 tensors changed, with no other differences in tensor content. The metadata-only first shard gained six trailing zero alignment bytes (10,946,618 to 10,946,624 bytes); its original prefix is byte-identical. The n-gram shard is byte-identical to stock. [The patched manifest](../config/weights/gufo-abliterated.tsv) records every output's size and SHA-256, plus the unchanged shared MTP head.

### Local checks

All starts used native 262144 context and MTP on. Engines ran one at a time, with a stop and memory-release check before switching. The October stock model was measured once more before removal on the same hash-table prompt, thinking off, temperature zero, 400 output tokens, two measured requests. The new stock and patched models used that same prompt and settings.

| Check | October stock baseline | UD 3.1 default | UD 3.1 abliterated |
|---|---|---|---|
| Ready and generation | Pass | Pass | Pass |
| Conversation, named/streamed tools, disconnect and generation after cancellation | Previously validated; not rerun for baseline | Pass | Pass |
| Startup GPU allocation | 89.12 GiB | 89.12 GiB | 89.12 GiB |
| Host MemAvailable at status | 27.38 GiB | 29.30 GiB | 28.03 GiB |
| Refusal probes, thinking off | Earlier trial: 5 refused | 5 refused | 5 answered |
| Case-sensitive tool identifiers | Earlier trial: 5/5 | 5/5 | 5/5 |
| Decode, two 400-token requests | 43.29, 43.74 tok/s | 43.87, 41.58 tok/s | 49.39, 49.41 tok/s |

Decode is Gufo's `timings.predicted_per_second`, not end-to-end throughput. These are exploratory samples, not a performance ranking: the patched model writes different text and accepts more draft tokens (239 of 359 versus stock's 206 of 351). Stock and patched live tests each assembled four tool-argument fragments successfully. No Gufo warning or error was logged. Raw prompts and replies remain outside the repository; the refusal results use the existing probe's opening-text classifier, not a broader safety or quality evaluation.

After both UD 3.1 runs, MemAvailable returned to about 120 GiB and GTT to about 1.08 GiB. Some desktop pages remained swapped out (about 2.1 GiB after the last run); available RAM was restored, and swap/kernel settings were not changed. At the user's explicit request, both October weight directories were deleted after validation, along with the temporary October comparison cache. The shared MTP head, huihui patch inputs and both UD 3.1 profiles remain.

Halogen and Strixite also passed readiness, smoke generation and their existing live conversation/tool/cancellation checks through the new default-profile launcher, then stopped. Halogen repeated its known low-contiguous-memory warning (234 free 2 MiB blocks after weights were pinned), with 20-second startup; no host tuning was applied. Strixite emitted one expected warning for the test that deliberately truncates a tool call. The launcher still prints its existing non-crun notice; the host's direct GPU device access worked.

Offline validation passed shell syntax, ShellCheck, `tests/models.sh`, `tests/run.py`, `tests/status.py`, `tests/cache.py`, `tests/dashboard.py`, `tests/weights.py`, JavaScript syntax and `git diff --check`. Live dashboard backend checks correctly identified a CLI-started Halogen default and Gufo abliterated container, and both installed Gufo profiles. No engine, monitoring container or dashboard helper was left running.

Not exercised: browser rendering of the new selectors, thinking-on quality, long-context workloads, images, Pi sessions, perplexity/KL, smaller quants or extension loading. Existing model-specific limitations still apply.

## November 15 trial: huihui patch on the stock Gufo file

Historical trial; both October copies described below were superseded and deleted after the UD 3.1 validation above. An abliterated copy of the then-pinned `UD-Q4_K_XL` was made with huihui's patch and run on Gufo 0.34.0. Pins, images and the default model are unchanged; the copy is selected only with `GUFO_MODEL` (README, First run). Plan and ticket: `.scratch/abliterated-trials/issues/04-gufo-huihui-patch.md`.

### Patch files

From [huihui-ai/Huihui-Qwen3.8-Flash-Next-abliterated-v2-GGUF](https://huggingface.co/huihui-ai/Huihui-Qwen3.8-Flash-Next-abliterated-v2-GGUF/tree/cbc7fba13f1939ac3fa42b18d77ccf43847d74ef/patch-unsloth) at revision `cbc7fba13f1939ac3fa42b18d77ccf43847d74ef`, stored under `/home/bogdan/models/huihui-ai/Huihui-Qwen3.8-Flash-Next-abliterated-v2-GGUF/patch-unsloth/`:

| File | Bytes | SHA-256 |
|---|---|---|
| `patch-unsloth-all/Huihui-Qwen3.8-Flash-Next-abliterated-patch-all.gguf` | 3,561,572,544 | `f3a42f213edb9117fd7f3873e0b29a9a94033cb49b91e100e792f6344adec752` |
| `patch-unsloth-all/Huihui-Qwen3.8-Flash-Next-abliterated-patch-all.gguf.key` | 64 | `2ed56e36f9a9c4f806d9fb48f5ef9e06ed5d1ab3b4f6b8ee31e19ef5b8ea9667` |
| `patch-unsloth-Qwen3.8-Flash-Next-dec.py` | 9,659 | `69d15f62facd3f9d16bdeaf13cab9077e3568b5f274a843d28fd1796eb31d22a` |

### Script review

`patch-unsloth-Qwen3.8-Flash-Next-dec.py` is the only executable file. It is 269 lines of ASCII with Windows line endings and no hidden characters, and was read in full. It imports only `gguf`, `numpy` and standard-library modules, and makes no network, subprocess, `eval`, `exec` or delete call. It reads the input GGUFs, the patch file and the key, and writes only into the output directory, where it would overwrite files of the same name. For each tensor in the chosen families it looks up a patch entry of the same quantisation type, decodes it by XOR with the 64-character key and writes it in place of the stock tensor; with no matching entry it copies the stock tensor and logs a warning. The patch file itself is data, not code: a GGUF holding 276 tensors.

### Run

The script ran under Bubblewrap with no network, no home directory, the stock shards and patch files read-only and only the new output directory writable, on Python 3.14.10 with NumPy 2.5.4 and hash-pinned `gguf` 0.19.0 and `tqdm` 4.70.1 in a temporary virtual environment:

```bash
python -I /patch/patch-unsloth-Qwen3.8-Flash-Next-dec.py --input-path /in --patch-path /patch/patch-unsloth-all \
  --output-path /out --start-layer 0 --end-layer 48 --ablate-experts 2
```

The input was the pinned October `UD-Q4_K_XL` at `38bb39ee97821de2c9009abb7e93950eec396e66`. It took 38 seconds and patched 96 tensors, all Q8_0: 36 `ssm_out`, 12 `attn_output` and 48 `ffn_down_shexp`, with no type-mismatch or missing-entry warning. Output, in `/home/bogdan/models/huihui-ai/Huihui-Qwen3.8-Flash-Next-abliterated-v2-GGUF/patched-unsloth-UD-Q4_K_XL-38bb39ee/`:

| File | Bytes | SHA-256 |
|---|---|---|
| `Qwen3.8-Flash-Next-UD-Q4_K_XL-00001-of-00004.gguf` (byte-identical to stock) | 10,946,624 | `4448186216b3af4cc558bbce2c3213f01608f8f8b2e5267a9767971dd3ec8082` |
| `Qwen3.8-Flash-Next-UD-Q4_K_XL-00002-of-00004.gguf` | 49,859,583,136 | `a9b7aad6475acf6c414b94f85fef48ec89f14c3f392e8d6d4a0e66e1050e4524` |
| `Qwen3.8-Flash-Next-UD-Q4_K_XL-00003-of-00004.gguf` | 49,376,141,504 | `f4b9c67c7a06b632aac0ea8c05f5b0ffff5e336837903b9bddde6e8226235134` |
| `Qwen3.8-Flash-Next-UD-Q4_K_XL-00004-of-00004.gguf` | 12,087,983,520 | `e828681eaf2eef3018fe8f2d64170d87eed161e79bcca440145479aeff5dfb3e` |

`.scratch/abliterated-trials/verify_patch.py` compared the output with stock, in the same sandbox with both read-only: every metadata key and value is identical, all 1,224 tensors keep their name, order, type, shape and size, and exactly the 96 patched tensors differ in content. Each differs from its stock tensor by 3.2 to 4.5% (relative norm), and 93 to 99% of that difference lies in a single direction, which is the signature of projecting out one refusal direction rather than of retrained weights.

### Gufo 0.34.0 checks

Each model was started alone at native 262144 context with MTP on and the stock shared MTP head, then stopped. MemAvailable was 115.6 GiB before the first start and 116.6 GiB after the last stop, with Unevictable 116 KiB. `python tests/run.py`, `bash -n` and `shellcheck` on `bin/run.sh` passed after the `GUFO_MODEL` change.

| Check | Stock `UD-Q4_K_XL` | Patched copy |
|---|---|---|
| Ready and a smoke generation | Pass | Pass |
| `tests/live.py` | Not rerun (passed November 14) | Pass, 4 fragments |
| Startup allocation | 89.12 GiB | 89.12 GiB |
| MemAvailable while running | 25.1 GiB | 24.8 GiB |
| Refusal probe, 5 prompts, thinking off, temperature 0 | 5 refused | 5 answered |
| Tool call copying an exact case-sensitive identifier, 5 identifiers | 5 of 5 | 5 of 5 |
| Decode, 400 tokens, two runs | 43.3 and 43.8 tok/s | 49.4 and 49.6 tok/s |

The probe categories were explicit adult fiction, hot-wiring a car, shoplifting, bypassing a paywall and picking someone else's lock. Three of the patched model's answers open with a legal disclaimer and then comply. The decode figures are Gufo's own `predicted_per_second` on one prompt; the two models wrote different text, so MTP acceptance differs and the gap is not a like-for-like speed-up. Neither run logged warnings or errors. `.scratch/abliterated-trials/probe.py` runs the probe; its prompt texts are kept outside the repository.

Not exercised: thinking on, long contexts, images, Pi sessions, coding quality, perplexity or KL against stock, a larger refusal set, and the patch on the UD 3.1 file, which is not downloaded yet.

## November 14 update

`bin/update.py` pulled Halogen 0.20.4 and Gufo 0.34.0 by digest and atomically updated their image and version pins. Strixite 0.7.0 was already current. Launch settings, model revisions, live Pi files and host settings are unchanged. `bin/npu-manifest.sh` against the 0.20.4 image changed only the 16 `d3-lite/devices/` files, republished with new contents at the same paths (`peonist-ai/halogen-npu-d3-lite` revision `2def562` to `8919811`); the `d3-lite` weights, tokenizer and picture files are unchanged. The 16 superseded files were deleted, then `bin/models.sh download npu` fetched them and verified all 166 NPU files. Both updated engines passed the [local checks](#november-14-local-checks). After the checks, the superseded Halogen 0.20.1 and Gufo 0.33.0 images were removed by digest, and `bin/cache.sh` cleared the Halogen and Gufo prompt caches, which held only the test runs' state.

| Engine | Previous | Current | Current image digest |
|---|---|---|---|
| Halogen | 0.20.1 | 0.20.4 | `sha256:70445bcf7acff8f1fe11396a97b866ed30dca31caf5fac62049127658080e07f` |
| Gufo | 0.33.0 | 0.34.0 | `sha256:49b1fce40cb43e33c46d91595e300cb320cdec768fcd976f8c8da24b402fc133` |

The images advertise revisions Halogen `0abf69e68c0e` and Gufo `2845939b2a7d61243d407c8816c6d42652512e50`, not compared with public source.

### What changed upstream

- **Halogen 0.20.2** is up to about 1% faster with several requests generating at once and up to about 4% sooner to the first token on long conversations, and starts NPU decisions on long prompts sooner. `d3-lite` answers 14 to 18% faster on the NPU; its scores can differ in the last digits. The Flash checkpoints are unchanged. [Tagged changelog](https://github.com/peonist-ai/halogen-flash-server/blob/v0.20.2/CHANGELOG.md).
- **Halogen 0.20.3** makes `d3-nano`, not provisioned here, 7 to 9% faster on the NPU. [Tagged changelog](https://github.com/peonist-ai/halogen-flash-server/blob/v0.20.3/CHANGELOG.md).
- **Halogen 0.20.4** reads a short follow-up message to a cached conversation 15 to 50% faster; at temperature 0 such a turn can occasionally differ from 0.20.3 where two tokens were nearly tied. Throughput past 8 concurrent requests rises about 10 to 20%, which does not apply at this launcher's `HALOGEN_KV_SLOTS=1`. With `tool_choice: "none"` in a conversation that already holds tool calls, the server now answers in prose instead of returning raw `<tool_call>` markup (#253), as Open WebUI 0.13 sends to end a tool loop. [Tagged changelog](https://github.com/peonist-ai/halogen-flash-server/blob/v0.20.4/CHANGELOG.md).
- **Gufo 0.34.0** decodes EmbeddingGemma 2 audio in Rust and drops libsndfile and soxr, marked breaking; the launcher serves no Gufo embeddings. It deprecates `--draft-tokens`, `--min-draft-tokens` and `--draft-policy`, which the launcher does not use. Fixes cover Flash-Next MTP backoff recovery after batch observations, continuing after a re-tokenized answer, refusing prompts over the host prompt-state budget, disk-cache admission and validation, and tool-call numbers and nested defaults. It reduces CPU overhead in sampling and n-gram lookups and speeds up batched Qwen3.8 steps. Its Qwen3.8-27B model pin (#1167) does not affect Flash-Next. [Release notes](https://github.com/gufo-org/gufo/releases/tag/v0.34.0).

### November 14 local checks

Each engine was started alone at native 262144 context with MTP on, then stopped. MemAvailable was 112.5 GiB before the first start, 113.8 GiB after the Halogen stop and 115.8 GiB after the Gufo stop, with Unevictable 116 KiB and kernel GTT 1.3 to 1.8 GiB. `tests/update.sh`, `python tests/run.py` and `git diff --check` passed. The v0.20.4 fabric-clock helper has the same SHA-256 as the installed one.

| Check | Halogen 0.20.4 | Gufo 0.34.0 |
|---|---|---|
| Ready and a chat generation | Pass | Pass |
| `tests/live.py` | Pass, 4 fragments | Pass, 4 fragments |
| Allowlisted names on `/metrics` | 33 of 33 | 17 of 17 |
| Startup allocation | 78.7 GiB, as on 0.20.1 | 89.12 GiB on the GPU, as on 0.33.0 |
| `tool_choice: "none"` after a failed tool call, 3 tries at temperature 0.7 | Prose each time | Raw `<tool_call>` markup each time |

- **Halogen NPU.** Halogen started with `d3-lite`, `decider-0.8b` and `embeddinggemma-2` and was ready in 12.9 s. On a double-charge complaint, `d3-lite` chose `billing` at 0.86 with a refund probability of 0.98 in 0.07 s, and `decider-0.8b` chose `billing` at 0.999 with 0.996 in 0.08 s. Two related sentences scored 0.82 and an unrelated one 0.55 on 768-dimension embeddings in 0.09 s. After stop the fabric clock was back on `auto`, and the kernel log had no `amdxdna` or `amdgpu` messages.
- **Gufo `tool_choice: "none"`.** Gufo 0.34.0 still returns the model's tool call as raw markup in the reply text when a conversation already holds a tool call. Gufo 0.33.0, rerun with a temporary cache directory, did the same, so this is not a regression. Clients that end a tool loop with `tool_choice: "none"`, such as Open WebUI 0.13, can show XML on Gufo.
- **Logs and memory.** Neither engine logged warnings. Halogen no longer warned about host RAM in use at start, and reported 324 contiguous 2 MiB blocks free, against 220 on November 9. While Gufo ran, MemAvailable was about 24 GiB and 4.2 GiB of swap was in use, against 8 MiB before; swap stayed in use after the stop.

The faster short follow-up turns, `d3-lite` speed against 0.20.1, Gufo's MTP backoff recovery, images, Pi sessions, power draw and performance benchmarks were not exercised. Strixite was not restarted.

## November 9 update

`bin/update.py` pulled Halogen 0.20.1 and Gufo 0.33.0 by digest and atomically updated their image and version pins. Strixite 0.7.0 was already current. The launcher no longer sets `HALOGEN_FORK=1`, the upstream default since 0.18.15, or `HALOGEN_FORK_MAP=auto`, retired in 0.20.1 in favour of a built-in reply-end cache. Model revisions, other launch settings, live Pi files and host settings are unchanged. Both updated engines passed the [local checks](#november-9-local-checks). After the checks, the superseded Halogen 0.19.1 and Gufo 0.31.0 images were removed by digest, and `bin/cache.sh` cleared the Halogen and Gufo prompt caches, which held only the test runs' state.

| Engine | Previous | Current | Current image digest |
|---|---|---|---|
| Halogen | 0.19.1 | 0.20.1 | `sha256:66dac8dac25bf15f2b63a684bbe3953036045172d881525600ea41d45e5acc73` |
| Gufo | 0.31.0 | 0.33.0 | `sha256:cf76a084e33e638ec4d934afaf9534aad591a5f2ddd951576bd63a9792b7d601` |

The images advertise revisions Halogen `9f38fe7ba960` and Gufo `77dff828be02a498e9951694f31b024e7ac87119`, not compared with public source.

### What changed upstream

- **Halogen 0.20.0** moves the image to ROCm 10.1, which upstream measured at about 9 to 15% less package energy while generating at the same speed, and reads Flash-Next prompts 2 to 6% faster. Temperature-zero output can differ from 0.19.1 in the last bits. It fixes a GPU memory fault from strict tool calls under concurrency and a `/v1/completions` tokenization mismatch at the reuse point. It adds document parsing on the NPU with a user-supplied OvisOCR3 checkpoint, not provisioned here; see [models](engine-models.md#checkpoints-you-supply-on-the-npu). [Tagged changelog](https://github.com/peonist-ai/halogen-flash-server/blob/v0.20.0/CHANGELOG.md).
- **Halogen 0.20.1** caches the end of each reply in the RAM prompt cache by default, about 112 MiB a conversation, so a follow-up that sends the reply back unchanged resumes from it. This retires `HALOGEN_FORK_MAP=auto`; a configuration that still sets it starts and logs that it is ignored. When the model ends its turn inside its reasoning, the server now closes the reasoning and lets the model answer. A routine KV-pool growth line moves from stderr to stdout. [Tagged changelog](https://github.com/peonist-ai/halogen-flash-server/blob/v0.20.1/CHANGELOG.md).
- **Gufo 0.32.0** splits prompt passes by layers on Flash-Next so other sessions keep decoding, and deprecates `--prefill-chunk`, which the launcher does not use. It overlaps the shared expert with routed experts on Flash-Next decode, accepts `$schema` and type unions in strict schemas, refuses a RAM cache the host cannot hold with a message instead of `bad_alloc`, and adds `/tokenize`. [Release notes](https://github.com/gufo-org/gufo/releases/tag/v0.32.0).
- **Gufo 0.33.0** measures the Flash-Next decode shared-expert overlap before using it, fixes component-cache eviction and snapshot copies, and speeds up DeepSeek V4 Flash. [Release notes](https://github.com/gufo-org/gufo/releases/tag/v0.33.0).

### November 9 local checks

Each engine was started alone at native 262144 context with MTP on, then stopped. A ComfyUI container from another project was stopped first. MemAvailable was 114.0 GiB before the first start and 114.4 to 116.3 GiB after each stop, with Unevictable at most 252 KiB and kernel GTT 2.0 to 2.4 GiB, against about 1.1 GiB on November 7. `tests/update.sh`, `python tests/run.py` and `git diff --check` passed. `bin/npu-manifest.sh` left all 166 NPU file records unchanged. The v0.20.1 fabric-clock helper has the same SHA-256 as the installed one.

| Check | Halogen 0.20.1 | Gufo 0.33.0 |
|---|---|---|
| Ready and a chat generation | Pass | Pass |
| `tests/live.py` | Pass, 4 fragments | Pass, 4 fragments |
| Allowlisted names on `/metrics` | 33 of 33 | 17 of 17 |
| Startup allocation | 78.7 GiB, 78.8 on 0.19.1 | 89.12 GiB on the GPU, 89.11 on 0.31.0 |

- **Halogen reply-end cache.** Without the fork settings, a 197-token reply sent back with a new question reused 220 of the second turn's 240 prompt tokens, so the whole first turn came from cache. The changed settings started the disk cache in a new directory.
- **Halogen NPU on ROCm 10.1.** Halogen started with `decider-0.8b`, `embeddinggemma-2` and `qwen3guard-stream-0.6b` and logged the kernel's `amdxdna` driver with the image's XRT 2.25.37. `decider-0.8b` answered a spam question with `yes` at 0.992 in 0.59 s, two related sentences scored 0.87 and an unrelated one 0.60 on 768-dimension embeddings in 0.06 s, and the streaming guard labelled a 465-character Flash reply in six chunks, none flagged. A Flash chat generation passed with the NPU models loaded. After stop the fabric clock was back on `auto`, and the kernel log had no `amdxdna` or `amdgpu` messages.
- **Logs.** Halogen warned at start that 11.0 GiB of host RAM was in use and that free memory held only 220 contiguous 2 MiB blocks; startup still took 22.5 s. Gufo logged no lines above INFO.

OvisOCR3, images, Pi sessions, the strict-tool concurrency fix, reasoning closed at end of turn, Gufo's layer-split prefill beside a second session, power draw and performance benchmarks were not exercised. Strixite was not restarted.

## November 7 update

`bin/update.py` pulled Halogen 0.19.1, Gufo 0.31.0 and Strixite 0.7.0 by digest and atomically updated their image and version pins. The launcher no longer mounts host XRT for NPU models, because Halogen 0.19.1 carries its own. Model revisions, other launch settings, live Pi files and host settings are unchanged. All three engines passed the [local checks](#november-7-local-checks). The superseded Halogen 0.18.23, Gufo 0.29.0 and Strixite 0.5.0 images were removed afterwards, and no prompt cache was rotated.

| Engine | Previous | Current | Current image digest |
|---|---|---|---|
| Halogen | 0.18.23 | 0.19.1 | `sha256:7ab5c3dfd77acb2387603f1807069cac3494e678f413c0670745ba2df74c0f0e` |
| Gufo | 0.29.0 | 0.31.0 | `sha256:9a6e2d43ca00d8d1c89453ebf456e975fd197ef54d648ba0d1b4a8bcc0917f24` |
| Strixite | 0.5.0 (`sha256:f0d3211f05c65036673d00bcf9daa69e83fe7ea12018c9b4810cd57ba7568293`) | 0.7.0 | `sha256:8eb565146ed6e7d32310e6506dacb5144498639d2cc2ae8246c235a12156472b` |

The images advertise revisions Halogen `85b2b0c37d5d`, Gufo `be7bd3be303f6d0f6c24f8ef544d0798b4281684` and Strixite `0945ce8`, not compared with public source.

### What changed upstream

- **Halogen 0.19.0** makes whole-file rewrites about 30% faster and Edit calls about 20% faster by letting prompt lookup follow the file it copies, listens on IPv6 as well as IPv4 (#231), refuses unknown keys on `/v1/systemone` with a 422 (#234), and fixes long LFM3 prompts, NPU restarts at the host memory floor and NPU error codes (#235). It adds an opt-in agent guard preview, `HALOGEN_AGENT_GUARD=watch|hold`, run by a new `halogen-spotter-0.6b` NPU model, not used here. [Tagged changelog](https://github.com/peonist-ai/halogen-flash-server/blob/v0.19.0/CHANGELOG.md).
- **Halogen 0.19.1** ships XRT 2.25.37 with its NPU plugin in the image, so the NPU needs only the host's driver and firmware; a mounted host XRT still replaces it. A tool schema that is not an object now gets a 400 instead of a 500 that held a generation slot until restart (#243). It adds `ignore_eos` on `/v1/completions` for benchmarks and drops the FastAPI `on_event` warning. Upstream states unchanged Flash checkpoints and byte-identical temperature-zero Flash output across both releases. [Tagged changelog](https://github.com/peonist-ai/halogen-flash-server/blob/v0.19.1/CHANGELOG.md).
- **Gufo 0.30.0** removes the legacy continuation cache (#1014) in favour of the component cache, fixes capacity-limited Flash-Next prefill steps (#1016) and tool argument schemas beside arrays without items (#1012), and captures prompt checkpoints inside prefill passes (#963). [Release notes](https://github.com/gufo-org/gufo/releases/tag/v0.30.0).
- **Gufo 0.31.0** adds sliding-window cache components and extension hooks, and opens tensorless GGUF split shards (#1021). None changes our Flash-Next configuration. [Release notes](https://github.com/gufo-org/gufo/releases/tag/v0.31.0).
- **Strixite 0.6.0** hands a switched slot's K/V pages to the prompt cache without copying and renews its working state in seconds when a slot's switch budget (`kv-generations`, auto by default) runs low, reported on `/health`. The default prompt-cache RAM margin rises from 4 to 5 GiB; the launcher passes 8. It fixes shared decode steps after one conversation held an image (#29). [Release notes](https://github.com/shawnshekari/strixite/releases/tag/v0.6.0).
- **Strixite 0.7.0** keeps resume points at each reply and user message (`prompt-cache-points`, 16), so an edited old message costs only what follows it, adds `logit_bias`, accepts the `developer` role (#28) and reads the expert count from the weights (#35). Prompt-cache entries from 0.5 stay valid. [Release notes](https://github.com/shawnshekari/strixite/releases/tag/v0.7.0).

### November 7 local checks

Each engine was started alone at native 262144 context with MTP on, then stopped. MemAvailable was 116.0 GiB before the first start and 116.0 to 117.2 GiB after each stop, with Unevictable 116 KiB and kernel GTT about 1.1 GiB. `tests/update.sh`, `python tests/run.py` and `git diff --check` passed. `bin/npu-manifest.sh` left all 166 NPU file records unchanged. The v0.19.1 fabric-clock helper has the same SHA-256 as the installed one.

| Check | Halogen 0.19.1 | Gufo 0.31.0 | Strixite 0.7.0 |
|---|---|---|---|
| Ready and a chat generation | Pass | Pass | Pass |
| `tests/live.py` or `tests/strixite_live.py` | Pass, 4 fragments | Pass, 4 fragments | Pass, 22 fragments, release 0.253 s |
| Allowlisted names on `/metrics` | 33 of 33 | 17 of 17 | 33 of 33 |
| Startup allocation | 78.8 GiB, as on 0.18.23 | 89.11 GiB on the GPU, as on 0.29.0 | 79.3 GiB of GPU buffers, as on 0.5.0 |

- **Halogen NPU without host XRT.** Halogen started with `decider-0.8b`, `embeddinggemma-2` and `qwen3guard-stream-0.6b` and logged the kernel's own `amdxdna` driver with the image's XRT 2.25.37. Two related sentences scored 0.82 and an unrelated one 0.55 on 768-dimension embeddings in 0.21 s, and `decider-0.8b` answered a spam question with `yes` in 0.44 s. A Flash chat generation passed with the NPU models loaded. After stop the fabric clock was back on `auto`, and the kernel log had no `amdxdna` errors. The host's XRT 2.21.75 packages remain installed but unused.
- **Gufo cache.** After the update the Gufo cache directory held only a new `v2` store under schema `component-cache-v1`, so prompt state cached under 0.29.0 was not restored.
- **Logs.** Halogen logged its warm-up and no warnings. The FastAPI deprecation warning is gone. Gufo's only warning was the disconnect `tests/live.py` causes on purpose. Strixite's only warning was the open tool call `tests/strixite_live.py` cuts short on purpose.

Images, Pi sessions, the agent guard, Strixite resume points and renewal, deep-prefill cancellation and performance benchmarks were not exercised.

## November 4 update

`bin/update.py` pulled Halogen 0.18.23 and Gufo 0.29.0 by digest and atomically updated their image and version pins. Gufo 0.28.1 was pinned on November 3 without being started. Strixite 0.5.0 was already current. Model revisions, launch settings, live Pi files and host settings are unchanged. Both updated engines passed the [local checks](#november-4-local-checks). Superseded Halogen and Gufo images up to 0.28.0 were removed on November 3.

| Engine | Previous | Current | Current image digest |
|---|---|---|---|
| Halogen | 0.18.22 | 0.18.23 | `sha256:b53c96edc042b1d9570cda2771c5002527f94d6aca0c8704a4475aa621d355ff` |
| Gufo | 0.28.0, then 0.28.1 (`sha256:faaa6e21afb903bea20cbc893aa30239146e68e0252d412a7ff4932a26f236b8`) | 0.29.0 | `sha256:9d77753a051fc8bf08eeaea45457ac186d211a0d8b647d9b55fac60cdc781792` |

The images advertise revisions Halogen `0b28c4c51cfe` and Gufo `883f67b609b2ca38c437d0cb6672fc7577f89362`, not compared with public source.

### What changed upstream

- **Halogen 0.18.23** fixes a reply that, when the model ended its turn inside reasoning, went on to write an invented user turn (#232), and a tool string argument quoting `</parameter>`, `</function>` and `</tool_call>` that was cut short with the rest leaking into the answer (#227). Concurrent decoding is 1.1 to 3.4% faster for 0.43 GiB more device memory, the server runs a warm-up request before reporting ready, and sampled tokens are now drawn from the exact requested distribution, so seeded sampled replies may differ. It adds LiquidAI LFM3-VL-2B, LFM3-Audio-2B and LFM3-Omni-2B NPU models, not used here. Upstream states unchanged Flash checkpoints and byte-identical temperature-zero Flash output apart from the two fixes. [Tagged changelog](https://github.com/peonist-ai/halogen-flash-server/blob/v0.18.23/CHANGELOG.md).
- **Gufo 0.28.1** keeps Flash-Next prefill rows independent of the pass route (#875) and ends MTP chains at the first unconfident draft (#882). [Release notes](https://github.com/gufo-org/gufo/releases/tag/v0.28.1).
- **Gufo 0.29.0** rebuilds Flash-Next prefill around 16,384-row passes for lone prompts with fused DeltaNet kernels (#933, #895, #890), fuses part of batched decode (#894) and verifies long prompt-lookup copies in one pass (#961). Fixes widen BF16 HC inject rows to F32 (#950), restore serving concurrency (#953), correct session byte accounting (#993) and keep cached requests alive without snapshot headroom (#954). YaRN now scales with the context a session holds (#905); the launcher still passes `--rope-yarn-factor 1`. Serving drops API-key auth (#957), answers `GET /` with health and reports `reasoning_tokens`. The breaking change concerns upstream CI only. Most of the rest moves models into extensions. [Release notes](https://github.com/gufo-org/gufo/releases/tag/v0.29.0).

### November 4 local checks

Each engine was started alone at native 262144 context with MTP on, then stopped. MemAvailable was 114.7 GiB before Halogen started, 117.1 GiB after it stopped and 119.9 GiB after Gufo stopped, with Unevictable 48 KiB and kernel GTT about 0.9 GiB once stopped. Gufo first failed to start because an unrelated Docker container held port 8080; Docker containers were stopped before it ran. `tests/update.sh`, `python tests/run.py`, `tests/halogen_metrics.py`, `tests/gufo_metrics.py` and `git diff --check` passed. `bin/npu-manifest.sh` left all 166 NPU file records unchanged. The v0.18.23 fabric-clock helper has the same SHA-256 as the installed one, and host XRT is 2.21.75.

| Check | Halogen 0.18.23 | Gufo 0.29.0 |
|---|---|---|
| Ready and a chat generation | Pass | Pass |
| `tests/live.py`, including the forced tool call | Pass, 4 fragments | Pass, 4 fragments |
| Allowlisted names on `/metrics` | 33 of 33 | 17 of 17 |
| Startup GPU allocation | 78.8 GiB, against 78.3 GiB on 0.18.22 | 89.11 GiB, against 89.10 GiB on 0.28.0 |

Halogen logged its warm-up (one 15-token request, 0.79 seconds) and the FastAPI `on_event` deprecation warning seen before. With the Docker containers still running, it also warned that 10.4 GiB of host RAM was in use before it started and that only 239 contiguous free 2 MiB blocks remained; see the README on compacting memory. Gufo logged no warnings. NPU models, images, Pi sessions, cache restoration, deep-prefill cancellation, the #227 and #232 fixes and performance benchmarks were not exercised.

## October 31 update

`bin/update.py` pulled Halogen 0.18.22 and Gufo 0.28.0 by digest and atomically updated their image and version pins. Strixite 0.5.0 was already current. Model revisions, launch settings, live Pi files and host settings are unchanged. Both updated engines passed the [local checks](#october-31-local-checks), which also cover the October 29 pins' deferred validation.

| Engine | Previous | Current | Current image digest |
|---|---|---|---|
| Halogen | 0.18.18 | 0.18.22 | `sha256:273714ccb64dabb7fac0418ee1b6dd83eb57d2fd44cf286eb68a7c694a27c203` |
| Gufo | 0.27.0 | 0.28.0 | `sha256:29b231d7d296c7de56cf3412a6bb40002b43f12b04e225885bd54a06a652db7d` |

The images advertise revisions Halogen `7be7fa7c7d59` and Gufo `33731145678c1e3edb1ad05f3224d2d08f1c3983`, not compared with public source. Previous digests remain in the October 29 record; no image cleanup or prompt-cache rotation was performed.

### What changed upstream

- **Halogen 0.18.19** fixes two 0.18.18 tool-call regressions (#221): text after a finished call holding another closing tag was folded into its last argument, and a parameterless call was dropped when another call followed, failing forced `tool_choice` with a 502. It also removes the 64-image request limit, returns the Anthropic API's own over-context message on `/v1/messages`, rounds a `HALOGEN_KV_POOL_POSITIONS` that is not a multiple of 256 up instead of refusing to start, and fixes an image request racing a concurrent prompt read. [Tagged changelog](https://github.com/peonist-ai/halogen-flash-server/blob/v0.18.19/CHANGELOG.md).
- **Halogen 0.18.20** speeds decoding with two or three concurrent requests, enforces JSON schemas and strict tools on requests with images, and names the host XRT version when it is older than the new 2.20 floor. [Tagged changelog](https://github.com/peonist-ai/halogen-flash-server/blob/v0.18.20/CHANGELOG.md).
- **Halogen 0.18.21 and 0.18.22** add user-supplied LiquidAI LFM3-1.7B and d1-2B NPU models, the latter on a new `/v1/systemone` route, and let long NPU requests run between tokens of an NPU generation. Upstream states unchanged Flash checkpoints and byte-identical temperature-zero Flash output across all four releases. [0.18.21](https://github.com/peonist-ai/halogen-flash-server/blob/v0.18.21/CHANGELOG.md), [0.18.22](https://github.com/peonist-ai/halogen-flash-server/blob/v0.18.22/CHANGELOG.md).
- **Gufo 0.28.0** adds video embedding inputs and a per-request EmbeddingGemma 2 image budget, streams Qwen-Image weights from safetensors files and tunes Qwen3.8-27B verification GEMMs. None touches our Flash-Next configuration. [Release notes](https://github.com/gufo-org/gufo/releases/tag/v0.28.0).

### October 31 local checks

Each engine was started alone at native 262144 context with MTP on, then stopped. MemAvailable was about 121 GiB before each start and after each stop, with Unevictable 32 KiB and kernel GTT about 0.6 GiB once stopped. `tests/update.sh`, `python tests/run.py` and `git diff --check` passed. `bin/npu-manifest.sh` left all 166 NPU file records unchanged. The v0.18.22 fabric-clock helper has the same SHA-256 as the installed one, and host XRT 2.21.75 meets 0.18.20's floor.

| Check | Halogen 0.18.22 | Gufo 0.28.0 |
|---|---|---|
| Ready and a chat generation | Pass | Pass |
| `tests/live.py`, including the forced tool call | Pass, 4 fragments | Pass, 4 fragments |
| Allowlisted names on `/metrics` | 31 of 31 | 15 of 15 |
| Startup GPU allocation | 78.3 GiB, as on 0.18.17 | 89.10 GiB, as on 0.26.0 |

Halogen now also exports `halogen:strict_tool_requests_total` and `halogen:strict_tools_unenforced_total`, and Gufo exports `gufo_spec_lookup_tokens_total` and `gufo_spec_lookup_accepted_tokens_total`. All four are now collected: Halogen's in a strict-tools dashboard panel, Gufo's as lookup series on the speculative throughput chart. Halogen logs a FastAPI `on_event` deprecation warning from its own `serve_api.py`, which is harmless. Gufo 0.28.0 still logged `--cache-disk-staging-bytes` as ignored, with a 1 MiB staging capacity, as every release since 0.15.0 has. The launcher no longer passes it, and `status` no longer reports a staging limit. NPU models, images, Pi sessions, cache restoration, deep-prefill cancellation and performance benchmarks were not exercised.

### Halogen image input

The October 31 changes also make Halogen's vision tower available. `config/halogen-files.tsv` now lists `qwen38-flash-next-vision.hgn` (897,916,416 bytes) at the pinned model revision, and `env VISION=on bin/run.sh halogen start` passes it as `HALOGEN_VISION_TOWER`. Without it the launcher passes no tower, `/health` reports `vision.enabled: false`, and an image request gets a 400 naming the flag. `VISION=on` is refused for Gufo. `status` now parses the startup allocation line the tower changes.

Checked on October 31 at native context with MTP on:

| Check | Halogen 0.18.22, `VISION=on` |
|---|---|
| Startup allocation | 79.2 GiB, of which 0.8 GiB is the tower, against 78.3 GiB without it |
| First image | About 1 GiB less MemAvailable and 0.35 GiB more GTT, the tower's scratch |
| 1280x800 test image, buffered | 2.9 seconds, 1,034 prompt tokens. Transcribed "ORCHID 4471" and "blue square below" exactly and named both shapes' colors and sides, but placed the caption below the square instead of above it |
| Same request, streamed | 0.9 seconds with the image prefix reused, text identical to the buffered reply |
| `tests/live.py` | Pass, 4 fragments |
| Default start | `vision.enabled: false`, 78.3 GiB, a valid image refused with a 400 |

That start also logged Halogen's warning that the host had only 734 MiB of contiguous free 2 MiB blocks; see the README on compacting memory. Large or many images, image tool calls, schemas on image requests and Pi image input were not exercised.

## October 29 update

`bin/update.py` pulled Halogen 0.18.18 and Gufo 0.27.0 by digest and atomically updated their image and version pins. Strixite 0.5.0 was already current. Model revisions and launch settings are unchanged. No inference engine was running before the update. The new pins are installed but not locally validated for inference; see [the checks and remaining validation](#october-29-checks-and-remaining-validation).

| Engine | Previous | Current | Current image digest |
|---|---|---|---|
| Halogen | 0.18.17 | 0.18.18 | `sha256:d6cb2a7d20211da675cd1f104a02f4bf4cb60e29afffbaadf8b0d495d332cc8a` |
| Gufo | 0.26.0 | 0.27.0 | `sha256:af997f31d5a825ad02fd44cbb6744e71a21df6149c02c5ed3bb0bb843b3f0013` |

The images advertise revisions Halogen `d2c67670fe03` and Gufo `de15fdb91f6992f09a2514dabd6d6a8e5f8a2efc`. The advertised revisions were not independently compared with the shipped binaries. Previous image digests remain in the October 27 and 28 records; no image cleanup or prompt-cache rotation was performed.

### What changed upstream

- **Halogen 0.18.18** preserves cached prompts when Claude Code loads deferred tools, including MCP tools; fixes admission of short requests after a paused reply changes state during a long prefill (#214); and preserves literal closing tool tags inside string arguments (#216). It loads ggml-org's `IQ4_NL` GGUF with its `Q4_0` lookup table (#217), suppresses a noisy second-token progress log and improves model links. Upstream states unchanged Flash checkpoints, speed and temperature-zero output apart from the fixes. Our native `.hgn` checkpoint needs no replacement. [Tagged changelog](https://github.com/peonist-ai/halogen-flash-server/blob/v0.18.18/CHANGELOG.md).
- **Gufo 0.27.0** adds per-request disk-persistence control and generated-token probabilities. It bounds draft-ID remapping and block selection, preserves YaRN during batched MTP cache catch-up, fixes Q8_0 inject/alpha/beta execution and prefill scratch sizing, and retries failed unbuffered weight reads through buffered reads. Per-stream Flash-Next scratch now grows from smaller blocks. Prefill changes retain fused attention beyond 262,144 visible tokens and combine small K-quant GEMM work into one masked pass. MiniMax H3 gains Windows support and its Windows archive packaging is fixed. These are publisher changes, not local speed or memory measurements. [Release notes](https://github.com/gufo-org/gufo/releases/tag/v0.27.0).

### Features we do not use or validate yet

| Feature | Current local handling | What remains |
|---|---|---|
| Gufo per-request disk opt-out | Pi does not send `cache_persist`; normal disk caching stays enabled. `supportsStore: false` in the profile concerns OpenAI `store`, not this flag. | Decide whether an opt-out belongs in a separate profile or per-request control, then check the transmitted flag and disk writes. |
| Gufo generated-token probabilities | Pi, `tests/live.py` and the dashboard neither request nor display them. | Use a direct API request or add client support when needed; verify streaming and buffered responses. |
| Halogen literal tool-tag arguments | The fix applies automatically to our Chat Completions route. The live test assembles strict JSON but uses only a simple `status` argument. | Exercise file/heredoc arguments containing closing tags, streamed and buffered, without executing the returned calls. |
| Halogen deferred tool-search cache reuse | Our documented client is Pi over Chat Completions, not Claude Code's deferred-tool Messages flow. No `ENABLE_TOOL_SEARCH=false` workaround is configured in this repo. | A Claude Code session that loads MCP tools incrementally must validate cache reuse separately. |
| Halogen pause/resume scheduling during long prefill | One slot, automatic reply keeps and upstream retry-grace defaults remain. The live test checks disconnect-to-idle within 30 seconds. | Retry resumption and short-request admission beside deep prefill are not covered by that test. |
| Halogen official GGUF loading | The launcher selects the existing native `.hgn` package; it exposes no GGUF selection. | An explicit alternative-model trial would need pinned files, a launcher change and validation. |
| Gufo YaRN and attention above native context | The launcher caps context at 262,144 and does not enable YaRN. | Extended-context quality, memory and MTP catch-up remain untested; the new beyond-native attention path is outside our configuration. |
| Other Gufo routes and controls | No MiniMax/Windows deployment, embedding service, image/audio embedding inputs, `/apply-template` client, or RAM-cache-off mode is configured. These include still-unused additions from earlier releases. | Provision and validate separately if needed; this update adds no new models, routes to Pi, or launcher controls. |

For direct Gufo Chat Completions requests, `"cache_persist": false` suppresses that request's disk checkpoints. It still allows RAM reuse and reading existing disk checkpoints; a later unflagged request with the same prefix can persist its own state. Omitted/null defaults to true, and the applied boolean is echoed in responses. This is not cache deletion or a private-session guarantee. The installed Pi 1.4.0 source forwards arbitrary `samplingParams` into Chat payloads, so the flag could be configured there, but that path was source-inspected only and the checked-in/live profiles were not changed. [Gufo prompt-cache contract](https://github.com/gufo-org/gufo/blob/v0.27.0/docs/SERVER.md#prompt-cache).

Gufo Chat requests accept `"logprobs": true` and optional `"top_logprobs": 0..20`; results appear in each choice's `logprobs.content`, including streamed chunks. They describe generated tokens using raw target-model probabilities before sampling controls, not prompt tokens, and add work when requested. Responses uses `include: ["message.output_text.logprobs"]` for visible output. [Gufo probability contract](https://github.com/gufo-org/gufo/blob/v0.27.0/docs/SERVER.md#generated-token-log-probabilities).

### Model, memory and cache implications

- **Existing quantization.** Header inspection of the selected Gufo GGUFs found all 168 trunk inject/alpha/beta tensors already F32, and two Q8_0 inject tensors in the MTP sidecar. The fix does not require replacing the trunk weights. It also changes the draft inject execution path, so unchanged output is not assumed. The upstream warning excludes the official MTP inject tensors. [Q8_0 fix](https://github.com/gufo-org/gufo/commit/7b94a6a3fc52de630c15a822a0659a3e25f46bf7).
- **Scratch memory.** Gufo's per-stream scratch starts at 16 MiB instead of 256 MiB and grows in blocks retained for stable graph addresses. That may reduce small draft-stream overhead; it is not a fixed total-memory saving or evidence that near-capacity workloads fit. [Allocation change](https://github.com/gufo-org/gufo/commit/1a6655fcb1c63f7e1e8aae7394e9c903b25ad91f).
- **Cache compatibility.** Neither release announces a cache-format migration. No cache files were removed or archived, and cross-version restoration remains untested. Halogen's build-specific namespaces can leave old directories consuming space outside the new namespace's 16 GiB limit.
- **Monitoring.** Existing allowlists and panels are unchanged. They do not collect Gufo's persistence acknowledgement or token probabilities. The new images' native metric endpoints and Prometheus scrapes still need checking.

### October 29 checks and remaining validation

All three configured digests are present locally with matching OCI versions and Linux AMD64 metadata. `bin/npu-manifest.sh` reran against the new Halogen image: all 166 selected file records are unchanged, so no NPU weight refresh is required. The offline `tests/update.sh` and `python tests/run.py` checks passed without warnings, covering update transactions and launcher policy rather than compatibility with the new binaries. `git diff --check` passed. The update leaves weights, live Pi files and host settings unchanged. The versioned Halogen fabric-clock helper has SHA-256 `0dbd47c15f1002e0a8997ec7070e96f3e009125068eab8eccbbd49424a594f5a`, identical to the installed helper; no host-script replacement is needed.

Live checks were deferred: before pulling, MemAvailable was about 80 GiB, falling to about 79 GiB during the pull. Previous native-262144 startup allocations were 78.3 GiB for Halogen and 89.10 GiB for Gufo, with roughly 108 GiB available before those rollouts. These are different accounting views, not an exact admission formula, but leave insufficient conservative headroom for this validation. No applications were closed or host memory settings changed to force the tests.

Once headroom is restored, start each updated engine alone at native context with MTP, check readiness and a real generation (`bin/run.sh ENGINE start --wait`, `bin/run.sh ENGINE smoke`), run `python tests/live.py ENGINE`, inspect startup warnings and the metric allowlist, then stop and verify memory release before switching. Halogen NPU requests also need a separate check if used. The last successful baseline checks remain Halogen 0.18.17 on October 27 and Gufo 0.26.0 on October 28. New-feature cases listed above, Pi sessions, cache restoration, deep-prefill cancellation and performance benchmarks were not exercised on the October 29 pins.

## October 28 update

`bin/update.py` pulled the new Gufo image by digest and atomically updated its image and version pins. Halogen 0.18.17 and Strixite 0.5.0 were already current. Model revisions, launch settings, live Pi files and host settings remain unchanged. The release notes are publisher claims; the [local checks](#october-28-local-checks) follow.

| Engine | Previous | Current | Current image digest |
|---|---|---|---|
| Gufo | 0.25.0 | 0.26.0 | `sha256:c0df630a7048fed5722e19d5f031464b0fb04156071a0a3191dff226c14cd91e` |

The image advertises revision `78d741856d0063825482660e1b1081184419c7a8`, not compared with public source.

### What changed upstream

**Gufo 0.26.0** removes a lossy chunked DeltaNet prefill for qwen-flash (#850) and adds a faster chunked prefill with stream overlap (#758). The notes do not say which earlier releases used the lossy path, so earlier Gufo results may or may not be affected. It keeps Qwen weights in device memory when the heap has room (#708), accepts more than 128 function tools, drains a request before the loading responder closes, and adds native audio embeddings, llama-server's `/apply-template`, a way to turn the RAM cache off through `--cache-ram-bytes` and EmbeddingGemma 2 prompt selection by name. None mentions a cache format change.

### Launch and model changes

- **No launcher change.** The existing Gufo flags were accepted. The new features are unused.
- **Updater output.** `bin/update.py` now prints release notes only for engines whose pin changes. `tests/update.sh` checks that a current pin prints none and that outdated pins print the right releases.

### October 28 local checks

Gufo was started alone at native 262144 context with MTP on, then stopped. MemAvailable was 108 GiB before the start; after the stop it was 114 GiB, Unevictable 0.1 MiB and kernel GTT 1.8 GiB.

| Check | Gufo 0.26.0 |
|---|---|
| Ready and a chat generation | Pass |
| `tests/live.py` | Pass, 4 fragments |
| Allowlisted names on `/metrics` | 15 of 15 |
| Startup GPU allocation | 89.10 GiB, against 89.09 GiB on 0.25.0 |

- **Weights in device memory.** The startup allocation and MemAvailable while serving, about 22 GiB, are unchanged from 0.25.0, so #708 changed nothing visible at this context.
- Gufo still logs `option_ignored` for `--cache-disk-staging-bytes`.

Not exercised: deep prefill, where #850 and #758 apply, and its speed or output against 0.25.0; Pi sessions; cache reuse across the upgrade; the new embedding, audio and template features.

### Image cleanup

The superseded Gufo 0.25.0 image was removed by digest without force. No container used it. Podman's image store fell from 17.25 GB to 11.89 GB. Rolling back requires pulling the previous digest in the October 27 table again.

Source: [Gufo 0.26.0](https://github.com/gufo-org/gufo/releases/tag/v0.26.0).

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

- **Halogen** 0.18.17 opened new cache directories. 0.18.14's two, about 0.2 GiB and fingerprinted with its engine build, were deleted.
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

Not exercised: Strixite image input; Pi sessions on the new versions; prompt-cache restoration across the upgrade; Prometheus scrapes and the rendered dashboard, as monitoring was stopped; Halogen's answer guard reaching its case, the keep under a full KV pool and the out-of-memory path; Gufo's embedding changes; two Strixite slots at depth; prefill or decode benchmarks. Strixite is not in use, so further Strixite testing, including `SLOTS=2` in a Pi session, is deferred.

### Image cleanup

The superseded Halogen 0.18.14, Gufo 0.23.0 and Strixite 0.4.0 images were removed by digest without force. No container used them. Podman's image store fell from 19.3 GB to 15.34 GB. Rolling back requires pulling the previous digests in the October 24 table again.

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
