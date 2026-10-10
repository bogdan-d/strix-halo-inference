# 07: Display live Halogen inference metrics in Grafana

**What to build:** Extend the local dashboard with verified Halogen telemetry so the user can observe real inference behavior and distinguish engine availability from telemetry collection health.

**Blocked by:** 06: Run an optional Grafana dashboard with host metrics.

**Status:** ready-for-agent

- [ ] Check the pinned Halogen release's actual telemetry and document sources, units and semantics before selecting panels. Prefer native telemetry and add a collector only for verified gaps without modifying the engine.
- [ ] Display supported readings for readiness, inference speed, token counts, context, cache behavior and speculative decoding. Identify unsupported measurements explicitly instead of fabricating them.
- [ ] Distinguish decode and prefill rates from aggregate throughput, counters from gauges, and configured context capacity from occupancy. Account for counter resets when the engine restarts.
- [ ] Keep engine state distinct from scrape health. Stopping Halogen or switching to Gufo makes current Halogen readings unavailable or clearly inactive rather than leaving stale values looking live.
- [ ] Collection reaches the localhost-bound service without broadening its exposure and does not collect prompts, completions or source code. Document any additional access and measured collection overhead.
- [ ] Verify dashboard changes during a real generation request, after engine shutdown and after restart. Record which proposed metrics the pinned release cannot provide.
