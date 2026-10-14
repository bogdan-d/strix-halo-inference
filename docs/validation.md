# Local validation, October 10, 2026

The detailed results below are historical. Image pins moved to Halogen 0.18.0, Gufo 0.12.0 and Strixite 0.2.4 on October 11, followed by basic checks only. Halogen 0.18.1 and Gufo 0.13.0 were pinned on October 12. Halogen passed a short check at 32K context, and Gufo has not been started. Halogen 0.18.3 and Gufo 0.15.0 were pinned on October 14 and passed basic native-256K checks that day, with Strixite 0.2.4 and the NPU device passed to all three. See the [release update record](engine-updates.md) for current versions, compatibility and validation scope. Historical image digests remain in Git history rather than the current `config/pins.env`.

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

## Optional host monitoring, October 11, 2026

Ticket 06 adds a manually managed rootless stack with Grafana 13.2.3, Prometheus 3.15.0 and node-exporter 1.12.1. Official image digests are recorded separately from engine pins. Native DRM and hwmon collectors supply the requested GPU readings without a custom collector. The provisioned dashboard and data source were verified against running services, and every panel query returned real series. A disposable browser verified the rendered dashboard and the unavailable-memory state after stopping the exporter. The anonymous bookmark endpoint returned an expected nonblocking 401, while dashboard data queries succeeded.

Exporter RAM total, swap total and GTT limit matched the host counters exactly. GTT used also matched in the sampled idle comparison, while MemAvailable differed by only 32 KiB between sequential reads. The dashboard keeps physical RAM, GTT and engine allocations separate and does not calculate guaranteed application headroom. All seven enabled collectors reported success on this host. CPU, PSI and disk panels use rates of native counters, not invented instantaneous values.

Actual listeners were restricted to 127.0.0.1 on ports 3000, 9090 and 9100. Runtime inspection verified read-only host sensor mounts, read-only root filesystems, no privileged mode, no GPU grants and zero effective, permitted, bounding, inheritable and ambient capabilities. No model directory or Podman socket was mounted. Anonymous dashboard access was verified as provisioned and non-editable. A real occupied-Prometheus-port failure rejected startup, stopped the invocation's containers and retained both volumes. A historical sample remained queryable after monitoring stop and restart.

An exploratory idle interval of approximately 60 seconds, with the browser closed and five-second scraping, measured RSS snapshots of 24 MiB for node-exporter, 99 MiB for Prometheus and 355 MiB for Grafana. Mean CPU from native process counters was 0.38%, 0.28% and 0.58% respectively, where one logical CPU is 100%. Summed RSS is not an exact net physical-memory cost, and this is not a peak or open-dashboard profile. Storage retention, permissions and operational limits are documented in [the monitoring guide](monitoring.md).

Both pinned engines passed the conversation, tool-call, streaming-disconnect and post-cancellation generation checks with monitoring running at 256K and MTP enabled. Both also returned the smoke response with monitoring stopped. Halogen continued generating after monitoring restart. Host GPU activity updated during inference. No inference launcher, engine image or model pin, live Pi setting, host permission, kernel or BIOS setting was changed. Validation can add public synthetic requests to existing engine caches, but no engine cache was rotated or deleted. Both engines and monitoring are stopped afterward, matching the initial state, and monitoring history is retained in its two named volumes.

Shell syntax, ShellCheck and the offline model, updater, launcher, status and new monitoring-policy checks passed. The new check covers detached launch, argument rejection, unrelated-container and volume guards, rollback after partial startup and retention of volumes. CLI stubs are policy tests, not compatibility evidence. Tickets 07 and 08 remain unimplemented, so engine throughput, context occupancy, cache and speculation panels are not yet present.

## Halogen inference telemetry, October 11, 2026

Ticket 07 adds a native Halogen metrics scrape and a separate provisioned dashboard using the existing monitoring containers. The pinned 0.17.5 endpoint's wire HELP and TYPE declarations were verified alongside tagged upstream documentation. Only 28 reviewed scalar metrics are retained, and labels are restricted to metric name, fixed job and loopback instance. Actual stored series showed no publisher-provided content labels or build metadata. No collector, image update, host access or broader listener was added.

Every dashboard expression was accepted by real Prometheus, and every target returned real series after completed generation requests. Processing-time ratios are separated from wall-time throughput, pool capacity from completed-request occupancy, and frontend counters from background cache reports. Cache readings are hidden at 15 seconds of report age. The engine probe is explicitly liveness rather than a separate readiness guarantee. Unsupported current-request context, per-request latency distributions and total live RAM allocation remain unavailable instead of estimated. The detailed sources and limitations are in [Halogen monitoring](halogen-monitoring.md).

