# Gufo inference dashboard

The current image is 0.15.0, pinned October 14. Its metrics and readiness scrapes were up during the October 14 [basic release checks](engine-updates.md), and every allowlisted name was stored. Wire types and semantics were not rechecked. 0.13.0 was never started on this host. On 0.12.0 the existing metric contracts remained compatible, and native scrape and independent readiness passed the [basic release checks](engine-updates.md). Detailed accounting and overhead measurements below were originally collected on 0.11.0 and were not repeated as benchmarks.

Open [the dashboard page](../config/monitoring/dashboard.html) after starting monitoring and Gufo. Its Gufo section appears while the engine's metrics scrape is up:

```bash
bin/monitor.sh pull
bin/monitor.sh start
bin/run.sh gufo start --wait
```

If either is already running, use the existing instance or explicitly stop and restart it. When upgrading an existing monitoring setup, stop monitoring, pull its new pinned readiness-probe image, then restart monitoring. Gufo itself needs no new image, flag or configuration. Start only one inference engine at a time. Monitoring does not start an engine, and inference works without monitoring.

Run Pi against Gufo as usual and watch the dashboard. Host readings are on the same page, above the engine section. Gufo's integration does not depend on Halogen metrics being available. Collection happens every two seconds and the page refreshes at the interval chosen in its header; very short requests can finish between scrapes. See [monitoring setup](monitoring.md).

## Readiness is not scrape health

- **Metrics scrape:** Prometheus could fetch and parse Gufo's native `/metrics`. This can succeed while the model is loading or not ready.
- **Readiness collection:** Prometheus could collect the HTTP probe's result. Up means the probe ran, not that Gufo passed it.
- **Model readiness:** the probe received HTTP 200 from `/ready` and parsed a JSON body with `status: ready`. Loading, shutdown, device loss or connectivity failure shows Not ready. If the probe exporter itself cannot be scraped, this shows Unavailable instead of trusting an old successful result. Ready does not guarantee an unoccupied execution slot.

Gufo 0.11.0 has no native Prometheus readiness gauge. The official Prometheus blackbox-exporter supplies that verified gap in a separately containerized monitoring service. Its HTTP probe has a two-second timeout, a 4 KiB response-body limit and no redirects. Malformed JSON, other status values and HTTP status codes other than 200 fail the probe. The launcher's monitoring `status` checks service availability, not model readiness.

Stopping Gufo makes native scrape health Down and model readiness Not ready after the next collections. Current native readings become Unavailable; historical charts retain earlier samples and show gaps. Stopping the probe makes readiness Unavailable even if native metrics remain reachable. Switching to Halogen does not make old Gufo values look current. The device-loss diagnostic depends only on native scrape health, so it can remain visible when model readiness fails.

## Gufo-specific accounting

These meanings were checked against the pinned Gufo 0.11.0 source and actual wire HELP and TYPE declarations. Do not assume that similarly named Halogen metrics have the same meaning.

