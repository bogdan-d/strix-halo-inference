# Strixite inference dashboard

The current image is 0.4.0, pinned October 19. Its native endpoint still exports all 33 allowlisted names. Under 0.2.4, existing accounting semantics and queries remained compatible, and native scrape and independent readiness passed the [basic release checks](engine-updates.md). Detailed measurements below used 0.2.3. The additive `strix_think_closed_for_call_total` counter is intentionally dropped by the existing allowlist. Streamed prefill progress is not a new Prometheus progress gauge.

Open [the dashboard page](../config/monitoring/dashboard.html) after starting the optional monitoring stack and Strixite. Its Strixite section appears while the engine's metrics scrape is up:

```bash
bin/monitor.sh start
bin/run.sh strixite start --wait
bin/run.sh strixite status
```

Use existing instances if already running. If updating a running monitoring stack, stop and restart monitoring to load its scrape and probe configuration. No new monitoring image or container is needed. Stop the active inference engine and verify memory release before starting Strixite. Monitoring never starts or stops inference. Host readings are on the same page. [Halogen](halogen-monitoring.md) and [Gufo](gufo-monitoring.md) have their own sections and semantics. See [monitoring setup](monitoring.md).

## Readiness and current readings

The native scrape job fetches localhost:5300 `/metrics`. Successful collection is not proof of model readiness. The independent `strixite-ready` job uses the existing blackbox-exporter and requires HTTP 200 with JSON `status: ok` from `/health`. Busy requests do not fail readiness. The probe has a two-second timeout, 4 KiB body limit and no redirects. Malformed JSON, other status values, HTTP failures and connectivity failures are Not ready. If collection from the probe exporter fails, model readiness is Unavailable rather than an old probe result.

Health can include a startup `degraded` note. That describes cache adaptation, not readiness or current memory pressure, and is not exported as a metric in this pin. Check `bin/run.sh strixite status` and logs for degradation, expected model and context. The readiness probe does not enforce 262144 capacity, allowing deliberate smaller-context launches; the dashboard shows actual configured capacity from native telemetry. The local baseline still uses native 262144, YaRN factor 1, MTP on, thinking nudge off and low-memory fail.

Every native panel is gated on a successful native scrape. Diagnostics remain visible if readiness fails but metrics are still reachable. Stopping Strixite makes scrape health Down, readiness Not ready and current native readings Unavailable after the next collections. Historical graphs retain prior data and show gaps. A Prometheus failure is a data-source error, not an engine failure. Scraping happens every two seconds and the page refreshes at the interval chosen in its header, so shorter events can be missed.

## Strixite 0.2.3 accounting

Semantics were checked against release source `dbe7b66ed620d392d0b3b6a8a6e836f9907ffea6` and the pinned image's real wire HELP/TYPE declarations. Do not copy similarly named Halogen or Gufo interpretations.

| Reading | Meaning |
|---|---|
| Execution slot | `strix_busy` includes worker processing and post-generation work. `strix_queue_depth` counts waiting execution jobs. Ready does not mean idle. |
| Context capacity and last completed session | `strix_context_length` is configured capacity. Despite its name, `strix_live_tokens` is the session size at last worker completion, not streaming token progression. Neither measures physical GPU occupancy. |
| Last qualifying request speed | Gauges retain the last positive-work prefill/decode speed while idle. Fully reused prompts leave the prior prefill speed. Decode uses completion tokens minus the first token over decode seconds. Zero before qualifying work is hidden. |
| Completion-accounted wall-time throughput | Counter rates include idle time. Prefill totals commit after prefill; generated-token and MTP totals commit at request finalization, including cancellation. Bursts are accounting events, not instantaneous decode speed. |
| Windowed reused-token share | Cached prefix-token rate divided by full prompt-token rate, not newly prefilled tokens. No prompt work is Unavailable. This is token reuse, not request hit probability. |
| Windowed draft acceptance | Accepted divided by drafted-token rates. No proposals is Unavailable. Acceptance alone does not establish speculative speedup. |
| Prompt-cache bytes | Disk bytes, RAM-entry buffer capacities and spare-buffer capacities are separate series. RAM and disk can contain the same saved state, so do not add them as unique cache size. They do not represent total engine memory. |
| Prompt-cache entries | Disk and RAM tier counts are separate and not additive unique conversation counts. Disk entries can survive restart; RAM starts empty. |
| Cache-pressure events | Room refusals indicate insufficient RAM above the margin. RAM evictions indicate pressure. Disk write rejection reasons are space, budget and queue. RAM-only one-shot drops are intentional and are not necessarily errors. |
| Cache disk operations | Completed write/load counters and written bytes. Disk loads exclude RAM resumes. The misleading native `prompt_cache_disk_hits_total`, which also includes RAM restoration, is intentionally not used. |
| N-gram row-cache share | Cached unique gather rows divided by unique rows, including rows previously prefetched. This is not prompt-cache reuse or physical SSD I/O. |
| PLE wait | Cumulative forward wait for n-gram rows, shown per wall second. Maximum wait is a lifetime high-water gauge, not latest latency. Neither measures indexer timing or GPU utilization. |
| Executed request outcomes | Successful, errored and cancelled executed requests since process start. These are not all HTTP requests or pre-admission validation errors. |

