# 06: Run an optional Grafana dashboard with host metrics

**What to build:** Provide a separately containerized local monitoring setup in this repository, with a provisioned Grafana dashboard backed by live host telemetry. Inference remains independently usable when monitoring is stopped.

**Blocked by:** None (can start immediately).

**Status:** resolved

- [x] A documented manual workflow starts and stops independently managed rootless monitoring containers with immutable image pins, a provisioned data source and a usable dashboard. No automatic login service is introduced.
- [x] Show verified CPU, physical RAM, swap, GTT and memory-pressure readings. Include disk activity and GPU load, temperature and power where accessible, and explicitly identify unavailable readings.
- [x] Distinguish host accounting from engine allocations and practical-memory estimates. Explain the Halogen available-memory caveat and avoid presenting reclaimable cache or free GTT as guaranteed application headroom.
- [x] Keep published interfaces localhost-only and collector access minimal. Do not expose the Podman socket, mount model weights, collect conversation content, require privileged containers or change host kernel, BIOS or permissions.
- [x] Bound data retention and document storage, collection interval and measured CPU and memory overhead. Monitoring can restart without unexpectedly losing the retained history within its configured storage policy.
- [x] Verify live dashboard updates against host readings, monitoring restart and continued engine generation with monitoring both running and stopped. Document permissions, unavailable sensors and cleanup without deleting weights or engine caches.

## Comments

Completed an optional three-container stack using native node-exporter collectors, with loopback listeners, a provisioned read-only Grafana dashboard and persistent seven-day or 2 GiB size-based history retention. Host counter agreement, real queries, browser rendering, unavailable current values, retained restart history and occupied-port rollback were verified. Both engines passed generation and lifecycle checks with monitoring on and generated with it off. Idle process RSS totaled approximately 478 MiB, with approximately 1.25% of one logical CPU. Documentation records measurement limits and cleanup. Both engines and monitoring are stopped, retained volumes remain, and tickets 07 and 08 are untouched.