| Panel | Native source and interpretation |
|---|---|
| Latest positive request processing speed | `llamacpp:prompt_tokens_seconds` and `llamacpp:predicted_tokens_seconds` are gauges containing the latest positive finished or cancelled request's stage speed, in tokens per processing second. They persist while idle; zero-work stages do not clear them. Zero before any measured stage is hidden, not presented as a measured speed. |
| Aggregate wall-time throughput | Reset-aware rates of `llamacpp:prompt_tokens_total`, `llamacpp:tokens_predicted_total` and `llamacpp:prompt_tokens_cached_total`, in tokens per wall second including idle time. Newly processed prompt and generated tokens advance during execution; cached tokens update at finish or cancellation. |
| Requests in flight | `llamacpp:requests_processing` counts admitted requests, including cache preparation and cleanup. `llamacpp:requests_deferred` counts requests waiting for a session. Both are gauges. |
| In-flight logical context share | `llamacpp:kv_cache_usage_ratio` divides whole admitted prompts plus generated output by sessions times per-session context. It includes prompt tokens before their prefill executes, excludes retained cache, and returns to zero while idle. It is not physical KV allocation or Halogen's busy-plus-held pool occupancy. |
| Largest completed sequence | `llamacpp:n_tokens_max` is a process-wide high-water mark of finished prompt-plus-output length. Although declared a counter upstream, it is not an additive total. Display it directly, not through `rate`. It is neither configured capacity nor current occupancy. |
| Token counters | Process-wide processed-prompt, cached-prompt and generated-token totals. Process restart resets them to zero. Execution counters can already contain work performed before a scheduler failure. |
| Approximate windowed reused-token share | Rate of cached prompt tokens divided by cached plus newly processed prompt-token rates. This is token reuse, not request cache-hit probability. Different execution and finish accounting clocks make it approximate over the window, especially for long or failed requests. No work makes it unavailable. |
| Draft acceptance share | Rate of `llamacpp:spec_decode_num_accepted_tokens_total` divided by `llamacpp:spec_decode_num_draft_tokens_total`. These update at finish or cancellation. No proposals makes the share unavailable. Acceptance alone does not demonstrate speedup. |
| Speculative proposal throughput | Proposed and accepted draft-token counter rates, in tokens per wall second. These can appear as completion-accounting bursts rather than live decoding progress. |
| Draft tokens per verification round | Proposed draft-token rate divided by `llamacpp:spec_decode_num_drafts_total` rate, which counts verification rounds. Not generated tokens per round or draft compute cost. |
| Confirmed device losses | `gufo_device_lost_total`, since process start. A fatal device-context loss leads to exit and can be missed between scrapes. Zero is not proof of GPU health. No device-loss fault was induced during validation. |

**Processing speed and throughput are different measurements.** Unlike Halogen, Gufo's execution token counters and finish-accounted `prompt_seconds_total` / `tokens_predicted_seconds_total` use different clocks. Dividing their rates would misrepresent a long in-flight request, so this dashboard uses Gufo's explicit historical speed gauges. The stage-time counters remain available as raw cumulative accounting, not dashboard speed ratios. Shared batched stage time is not a GPU busy stopwatch or end-to-end request latency.

Failed scheduler requests do not add finish-accounted cached tokens, stage time or speculative totals, although execution token counters may already have advanced. Cancellation does contribute finish accounting. Prometheus handles observed counter decreases as resets; raw total cards and the high-water mark reset after process restart. A restart between collections may be missed, and requests made while monitoring is stopped cannot be reconstructed into precise request history.

Configured context capacity is not exported by native metrics. The default launcher uses 262,144 tokens, but the dashboard deliberately does not hardcode that as a measured capacity. Use `bin/run.sh gufo status` for actual launch configuration. Context share must not be added to host GTT or interpreted as free RAM for desktop applications.

## Collection and privacy boundaries

Prometheus fetches `http://127.0.0.1:8080/metrics`; blackbox-exporter probes `http://127.0.0.1:8080/ready`. Both use the existing host-network boundary. The new exporter listens only on `127.0.0.1:9115` and receives only its read-only probe configuration, no host sensor mounts, GPU devices, weights, engine cache, Podman socket or user directory. Like the other monitoring services, it is rootless, has a read-only root filesystem, drops capabilities and uses no-new-privileges. It adds no persistent volume.

The probe endpoint accepts a target from its local caller and host networking is not network isolation. Do not expose it or Prometheus beyond loopback without separate access controls. The configured collection target is fixed to Gufo's local readiness endpoint. Probe response bodies are validated transiently, not stored as telemetry; debug probing is not enabled and probe logging is restricted to warnings. The readiness response includes model identity, not conversation content.

