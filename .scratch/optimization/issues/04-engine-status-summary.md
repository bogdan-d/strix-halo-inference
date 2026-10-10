# 04: Show a useful engine status summary

**What to build:** Give the user a concise operational summary of the selected engine without requiring Grafana, using the running container and verified telemetry rather than assuming current pins describe the active process.

**Blocked by:** 01: Use engine-first launcher commands.

**Status:** resolved

- [x] Report container state, readiness, running image identity and version, configured context and MTP state for both engines. An image-pin update does not mislabel a still-running older image.
- [x] Show cache limits separately from actual disk or memory cache usage. Missing or unsupported readings are explicitly unavailable rather than zero or inferred from unrelated values.
- [x] Label engine-reported allocations, kernel GTT readings and host memory accounting with their sources. Warn that Halogen's pinned weights can make host available-memory readings misleading. Do not present free GTT as free physical RAM.
- [x] Missing, stopped, starting and unresponsive engines produce useful summaries without hanging. Preserve the operational contract that status is nonzero unless the engine is ready.
- [x] Document the readings and limitations. Verify ready and missing-container states and the running-image versus configured-pin distinction, with a real generation check for each engine.

## Comments

Completed with actual container configuration, inherited image labels, cache limits, bounded disk usage, verified startup-allocation log parsing and separately labeled host memory and GTT. Unsupported readings remain unavailable. Offline status checks cover pin and shell independence plus missing, stopped, loading and unreachable states. Both live engines passed status, smoke generation and conversation, tool-call and cancellation checks at 256K with MTP enabled. Both were stopped afterward, matching the initial state.
