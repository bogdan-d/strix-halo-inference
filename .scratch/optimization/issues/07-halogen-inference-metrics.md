# 07: Display live Halogen inference metrics in Grafana

**What to build:** Extend the local dashboard with verified Halogen telemetry so the user can observe real inference behavior and distinguish engine availability from telemetry collection health.

**Blocked by:** 06: Run an optional Grafana dashboard with host metrics.

**Status:** resolved

- [x] Check the pinned Halogen release's actual telemetry and document sources, units and semantics before selecting panels. Prefer native telemetry and add a collector only for verified gaps without modifying the engine.
- [x] Display supported readings for readiness, inference speed, token counts, context, cache behavior and speculative decoding. Identify unsupported measurements explicitly instead of fabricating them.
- [x] Distinguish decode and prefill rates from aggregate throughput, counters from gauges, and configured context capacity from occupancy. Account for counter resets when the engine restarts.
- [x] Keep engine state distinct from scrape health. Stopping Halogen or switching to Gufo makes current Halogen readings unavailable or clearly inactive rather than leaving stale values looking live.
- [x] Collection reaches the localhost-bound service without broadening its exposure and does not collect prompts, completions or source code. Document any additional access and measured collection overhead.
- [x] Verify dashboard changes during a real generation request, after engine shutdown and after restart. Record which proposed metrics the pinned release cannot provide.

## Comments

Completed a native-metrics scrape and separate Halogen dashboard with no new collector or image. Live generation, in-flight state, cache reuse, shutdown unavailability and real frontend counter resets were verified. Real promtool checks protect reset-aware rates, stale cache hiding, no-work windows and separate engine versus scrape health. Stored labels are restricted to metric name, fixed job and instance. Collection cost and unsupported metrics are documented, including the absence of a separate readiness or current-request context metric. Halogen and monitoring are stopped afterward, monitoring volumes are retained, and ticket 08 is untouched.