Halogen passed the existing conversation, tool-call, streaming-disconnect and post-cancellation checks with metrics scraping active at 256K and MTP enabled. Two deliberately 512-token-bounded generations exercised completed token, cache and speculative counters, and a repeated prompt reported cache reuse. Their length stop was intentional for telemetry validation, not a completed coding task. A separate 1,024-token-bounded request was observed in flight through Prometheus with a processing count of one and a nonzero busy age. These checks do not establish model quality or an engine-speed benchmark.

Stopping Halogen changed scrape health to down and made all current engine queries unavailable while host monitoring remained independent. A disposable browser verified the unavailable engine-probe panel after shutdown. Restarting Halogen reset its generated-token and completed-request counters to zero, and Prometheus detected the reset. A subsequent smoke request generated successfully. The pinned real promtool also passed synthetic policy checks for counter resets, stale cache snapshots, no-work speed windows, zero speculative proposals and scrape versus engine health. Those synthetic sequences exercise dashboard semantics, not engine compatibility.

The final idle collection interval measured approximately 102 ms mean scrape duration, 204 ms maximum and a roughly 5.4 kB native response. The engine's idle CPU was approximately 0.246% of one logical CPU without monitoring and 0.289% with it in separate 60-second windows. The approximately 0.044-percentage-point difference is uncontrolled and not proof of a precise marginal cost. A monitored interval overlapping generation was discarded for idle comparison. Prometheus with both jobs used approximately 0.98% of one logical CPU and 110 MiB RSS in the final window, not a Halogen-only increment. There was no controlled inference-speed impact test.

No inference launcher, image or model pin, live Pi setting, host permission, kernel or BIOS setting was changed. Validation used only public synthetic prompts and may add their state to existing engine caches, but did not rotate or delete those caches. Halogen and monitoring are stopped at completion, matching their state before ticket 07 began. Monitoring history remains in the existing volumes. Temporary screenshots and measurement files were removed. Ticket 08 remains pending.

## Gufo inference telemetry, October 11, 2026

Ticket 08 adds independent native Gufo and HTTP-readiness scrape jobs with a separate provisioned dashboard. Actual 0.11.0 metric exposition was checked against tagged server, metric-accounting and scheduler source. The jobs retain 15 native scalars and three probe scalars, respectively, plus Prometheus's automatic scrape series. Actual stored series had only metric name, fixed job and loopback instance labels. All 21 dashboard targets returned real series after completed requests while Halogen remained stopped.

Gufo has no native readiness gauge, so the official digest-pinned blackbox-exporter 0.29.0 supplies a bounded HTTP probe in a fourth monitoring container. Runtime inspection verified its read-only root, read-only configuration-only mount, no privileged mode, no-new-privileges and zero capabilities in all five kernel sets. Its listener was restricted to 127.0.0.1:9115. No model, cache, host sensor or Podman socket mount was added. Real probe tests accepted HTTP 200 with JSON status ready and rejected another status value, malformed JSON and HTTP 503 even with a ready body. Response bodies are not persisted.

Gufo passed conversation recall, forced tool arguments, streaming-disconnect slot release and post-cancellation generation with monitoring enabled at 256K and MTP on. A deliberately 1,024-token-bounded request showed admitted work, nonzero logical context and an advancing generated-token counter through Prometheus. After completion, logical context returned to zero while the historical speed gauge retained its latest positive value. Two further 512-token-bounded requests exercised speculation and cache reuse; the repeat reported 34 cached prompt tokens. These deliberately length-limited requests validate telemetry, not coding quality or engine-speed superiority.

The dashboard explicitly distinguishes Gufo's live execution counters from finish-accounted stage times, cached tokens and draft totals. Unlike Halogen, speed panels use latest-positive historical gauges rather than token/time counter ratios. Logical in-flight context is not retained-cache occupancy or physical GPU allocation, and `n_tokens_max` is displayed as a high-water mark rather than configured capacity. Unsupported retained-cache bytes and limits, request-hit probability, latency distributions and live allocation are documented in [Gufo monitoring](gufo-monitoring.md).

Stopping the readiness exporter made its scrape Down and model readiness Unavailable while the native Gufo scrape stayed Up. Stopping Gufo made native scrape Down and model readiness Not ready while probe collection remained Up. Every current native dashboard query became empty after engine shutdown. A disposable browser verified both distinct failure states and the provisioned layout. Restarting Gufo reset generated tokens, cached tokens and the sequence high-water mark to zero, with Prometheus observing one generated-counter reset; smoke generation passed afterward. Halogen was not required for any Gufo query or check. Fatal GPU device loss was not induced.

