# Local validation, October 10, 2026

Host: CachyOS, kernel `7.2.9-2-cachyos`, Ryzen AI Max+ 395, Radeon 8060S, approximately 125 GiB usable system RAM. Existing BIOS, IOMMU and kernel settings were preserved. Rootless Podman uses `runc`. GPU devices are directly accessible on this host, so supplementary-group preservation was not needed for these checks.

## Pinned artifacts

| Artifact | Selected version or revision |
|---|---|
| Halogen Flash image | 0.17.5, digest in `config/pins.env` |
| Gufo runtime image | 0.11.0, digest in `config/pins.env` |
| Gufo engine image label | `e3c0d4cc130721f2810999d8dbb9221cd092edf4` |
| Halogen native weights | `506567c641cfb737e0b01c1deff10813154c5529`, v2 checkpoint, lookup table and tokenizer |
| Gufo GGUF weights | `38bb39ee97821de2c9009abb7e93950eec396e66`, UD-Q4_K_XL shards and shared Q8 MTP head |

The Gufo pin is a published stable release, not the earlier PR candidate described in the historical research. Exact file sizes and SHA-256 hashes were obtained from pinned Hugging Face metadata. Non-LFS tokenizer hashes were computed from their pinned bytes. Both images were pulled by digest.

## Completed checks

- Shell syntax and ShellCheck pass. The offline model-integrity test rejects a size-correct corrupt existing shard without replacing it and rejects missing weights before launch.
- Gufo's `diagnose` passes inside the selected rootless container, detects `gfx1151` and reports ROCm 7.2.3. Its serve help confirms the configured model, context, speculative and cache flags.
- Halogen's container `rocminfo` detects the GPU. The rootless container hard memlock remains 8 MiB despite `--ulimit memlock=-1:-1`. Halogen's GPU-backed pinning still succeeds, while optional host `mlock` and NPU behavior remain untested and disabled.
- All eight selected Halogen files completed download and SHA-256 verification. The package totals 117,910,836,996 bytes, approximately 109.8 GiB.
- Halogen starts at one slot and 32K context with `/home/bogdan/models` mounted read-only and its own writable `/cache`. API and engine both report 0.17.5. The published port is localhost-only.
- Halogen produces `ready` for the non-thinking smoke prompt. The live test passes multi-turn secret-word recall, a named tool call with parsed JSON arguments, streaming disconnect slot release within 20 seconds, and generation after cancellation. The follow-up reports 24 cached prefix tokens, demonstrating in-process reuse.
- Halogen shuts down using the explicit stop command. No managed inference container remains running, and host available memory returns to approximately 119 GiB.
- All five selected Gufo files completed download. A separate verification pass after every download finished matched all 13 final files against their committed sizes and SHA-256 hashes. No corruption was detected.
- Gufo serves this model successfully at one session and 32K context, with speculation off and with the shared Q8 MTP head. Both modes pass conversation recall, forced tool arguments, streaming disconnect slot release and generation after cancellation. Follow-ups report 25 cached prefix tokens.
- Gufo's greedy autoregressive and MTP text is identical on two uncached prompts, one requesting a Fibonacci function and one explaining hash-mismatch handling. The MTP runs actually speculate, reporting 178 drafts with 159 accepted and 60 drafts with 29 accepted. This is a focused consistency check, not a general quality benchmark.
- Podman inspection confirms Gufo's central `/models` mount is read-only and its separate `/cache` mount is writable. Gufo shuts down cleanly and available host memory returns to approximately 120 GiB. About 1.3 GiB of previously swapped pages remains in swap afterward. No swap or cache flushing was performed.
- The startup lock stays in the launcher's shell rather than being inherited by the detached container monitor. A live check confirms the lock is released after launch and a second engine start is refused because the first engine is active. Both engines are stopped at the end of validation.

