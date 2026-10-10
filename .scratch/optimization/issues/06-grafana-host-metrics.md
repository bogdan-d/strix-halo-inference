# 06: Run an optional Grafana dashboard with host metrics

**What to build:** Provide a separately containerized local monitoring setup in this repository, with a provisioned Grafana dashboard backed by live host telemetry. Inference remains independently usable when monitoring is stopped.

**Blocked by:** None (can start immediately).

**Status:** ready-for-agent

- [ ] A documented manual workflow starts and stops independently managed rootless monitoring containers with immutable image pins, a provisioned data source and a usable dashboard. No automatic login service is introduced.
- [ ] Show verified CPU, physical RAM, swap, GTT and memory-pressure readings. Include disk activity and GPU load, temperature and power where accessible, and explicitly identify unavailable readings.
- [ ] Distinguish host accounting from engine allocations and practical-memory estimates. Explain the Halogen available-memory caveat and avoid presenting reclaimable cache or free GTT as guaranteed application headroom.
- [ ] Keep published interfaces localhost-only and collector access minimal. Do not expose the Podman socket, mount model weights, collect conversation content, require privileged containers or change host kernel, BIOS or permissions.
- [ ] Bound data retention and document storage, collection interval and measured CPU and memory overhead. Monitoring can restart without unexpectedly losing the retained history within its configured storage policy.
- [ ] Verify live dashboard updates against host readings, monitoring restart and continued engine generation with monitoring both running and stopped. Document permissions, unavailable sensors and cleanup without deleting weights or engine caches.