Native metric collection retains only 15 reviewed, unlabeled aggregate scalars. Probe collection retains only `probe_success`, `probe_duration_seconds` and `probe_http_status_code`. All publisher-provided labels are removed: stored labels are restricted to metric name, fixed job and loopback instance. Each native scrape allows at most 100 post-relabel samples, each readiness scrape 10. New metrics are dropped unless reviewed. Label stripping can make future labeled variants collide and fail collection rather than silently trusting changed semantics. This limits stored data, not what a future engine might return in its HTTP response.

No prompts, completions, source code, request IDs, cache keys, `/slots` polling or request-log parsing are collected. Gufo's current launcher sets no API key. If you separately enable authentication, metrics and readiness also need it; a private credential-file setup is not implemented here. Do not commit keys or broaden API exposure to repair collection. History stays in the existing [monitoring volumes and retention policy](monitoring.md#storage-and-overhead).

## Unsupported native measurements

- Configured per-request context capacity, physical KV occupancy and total live GPU or RAM allocation.
- Retained RAM/disk cache bytes, cache-entry limits, request cache-hit rate, separate disk versus RAM reuse, eviction totals or cache store/restore cost distributions.
- Request/completion totals, end-to-end latency distributions, time-to-first-token or inter-token distributions, and current-request processing speed.
- A native GPU-health gauge or proof of speculative speedup over autoregressive decoding.

Some per-request timing and cache details exist in generation responses, but collecting those responses would require a different instrumentation boundary. This stack does not intercept Pi traffic or invent aggregate telemetry from them. Host GPU sensors remain on the host dashboard.

## Measured collection cost

These measurements used the earlier five-second scrape interval and were not repeated at two seconds.

A native response was 2,466 bytes excluding HTTP headers. The job retains 15 native scalars, plus Prometheus's automatic scrape series. During a 60-second idle interval with the browser closed, native scrape duration averaged approximately 1.54 ms with a 2.31 ms maximum. Readiness-probe collection averaged 2.57 ms with a 3.32 ms maximum, including the exporter round trip. These are HTTP collection durations, not inference CPU time.

In separate 60-second idle windows, Gufo's container used approximately 0.027% of one logical CPU without monitoring and 0.039% with monitoring: a difference of approximately 0.012 percentage points. This single uncontrolled comparison includes background engine work and all monitoring requests; it does not establish the precise marginal cost of either endpoint.

The new blackbox-exporter used approximately 0.067% of one logical CPU and a 35 MiB RSS snapshot. Prometheus used approximately 1.03% and 103 MiB RSS with the host, Gufo, readiness and inactive Halogen jobs configured. These are whole-process measurements, not incremental Prometheus costs or peak memory. RSS may include shared pages. No controlled inference-throughput comparison was performed.

## Checks and sources

With the pinned Prometheus image pulled, run the offline query-policy check:

```bash
PYTHONDONTWRITEBYTECODE=1 python tests/gufo_metrics.py
```

It runs real pinned `promtool` in a temporary network-disabled container against synthetic sequences for reset handling, readiness versus scrape health, idle historical speed, high-water marks and zero-work ratios. These check dashboard policy, not engine compatibility. Actual compatibility, in-flight generation, cache reuse, shutdown, probe failure, restart and rendered states were checked separately; see [local validation](validation.md).

- [Pinned Gufo server metrics documentation](https://github.com/gufo-org/gufo/blob/v0.11.0/docs/SERVER.md#metrics).
- [Pinned metric exposition and readiness handlers](https://github.com/gufo-org/gufo/blob/v0.11.0/src/cli/serve/http_server.cpp).
- [Pinned counter and speed-gauge accounting](https://github.com/gufo-org/gufo/blob/v0.11.0/src/cli/serve/generation_metrics.hpp).
- [Pinned scheduler execution and finish accounting](https://github.com/gufo-org/gufo/blob/v0.11.0/src/cli/serve/text_generation_scheduler.cpp).
- [Official blackbox-exporter 0.29.0](https://github.com/prometheus/blackbox_exporter/releases/tag/v0.29.0) and [probe configuration](https://github.com/prometheus/blackbox_exporter/blob/v0.29.0/CONFIGURATION.md).
