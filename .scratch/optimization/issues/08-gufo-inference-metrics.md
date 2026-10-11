# 08: Display live Gufo inference metrics in Grafana

**What to build:** Extend the local dashboard with verified Gufo telemetry, using comparable labels where meanings agree and explicit engine-specific differences where they do not.

**Blocked by:** 06: Run an optional Grafana dashboard with host metrics.

**Status:** resolved

- [x] Check the pinned Gufo release's actual telemetry and document sources, units and semantics before selecting panels. Prefer native telemetry and add a collector only for verified gaps without modifying the engine.
- [x] Display supported readings for readiness, inference speed, token counts, context, cache behavior and speculative decoding. Identify unsupported measurements explicitly instead of fabricating them.
- [x] Distinguish decode and prefill rates from aggregate throughput, counters from gauges, and configured context capacity from occupancy. Account for counter resets when the engine restarts. Do not force unlike engine measurements into misleading comparisons.
- [x] Keep engine state distinct from scrape health. Stopping Gufo or switching to Halogen makes current Gufo readings unavailable or clearly inactive rather than leaving stale values looking live.
- [x] Collection reaches the localhost-bound service without broadening its exposure and does not collect prompts, completions or source code. Document any additional access and measured collection overhead.
- [x] Verify dashboard changes during a real generation request, after engine shutdown and after restart. The Gufo integration works without requiring the Halogen integration ticket to be complete. Record which proposed metrics the pinned release cannot provide.

## Resolution

Gufo 0.11.0 native aggregate metrics and an official blackbox-exporter readiness probe feed an independently provisioned dashboard. Verified semantics, unsupported measurements, privacy boundaries and measured idle cost are documented in the Gufo monitoring guide. Real generation, cache reuse, probe failure, shutdown, counter reset and rendered failure states passed; Halogen remained stopped throughout. Both engines and monitoring are stopped after validation, with history retained. The pinned promtool checks test reset, readiness, historical-speed and no-work query policies separately from engine compatibility.
