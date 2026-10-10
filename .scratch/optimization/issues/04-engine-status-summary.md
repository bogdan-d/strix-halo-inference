# 04: Show a useful engine status summary

**What to build:** Give the user a concise operational summary of the selected engine without requiring Grafana, using the running container and verified telemetry rather than assuming current pins describe the active process.

**Blocked by:** 01: Use engine-first launcher commands.

**Status:** ready-for-agent

- [ ] Report container state, readiness, running image identity and version, configured context and MTP state for both engines. An image-pin update does not mislabel a still-running older image.
- [ ] Show cache limits separately from actual disk or memory cache usage. Missing or unsupported readings are explicitly unavailable rather than zero or inferred from unrelated values.
- [ ] Label engine-reported allocations, kernel GTT readings and host memory accounting with their sources. Warn that Halogen's pinned weights can make host available-memory readings misleading. Do not present free GTT as free physical RAM.
- [ ] Missing, stopped, starting and unresponsive engines produce useful summaries without hanging. Preserve the operational contract that status is nonzero unless the engine is ready.
- [ ] Document the readings and limitations. Verify ready and missing-container states and the running-image versus configured-pin distinction, with a real generation check for each engine.
