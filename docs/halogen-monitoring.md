# Halogen inference dashboard

The current image is 0.18.0. Existing metric contracts remain compatible and its native scrape passed the [basic release checks](engine-updates.md). Detailed accounting and overhead measurements below were originally collected on 0.17.5. The two new rewrite/cut-back counters are intentionally not collected by the existing allowlist.

Open [Halogen telemetry](http://127.0.0.1:3000/d/strix-halo-halogen) after starting monitoring and Halogen:

```bash
bin/monitor.sh start
bin/run.sh halogen start --wait
```

If either is already running, do not start it again. Use the existing instance or explicitly stop and restart it. When upgrading from the host-only monitoring setup, restart monitoring once to load the new Prometheus scrape configuration. The engine itself does not need a new image, flag or restart for metrics. No new collector or container was added. The [host dashboard](http://127.0.0.1:3000/d/strix-halo-host) remains separate, under the same Strix Halo folder in Grafana.

Run Pi normally against Halogen and watch the dashboard. It refreshes and scrapes every five seconds. A short request may finish between scrapes, so you might never see a nonzero in-flight count even though token totals and rates update. Many measurements are completion-accounted, not token-by-token progress. There is no monitoring prerequisite for inference.

## Availability and freshness

- **Metrics scrape:** Prometheus could fetch and parse Halogen's public `/metrics` endpoint. Down can mean shutdown, authentication failure or network trouble. It is not proof of a particular engine failure.
- **Engine probe:** `halogen:engine_up` is Halogen's last engine liveness probe, also reported through `/health`. It is not a separate model-readiness guarantee or a promise that the next request can be admitted. A failed scrape makes this unavailable, rather than pretending the engine's last answer is current.
- **In-flight, deferred and busy age:** frontend gauges show current request counts and the age of the oldest request. These are not per-request latency distributions.
- **Cache snapshot age:** cache reporting is refreshed in the background. Cache panels hide snapshots aged 15 seconds or more. This is our display cutoff, not an upstream freshness promise. A busy engine can keep answering metric scrapes while cache reports become stale.

Stopping Halogen makes its scrape show Down within the next failed five-second collection. Current engine readings become Unavailable. Historical charts remain queryable and show gaps rather than interpolating across shutdown. Stopping monitoring does not stop Halogen. Switching to Gufo leaves Halogen's current readings unavailable because the engines have different endpoints. [Gufo telemetry](gufo-monitoring.md) uses independent scrape jobs and its own dashboard; similarly named metrics do not imply identical semantics.

## What each measurement means

Metric names and wire types below were checked against the pinned Halogen 0.17.5 endpoint. Gauges describe snapshots. Counters accumulate work within their reporting epoch.

| Panel | Native source and interpretation |
|---|---|
| Processing speed | `llamacpp:prompt_tokens_total / prompt_seconds_total` and `tokens_predicted_total / tokens_predicted_seconds_total`, calculated as ratios of reset-aware rates within the displayed interval. Tokens per summed processing second over completed requests. Prefill counts new processed tokens, not cached tokens. |
| Aggregate throughput | Rates of `llamacpp:prompt_tokens_total`, `llamacpp:tokens_predicted_total` and `halogen:prompt_tokens_cached_total`. Tokens per wall second, including idle time. Short completed requests can produce bursts. |
| Pool positions | `llamacpp:kv_cache_tokens` is engine-held positions across busy and warm held regions as of the last completed request. `halogen:kv_pool_positions` is pool capacity. `halogen:kv_pool_reserved_tokens` is the frontend's prompt-plus-output reservation, not actual occupancy. |
| Pool fraction and waiting | `llamacpp:kv_cache_usage_ratio` is held positions divided by pool capacity. `halogen:kv_pool_waiting_for_room` is a state gauge, not accumulated waiting time. |
| Completed requests | Reset-aware rate of `halogen:requests_total`. Frontend completion accounting and cache accounting follow separate paths. |
| Cache hit share | Rates of `halogen:cache_hits_total` divided by hits plus `halogen:cache_misses_total`. Request hit share, not token-cache share. No cache requests in the interval makes this unavailable. |
| Cache retention | `halogen:cache_entries`, `halogen:cache_bytes`, `halogen:cache_disk_bytes` and `halogen:cache_disk_budget_bytes`, with background age gating. Reported retained bytes are not a measurement of total RAM or the result of `du` over the cache directory. |
| Cache savings | `halogen:cache_prompt_tokens_saved_total` and `halogen:prompt_tokens_cached_total` are displayed separately. Different reporting paths or epochs mean they should not be summed or assumed equivalent. |
| Disk hits and evictions | Rates of `halogen:cache_disk_hits_total` and `halogen:cache_evicted_total`. Not a complete record of restore costs or why entries were forgotten. |
| Speculation | Rates of `halogen:draft_tokens_total` and `halogen:draft_tokens_accepted_total`. Acceptance share divides accepted proposals by all proposals in the rate window. Includes draft-head proposals and prompt-lookup proposals together. |
| Token totals | Current frontend processed-prompt, cached-prompt and generated-token counters. These are since frontend start, not persisted lifetime totals across restarts. |

Processing speed is not aggregate throughput. One divides by reported processing time, the other by wall time. The dashboard uses counter ratios instead of the native `prompt_tokens_seconds` and `predicted_tokens_seconds` gauges because those gauges cover requests since the last scrape. Another metrics reader can consume that window. Idle processing windows and intervals with no speculative proposals show Unavailable rather than NaN or a misleading zero speed.

Small processed prompt batches are dominated by fixed prefill costs. Their displayed rate is operational accounting, not a benchmark of cold-prompt throughput. Use substantial uncached prompts for that comparison.

**Pool capacity is not a per-request context limit.** The native metrics do not export `HALOGEN_CTX` or live current-request prompt occupancy. The launcher currently sets both request context and pool positions to 262,144, but those are different settings. Do not infer one from the other. Pool occupancy can include warm conversations between turns and stay unchanged during a long request. Engine-reported retained cache bytes can overlap other memory accounting and must not be added to GTT, pinned weights or physical RAM usage.

Prometheus `rate` handles observed counter decreases as resets. A real frontend restart reset generated-token and completed-request counters to zero during validation. Raw counter cards reset accordingly, while older history remains stored. Engine-only recovery, cache clearing and cache-counter epochs are not fully documented or validated. Requests completed while monitoring is stopped cannot be reconstructed into precise per-request history, and a restart between scrapes may not be detectable.

## Collection boundaries

Prometheus scrapes `http://127.0.0.1:8731/metrics` through its existing host network namespace. No new host access, mount, device permission or listener was introduced. Halogen's internal port 8730 remains unpublished. The job inherits five-second scraping and a three-second timeout, and retains at most 100 post-relabel samples per scrape.

The checked-in scrape configuration keeps only the exact verified aggregate metric names. It drops all publisher-provided labels, retaining only the metric name, fixed job and loopback instance. Build metadata is not stored. Live validation found no prompts, completions or cache keys in the native exposition, and persisted labels were limited to those three fields. Future publisher-added metrics are dropped unless explicitly reviewed. This controls stored telemetry, not what a future server could return in its HTTP response. If a future release turns an allowed scalar metric into multiple labeled series, removing labels can make them collide and fail the scrape rather than silently trusting new semantics.

The current launcher does not configure an API key. If you separately enable Halogen authentication, `/metrics` needs it too. Do not put keys in public configuration or broaden API exposure to fix a failed scrape. An authenticated monitoring configuration needs a separate private credential-file setup and is not implemented here. The job does not call `/cache`, inspect conversation files or parse request logs. Monitoring history remains in the existing bounded Prometheus volume.

## Supported limits

Native telemetry supports aggregate token accounting, processing-time rates, liveness, frontend request activity, pool snapshots, background cache reports and combined speculative proposals. It does not currently provide these dashboard measurements:

- A separate model-readiness metric or maximum context of one request.
- Token-by-token decode speed, current-request context progress or per-request latency percentiles.
- Total live engine RAM allocation or guaranteed desktop headroom.
- Cache-entry capacity, full versus partial matches, complete dropped or superseded counts, or a breakdown of store and restore costs.
- Separate MTP and prompt-lookup acceptance, or a demonstrated speculative speedup against autoregressive decoding.

These omissions are explicit. There is no custom collector to invent or approximate them. Refer to [Halogen's pinned telemetry documentation](https://github.com/peonist-ai/halogen-flash-server/blob/v0.17.5/README.md#L537-L588) and [the cache-metrics discussion](https://github.com/peonist-ai/halogen-flash-server/issues/156) for the publisher's reporting limits.

## Measured collection cost

The job retained 28 native scalar samples per scrape. A measured native response was approximately 5.4 kB, excluding HTTP headers. During a 60-second idle interval, the mean round-trip scrape duration was approximately 102 ms and the maximum was 204 ms, both below the three-second timeout. These are HTTP collection times, not CPU time spent evaluating the model.

The engine container consumed approximately 0.246% of one logical CPU during a preceding 60-second idle interval without monitoring, and 0.289% with monitoring. The difference was approximately 0.044 percentage points. This is one uncontrolled comparison that includes background engine work and the monitoring stack's polling, not a statistically established marginal cost of `/metrics`. A first monitored interval overlapped a generation check and was excluded from this idle comparison.

With host and Halogen scraping enabled and the browser closed, Prometheus used approximately 0.98% of one logical CPU and a 110 MiB RSS snapshot in the final interval. These are whole-process measurements, not incremental Halogen-only memory or CPU costs. No extra exporter process was introduced. There was no controlled inference-throughput or peak-memory comparison with scraping enabled and disabled.

## Verification

With the pinned Prometheus image already pulled, run the offline query-policy check:

```bash
PYTHONDONTWRITEBYTECODE=1 python tests/halogen_metrics.py
```

It invokes the real pinned `promtool` in a temporary, network-disabled container. Synthetic counter and gauge sequences test our reset, availability, freshness and idle-window expressions, not Halogen compatibility. The container sees only its temporary test input. Live compatibility was checked separately against the actual pinned engine, completed generation requests, shutdown and restart. Results and collection measurements are recorded in [local validation](validation.md).
