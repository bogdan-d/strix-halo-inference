# Strixite suitability, October 11, 2026

**Recommendation: try it as a third, isolated engine, not as a replacement yet.** Strixite targets exactly this host's Ryzen AI Max+ 395, Radeon 8060S `gfx1151` and Qwen3.8-Flash-Next. A prebuilt release image removes the need for a local ROCm installation or source build. Its long-context and cache design are promising for Pi coding sessions. Local generation, correctness, memory and client compatibility have not been tested. See the separate [performance evidence assessment](strixite-performance-research.md) before interpreting publisher speed claims as a comparison with our engines.

## Inspected artifacts

| Artifact | Verified value |
|---|---|
| Canonical source | [shawnshekari/strixite](https://github.com/shawnshekari/strixite) |
| Main at inspection | `d6060e3b4a0a659066b01cf227f897624ead6136` |
| Latest published release | [v0.2.3](https://github.com/shawnshekari/strixite/releases/tag/v0.2.3), published October 10, 2026 |
| Release source | `dbe7b66ed620d392d0b3b6a8a6e836f9907ffea6` |
| Published image | `ghcr.io/shawnshekari/strixite@sha256:9075d3def69d550b6c8f0b42a7795259ec02187ebf755027149f8c757d6cc738` |
| Image metadata | Linux AMD64, built October 10, 2026 at 18:43:45 UTC, OCI version `v0.2.3`, revision `dbe7b66` |
| Weight package | [wemoh/Qwen3.8-Flash-Next-strixw](https://huggingface.co/wemoh/Qwen3.8-Flash-Next-strixw), revision `e0be89740e7ac38f5ef0a911e0b91865431b7a01` |

Skopeo resolved `latest` and `v0.2.3` to the same digest. The release source and inspected main differ only in four documentation files, not runtime code. Image metadata links the binary to the release, but is not a signed provenance attestation. The upstream [Containerfile](https://github.com/shawnshekari/strixite/blob/dbe7b66ed620d392d0b3b6a8a6e836f9907ffea6/deploy/container/Containerfile) packages Fedora 43 with the server and its TheRock ROCm runtime. The engine is AGPL-3.0 and the weights have a separate Qwen license.

## Memory on this machine

The publisher reports 95.3 GiB of fixed GPU buffers at 512K capacity, plus a 3 GiB CPU n-gram row cache. Reducing capacity to 256K reportedly frees about 6.7 GiB of GPU buffers, giving an **estimated 88.6 GiB GPU footprint at 256K**. This is an inference from the author's measurements, not our allocation result. Our measured GTT limit is 105.46875 GiB, leaving roughly 16.9 GiB of GTT before other GPU users. GTT headroom is not physical RAM headroom. [Source: upstream memory accounting](https://github.com/shawnshekari/strixite/blob/d6060e3b4a0a659066b01cf227f897624ead6136/docs/memory.md).

The publisher's desktop recipe is `capacity = 262144` and `prompt-cache-ram-margin-gib = 8`. A full-capacity saved state is reported as about 6.8 GiB. The startup check therefore needs roughly 14.8 GiB of MemAvailable after loading. The author's headless measurement predicts about 26 GiB available at 256K, before our desktop and other services. Saved conversations can consume most of the remaining RAM above the margin. An 8 GiB cache margin is not a reservation for VS Code and the browser, and the periodic cache check cannot prevent every sudden allocation burst.

Upstream documents a roughly 124 GiB GTT configuration with `amd_iommu=off`. Our current host uses `iommu=pt` and a roughly 105.5 GiB GTT allocation. **Do not copy the upstream boot parameters.** The 256K estimate is below our existing limit, so test with current settings first. The startup memory check runs after GPU allocation, not before it, and `low-memory = adapt` reduces caches rather than solving an insufficient GPU allocation budget. Keep `low-memory = fail` for the first baseline. No safe coexistence with Halogen or Gufo is implied.

512K is a YaRN extension beyond the model's native 262,144 positions, not an independently trained 512K context. For a matched native-context trial, explicitly set `--capacity 262144 --rope-yarn-factor 1`. The default factor is 2 even when capacity is reduced. Changing that factor invalidates Strixite's own saved cache entries. Evaluate the extended context separately after native-context quality and memory checks pass. [Source: release configuration](https://github.com/shawnshekari/strixite/blob/dbe7b66ed620d392d0b3b6a8a6e836f9907ffea6/deploy/strix-server.conf).

## Weight downloads and integrity

Strixite reads its own `strixw` format version 4, not our existing Halogen HGN or Gufo GGUF files. Its main file is mixed 4-bit and 8-bit round-to-nearest quantization without an importance matrix. It is not an equivalent quantization of Gufo's UD-Q4_K_XL, so differences in coding quality cannot be attributed to the engine alone. The MTP tensors are included in the main file. [Source: weight formats](https://github.com/shawnshekari/strixite/blob/dbe7b66ed620d392d0b3b6a8a6e836f9907ffea6/docs/weights.md).

| Required large file | Bytes | SHA-256 from pinned Hugging Face metadata |
|---|---|---|
| `converted/Qwen3.8-Flash-Next.U-gdn_in-g128/weights.strixw` | 70,714,568,704 | `2d166ca51dbeeb428ff2eb2c00e53f82b1919afaa7ee1275406f55caa46476cb` |
| `converted/Qwen3.8-Flash-Next.ngram-q8/ngram.table` | 51,840,252,928 | `462ed3040b8b022b2977e7429a042f2a1d5e02f09c47cc6006cb1b71372bd313` |

Together these are approximately 114.1 GiB, plus tokenizer and small configuration files. The pinned package's [checksum manifest](https://huggingface.co/wemoh/Qwen3.8-Flash-Next-strixw/blob/e0be89740e7ac38f5ef0a911e0b91865431b7a01/sha256.txt) agrees with the large-file metadata. The tokenizer and generation configuration hashes match our selected Halogen files, but the two large files do not. Do not assume that their n-gram tables can be shared.

Use `/home/bogdan/models/wemoh/Qwen3.8-Flash-Next-strixw` for a future download. Pin its revision and add an explicit file manifest to the existing resumable downloader. Verify all selected final files after downloads finish, then optionally run the bundled `inspect_strixw --verify` for its internal tensor hashes. The latter is additional corruption checking, not proof of model quality or publisher trust. The converter expects the original roughly 360 GB checkpoint, which we do not have, so downloading the prepared package is the simpler path. The model filesystem currently has roughly 3.2 TiB free. No weights were downloaded for this assessment.

## Pi compatibility and traps

The server implements `/v1/chat/completions`, streamed `reasoning_content`, streamed tool-call arguments and OpenAI-shaped cached-token usage. It accepts reasoning levels `low`, `medium`, `xhigh` and `none` for thinking off. Its chat template supports preserved thinking. These are the ingredients needed to adapt our existing Pi Chat Completions provider, but **source-level support is not a passed Pi tool-loop test**. Use port 5300, model `qwen3.8-flash-next`, context 262,144 and the existing 16,384 output cap as starting values. [Sources: server contract](https://github.com/shawnshekari/strixite/blob/dbe7b66ed620d392d0b3b6a8a6e836f9907ffea6/docs/server.md), [request parser](https://github.com/shawnshekari/strixite/blob/dbe7b66ed620d392d0b3b6a8a6e836f9907ffea6/serve/openai.cpp), [chat template](https://github.com/shawnshekari/strixite/blob/dbe7b66ed620d392d0b3b6a8a6e836f9907ffea6/serve/chat_template.cpp).

- Normal tool choice `auto` is supported. Forced named tools and `tool_choice: required` return 400. Our current live-check script forces a named tool, so it cannot be reused unchanged. This does not by itself block ordinary Pi automatic tool selection.
- Nonzero presence and frequency penalties are rejected, as is repetition penalty other than 1. Our thinking-off profile sends presence penalty 1.5, so copying that override would break requests. Keep that limitation explicit rather than claiming an identical model-card sampling profile. Thinking-enabled temperature 1, top-p 0.95 and top-k 20 are supported.
- The default thinking nudge injects text into repetitive reasoning. Disable it for a matched baseline with `--think-nudge off`, then evaluate it separately. The end-of-turn guard and literal-tag handling also affect serving behavior and must be recorded in comparisons.
- Malformed or truncated streamed tool arguments can remain invalid JSON. Verify Pi's handling of partial calls and cancellation, including file content containing literal model tags, before using it on real projects.
- The default 16,384-token prefill chunks check cancellation between chunks. Upstream reports chunks lasting roughly 25 seconds at depth, so our existing 20-second disconnect-release expectation is not universally appropriate. Measure it, or evaluate a smaller explicit chunk size if responsiveness matters.

There is no Responses endpoint, authentication or vision input. Do not expose the API beyond loopback. The single execution slot queues other requests, rather than running several conversations simultaneously. Native `/metrics`, `/cache`, `/health` and `/v1/models` could support future status and dashboard integration, but their semantics need independent verification. [Sources: HTTP handlers](https://github.com/shawnshekari/strixite/blob/dbe7b66ed620d392d0b3b6a8a6e836f9907ffea6/serve/http_server.cpp), [roadmap](https://github.com/shawnshekari/strixite/blob/d6060e3b4a0a659066b01cf227f897624ead6136/docs/roadmap.md).

## Proposed smallest trial

1. Add a third digest-pinned image, revision-pinned model manifest and engine-first launcher path. Keep the current single-engine lock and explicitly stop Halogen or Gufo before Strixite starts. Do not add a source build or persistent service.
2. Bind the central model store read-only and select the package through `STRIX_MODELS_DIR=/models/wemoh/Qwen3.8-Flash-Next-strixw`. Bind a separate writable cache at `/cache` and set `--prompt-cache-dir /cache`. Upstream's writable model mount is unnecessary when cache storage is overridden. Start with a 16 GiB disk-cache cap to match our existing storage policy, an 8 GiB RAM margin and fail-on-low-memory behavior.
3. Publish only `127.0.0.1:5300:5300`. Pass only the existing GPU devices and validate ordinary rootless security first. Upstream examples disable seccomp and SELinux labeling, but those relaxations are not established requirements on our CachyOS host. `keep-groups` is not supported by our `runc` path, whose directly accessible devices already work for the other engines. A failure should prompt investigation, not blanket relaxation.
4. Allocate native 256K with YaRN off, MTP on and thinking nudge off. Inspect startup allocations, physical RAM, GTT and the startup memory decision. Check `/health` after loading and run bounded generation. Its HTTP server starts after model construction and the startup memory check. Allow 90 seconds for stop so cache flushing is not prematurely killed.
5. Run an isolated Pi read, edit and bash task, automatic tool selection, multi-turn recall, cancellation and restart-cache checks. Do not modify the user's live Pi defaults until these pass.
6. Compare matched coding prompts, realistic long-context retrieval and cold versus resumed prefill against Halogen and Gufo. Keep sampling, thinking, context, power settings and cache conditions explicit. Add Grafana only after the runtime earns continued use.

The upstream [container guide](https://github.com/shawnshekari/strixite/blob/d6060e3b4a0a659066b01cf227f897624ead6136/docs/container.md) supports this workflow, but its default writable weights, unrestricted host port and headless 512K settings are not our launch policy. This assessment changed documentation only. The sole new reference checkout outside the project is `/home/bogdan/Frameworks/strixite`. No engine image was pulled or executed, no kernel settings or Pi configuration changed, and no model weights or cache directories were modified.
