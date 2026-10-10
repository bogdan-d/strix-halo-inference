# 08: Display live Gufo inference metrics in Grafana

**What to build:** Extend the local dashboard with verified Gufo telemetry, using comparable labels where meanings agree and explicit engine-specific differences where they do not.

**Blocked by:** 06: Run an optional Grafana dashboard with host metrics.

**Status:** ready-for-agent

- [ ] Check the pinned Gufo release's actual telemetry and document sources, units and semantics before selecting panels. Prefer native telemetry and add a collector only for verified gaps without modifying the engine.
- [ ] Display supported readings for readiness, inference speed, token counts, context, cache behavior and speculative decoding. Identify unsupported measurements explicitly instead of fabricating them.
- [ ] Distinguish decode and prefill rates from aggregate throughput, counters from gauges, and configured context capacity from occupancy. Account for counter resets when the engine restarts. Do not force unlike engine measurements into misleading comparisons.
- [ ] Keep engine state distinct from scrape health. Stopping Gufo or switching to Halogen makes current Gufo readings unavailable or clearly inactive rather than leaving stale values looking live.
- [ ] Collection reaches the localhost-bound service without broadening its exposure and does not collect prompts, completions or source code. Document any additional access and measured collection overhead.
- [ ] Verify dashboard changes during a real generation request, after engine shutdown and after restart. The Gufo integration works without requiring the Halogen integration ticket to be complete. Record which proposed metrics the pinned release cannot provide.