Separate 60-second idle windows with the browser closed measured Gufo container CPU at approximately 0.027% of one logical CPU without monitoring and 0.039% with monitoring. The approximately 0.012-percentage-point difference is uncontrolled, not proof of precise marginal endpoint cost. Native scrape duration averaged 1.54 ms with a 2.31 ms maximum; readiness collection averaged 2.57 ms with a 3.32 ms maximum. The native response was 2,466 bytes. Blackbox-exporter measured approximately 0.067% CPU and 35 MiB RSS; whole Prometheus measured 1.03% CPU and 103 MiB RSS. These are idle whole-process observations, not peak, net physical memory or controlled inference-impact measurements.

Shell syntax, ShellCheck, monitoring lifecycle-policy checks and the real pinned promtool Gufo and Halogen query-policy checks passed. Real Prometheus and blackbox configuration checks passed. Synthetic Gufo cases cover reset-aware throughput, probe collection versus readiness, hidden stale counters, retained idle speed, direct high-water marks and no-work ratios; actual engine compatibility was checked separately. The existing host dashboard and Halogen scrape configuration were unchanged.

No inference launcher, engine image or model pin, live Pi setting, host permission, kernel or BIOS setting was changed. Engine pins and live Pi files remained byte-identical. The new image uses ordinary Podman storage, and monitoring history remains in its existing named volumes. Validation used public synthetic prompts and may add state to the existing engine cache; no cache was rotated or deleted. Both engines, all monitoring containers and disposable browsers are stopped at completion, matching the initial state. Temporary screenshots were removed. Optimization tickets 01 through 08 are complete.

## Single-page dashboard, October 12, 2026

Grafana, its pin, its four provisioned dashboards and its provisioning files were replaced by one checked-in HTML page that queries Prometheus directly. Monitoring is now three containers. Scraping changed from five seconds to two, with a two-second timeout, to match the page's default refresh. The earlier monitoring sections above describe the Grafana setup as validated at the time.

Every query on the page was accepted by real Prometheus 3.15.0. Every query from the four removed dashboards is present unchanged, except the host sensor-availability checks, which were dropped, and per-device disk rates, which are now summed. One new reading was added: Strixite last-session tokens divided by configured capacity. The existing promtool policy checks for all three engines pass against the page's definitions, and the monitoring lifecycle check passes for the three-container stack.

Halogen 0.18.0, Gufo 0.12.0 and Strixite 0.2.4 were each started at native 256K, given real non-streaming generations, and compared against their raw `/metrics`: token counters, speeds, context share, reuse share and draft acceptance agreed. Each engine section, the no-engine state and the Prometheus-unreachable state were rendered in headless Firefox opening the page as a local file. Each engine was stopped afterward with memory released, and monitoring was stopped. Prometheus answered a `null` origin with a matching CORS header.

Not exercised: Chromium-based browsers, the 1 hour and 6 hour ranges, refresh intervals other than the default, hover readouts, long-context or cancelled requests, and collection overhead at two-second scraping. The old `strix-halo-monitor-grafana` volume and pulled Grafana image were removed by name afterward.

## Dashboard controls, October 12, 2026

`bin/dashboard.py` was added: a loopback-only helper that serves the dashboard page and runs fixed `bin/run.sh` and `bin/monitor.sh` commands for its new start, stop and log controls. No launcher, container or scrape configuration changed.

The offline helper check passes, and the page script type-checks. On the real host, with headless Firefox driving the served page: monitoring was started through the helper and stopped from its page button with the Prometheus volume retained. Gufo 0.12.0 was started from its page button at native 256K; the other engine buttons were disabled, the log drawer opened on Gufo by itself, the button counted loading seconds and then showed ready, and `bin/run.sh gufo smoke` returned a real generation. Switching the drawer to Prometheus ended the Gufo log viewer. The page Stop button stopped Gufo with memory released and the drawer showed the log ending. A refused command showed the launcher's message in the header. The monitoring-off placeholder, the notice after the helper was stopped, and the unchanged control-free page opened as a file were also rendered. Everything was stopped afterward.

Not exercised: Halogen and Strixite started from the page, the visible stopping state (Gufo and monitoring stopped within about two seconds), a start that fails after its container exists, the partial monitoring state, a second engine start raced from another client, Chromium-based browsers, and manual use of the Follow checkbox and scrolling.

## Remaining work

Neither restart-safe engine-cache restoration nor long-context performance has been comprehensively tested. No host package, group, device-permission, login-limit, kernel or BIOS change was made. No persistent inference service, proxy or image-build CI was added. Optional host, Halogen and Gufo monitoring now work. Matched-engine benchmarks, near-capacity workloads and multi-request serving remain future work rather than completed telemetry tickets.