Halogen's startup log reports 62.1 GiB of weights, 0.9 GiB KV pool and 12.1 GiB working memory, 75.1 GiB total. Its separate 47.7 GiB lookup table is demand-paged. It warns that ordinary `MemAvailable` overstates memory reclaimable while the pinned weights are loaded. It also warns about fragmented host memory. Startup reached model readiness in approximately 11 seconds after download verification had warmed the file cache. This is not a cold-start benchmark, and the two-token smoke rate is not a meaningful throughput benchmark.

Gufo's MTP startup reports 84,599 MiB of GPU allocation, approximately 82.6 GiB, against the 108,000 MiB GPU memory limit. It reaches readiness in approximately 61 seconds in this run, including a 47-second full artifact fingerprint. These observations are not controlled cold-start or throughput benchmarks.

## Integrity record

Gufo's package totals 114,121,223,040 bytes, approximately 106.3 GiB. Together the packages total approximately 216.1 GiB. The complete post-download verification log is `/home/bogdan/.cache/strix-halo-inference/verify-models.log`, containing 13 `Verified` lines and successful completion records for both packages. Recheck at any time with `bin/models.sh verify halogen` and `bin/models.sh verify gufo`.

The download and verification used one-off transient user services, not enabled inference services. Their logs remain under `/home/bogdan/.cache/strix-halo-inference`. One resumed downloader logged a trailing shell parsing error after its final file was promoted because the script was edited while that process was running. The current script passes shell syntax checks, and the independent final-file verification completed successfully for every file afterward. The error did not indicate a failed or corrupted weight transfer.

## Pi coding-agent integration

The [Pi profiles](pi.md) were checked with Pi 1.1.0 using the pinned engines, MTP enabled, 32K context and the recommended sampled `xhigh` coding settings. In an isolated temporary workspace, each engine successfully used Pi's `read` tool to inspect a broken addition function and its checks, used `edit` to fix subtraction to addition, then used `bash` to run the unchanged checks. Both assertions passed and Pi returned a final success summary. Neither stream reported an error or length truncation. Both produced thinking blocks and follow-up cached-token usage. This is an end-to-end provider and tool-loop check, not a coding-quality benchmark.

Both models appear in Pi's available-model list with the intended context and output limits. The documented merge command was used to install the fragments in the host's existing agent directory. Backups were created, and unrelated providers, default model selection and settings were verified unchanged. The tool-loop checks disabled user extensions, skills and context files to isolate provider behavior. The user's complete extension stack, automatic compaction and large coding tasks were not exercised by these checks. Halogen was restored to a ready running state after testing Gufo because it was running before this work.

## Full native context, 256K

The launcher and checked-in Pi profiles now default to 262,144 tokens, with one active slot and MTP enabled. Both pinned engines start successfully at that capacity. Halogen's health endpoint confirms a 262,144-token request limit, slot context and KV pool. Gufo's model endpoint confirms `context_length: 262144`. Both pass the smoke request and the conversation, tool-call, cancellation and generation-after-cancellation checks in `tests/live.py` at this allocation.

Each engine also processes the same synthetic 40,030-token padding prompt and returns the requested `ready` response, demonstrating operation beyond the former 32K limit. The observed request durations were 23.2 seconds for Halogen and 25.1 seconds for Gufo. Repetitive padding is not representative coding text, and these single requests are not a throughput or quality comparison.

| Measurement with 256K configured | Halogen | Gufo |
|---|---|---|
| Engine startup memory report | 62.1 GiB weights + 7.2 GiB KV + 12.1 GiB working memory = 81.4 GiB | 90,605 MiB GPU allocation, approximately 88.5 GiB |
| Kernel GTT used after the 40,030-token request | approximately 20.0 GiB | approximately 89.7 GiB |
| GTT remaining against the 105.5 GiB limit | approximately 85.5 GiB | approximately 15.8 GiB |