Counters reset when the engine process restarts. Background cache and backend row-operation counters advance as operations occur, unlike request-finalized generation totals. Cached disk occupancy can reappear after restart without preserving counter values. Prompt-phase timing includes preparation/restoration overhead, so the last prefill rate is not a pure kernel benchmark. The configured 16 GiB disk cap is documented, not invented as a native metric. The 8 GiB RAM margin is not a cache cap or a desktop reservation.

No current-request token progression, time-to-first-token or inter-token distributions, total GPU/RAM allocation, indexer timing, native disk-cap gauge or pending cache-write gauge is exported by this pin. Host memory, GTT, disk and GPU sensors remain on the host dashboard and are separate accounting views, not additive quantities or guaranteed headroom.

## Collection and privacy

The integration reuses the same rootless monitoring containers and the existing Prometheus volume. It adds no device grants, host mounts, socket mounts, permissions, exporters, proxy or Pi traffic interception. Collection is localhost-only and requires no authentication under the current launcher. Host networking remains shared, not isolated. Keep all endpoints local, including the blackbox-exporter probe endpoint that accepts caller-supplied targets.

Prometheus retains 33 reviewed native metric families, currently 37 scalars. Only fixed job/loopback instance labels and bounded `outcome` and `reason` values survive relabeling; unreviewed metric names and nonempty unrecognized dimension values are dropped. Preserving the reviewed dimensions prevents collapsing the three outcomes or rejection reasons into duplicate samples. Each native scrape allows 100 retained samples; each probe scrape allows 10 and retains only success, duration and HTTP status. Publisher-added labels are otherwise removed, so a changed labeled variant can fail collection instead of being silently treated as the verified scalar. Review semantics after image changes.

No prompts, completions, source code, request IDs, cache keys, `/cache` polling or generation logs are stored. Probe response bodies are validated transiently, not retained. Existing [volume retention and lifecycle](monitoring.md#storage-and-overhead) still apply. Adding this scrape is not authorization to expose private conversation or filesystem state.

## Local validation

Validated October 11, 2026 with Strixite 0.2.3, native 256K and MTP on, using a fresh temporary SSD cache rather than the normal cache. The real wire response was 9433 bytes excluding HTTP headers. All 30 dashboard target expressions were accepted by real Prometheus and returned real series after generation. Collection retained 37 native scalars plus five automatic scrape series, with all three outcome and rejection-reason values preserved. Grafana returned the dashboard as provisioned and non-editable. A disposable browser rendered it and verified the stopped states without a data-source error.

The API check passed automatic tools, literal streamed arguments, deliberate truncation inspection, recall, short-prompt decode cancellation in 0.252 seconds and generation afterward. The shared-profile Bubblewrap Pi runner passed off and medium at 6.345 and 8.848 seconds, with five successful read/edit/bash calls each, strict original-JSON approval, preserved tags/marker recall and independent acceptance. These timings are single observations, not a new benchmark. Live Pi files stayed unchanged during validation. The provider installation happened separately before these checks.

Across 46 approximately one-second samples, minimum MemAvailable was 25.41 GiB, peak kernel GTT use 85.61 GiB and peak swap use 585.99 MiB. MemAvailable was 119.40 GiB before and 119.62 GiB after clean stop. Memory release passed; native current-value queries became empty. Stopping the probe exporter made readiness Unavailable. The actual blackbox policy accepted normal status ok and status ok with a degradation note, and rejected another status value, malformed JSON and HTTP 503 using local synthetic responses. No GPU-loss fault was induced. Monitoring, inference and the disposable browser were stopped afterward; named history volumes remain.

The pinned Prometheus tool passed configuration validation and focused synthetic query checks:

```bash
PYTHONDONTWRITEBYTECODE=1 python tests/strixite_metrics.py
```

Those checks protect reset handling, readiness versus collection health, historical speed retention, stopped-scrape gating and no-work ratio behavior. They are policy checks, not simulated engine compatibility. No controlled collection-overhead benchmark, new near-capacity test, deep-prefill cancellation or restart-cache integrity check was performed; those remain deferred.

## Sources

- [Pinned health and Prometheus exposition](https://github.com/shawnshekari/strixite/blob/dbe7b66ed620d392d0b3b6a8a6e836f9907ffea6/serve/http_server.cpp#L477-L646).
- [Pinned execution and counter update timing](https://github.com/shawnshekari/strixite/blob/dbe7b66ed620d392d0b3b6a8a6e836f9907ffea6/serve/engine.cpp).
- [Pinned prompt-cache accounting](https://github.com/shawnshekari/strixite/blob/dbe7b66ed620d392d0b3b6a8a6e836f9907ffea6/serve/prompt_cache.hpp).
- [Official blackbox-exporter probe configuration](https://github.com/prometheus/blackbox_exporter/blob/v0.29.0/CONFIGURATION.md).