Kernel counters were read from `/sys/class/drm/card1/device/mem_info_gtt_total` and `mem_info_gtt_used`. The exact GTT limit is 113,246,208,000 bytes, or 105.46875 GiB. These readings include other GPU users and are post-request snapshots, not peak measurements. The engines allocate weights differently, so Halogen's total resident weight memory must not be equated with its GTT charge. Its separate 47.7 GiB lookup table remains demand-paged, and pinned weights still make ordinary `MemAvailable` misleading.

This verifies capacity configuration, allocation and a prompt beyond 32K. It does not verify nearly full 256K prompts, peak memory under that workload or long-context retrieval quality. Halogen is left running and ready at 256K after Gufo testing. No live Pi configuration, host GTT allocation, kernel setting or BIOS setting was changed for this context increase. The older installed Pi profiles need the explicit update described in [the Pi setup guide](pi.md).

## Published-image updater

The updater's real registry check resolves Halogen `latest` to the existing 0.17.5 digest and Gufo `latest` to the existing 0.11.0 digest. Selected-version notes are fetched from Gufo's GitHub Release and Halogen's tagged changelog because Halogen's Releases API has no matching release. The offline update test exercises pin-transaction failure, cache rotation guards and preservation, selected release sections and downgrade refusal. The registry and notes checks exercise the real endpoints rather than relying on those CLI stubs for compatibility evidence.

The updater does not change model pins or live Pi configuration and does not restart containers. Cache rotation is optional and requires stopped engines. Future image versions remain unvalidated on this host until the launcher and live checks pass after an explicit restart.

## Launcher optimization tickets 01 through 04

Engine-first dispatch, live log following, optional readiness waiting and the operational status summary were validated against the existing pinned images with 256K capacity and MTP enabled. Both engines passed readiness and real smoke generation. Both also passed the conversation, tool-call, disconnect cancellation and generation-after-cancellation checks after the launcher changes. Neither engine was active at the beginning of this work, and both were stopped afterward. Host available memory returned to approximately 119 GiB. Existing swap was not flushed.

The offline launcher checks reject old, invalid and extra arguments before Podman effects, exercise missing-container log handling, and cover readiness success, timeout, early container exit and release of the startup lock before probing. Both live engines continued generating after the log viewer received an interrupt. Following also ended when Halogen stopped, and auto-removed logs were reported as unavailable. No foreground-start option was added.

Status uses actual Podman container configuration and inherited OCI labels, not current pins or shell overrides. Offline checks protect that distinction and the nonzero exit contract for stopped, loading, unreachable and missing engines. Both live engines showed their actual 262,144-token configuration, cache limits, readiness and measured startup allocations. Those allocation figures are explicitly startup snapshots, not current usage. Disk usage covers the entire mounted directory, and unverified cache RAM usage remains unavailable. Kernel GTT and host accounting stay separate and carry the Halogen pinned-memory warning.

No new services, dependencies, image pins, model revisions, live Pi defaults or host settings were changed. Grafana and the thinking-effort comparison remain deferred.

## Routine coding thinking-effort comparison

The [thinking comparison](thinking-comparison.md) completed 16 measured Pi tool-loop trials across both engines, two synthetic tasks, medium and xhigh effort, and two repeats with reversed order. All passed independent unchanged checks, without timeout or assistant truncation. Medium finished faster in each paired comparison. The report records timing, tool calls, intermediate tool errors, output tokens and cache conditions, while limiting its recommendation to small, well-specified edits. It does not establish equivalent quality for substantial coding work.

The original live Pi models and settings were preserved byte for byte. Checked-in profiles, image and model pins, host power settings and normal engine caches were unchanged. Both engines were stopped after the comparison, matching the initial state. Temporary workspaces, Pi configuration and isolated engine caches were removed. Grafana remains deferred.

## Remaining work

Neither restart-safe disk restoration nor long-context performance has been tested. No host package, group, device-permission, login-limit, kernel or BIOS change was made. No persistent inference service, proxy, image-build CI or dashboard was added.
