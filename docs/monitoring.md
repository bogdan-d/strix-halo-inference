# Optional monitoring dashboard

Run a local single-page dashboard independently of inference. Start and stop monitoring from this checkout:

```bash
bin/monitor.sh pull
bin/monitor.sh start
bin/monitor.sh status
```

`start` and `status` print the `file://` address of [the dashboard page](../config/monitoring/dashboard.html). Open it in a browser. It is one self-contained HTML file with no build step, dependency or server of its own. It reads the local Prometheus HTTP API directly. Nothing starts automatically at login. An inference engine does not require monitoring to be running.

Opened that way the page only reads. To also start and stop monitoring and engines and to read container logs from the page, use the [dashboard controls](#dashboard-controls) helper.

The page always shows host readings. Below them it shows whichever engine's metrics scrape is currently up, with headline speed, context, reuse and speculation readings, then charts and engine-specific extras. With no engine running it says so. Engine semantics are documented separately for [Halogen](halogen-monitoring.md), [Gufo](gufo-monitoring.md) and [Strixite](strixite-monitoring.md); similar headline names do not imply identical accounting. Hover over a reading for its caveat. Stop and restart monitoring to load new scrape/probe configuration; run `pull` first only when pinned images are missing or changed. Starting monitoring does not start an engine.

Use the header controls to choose the chart range (15 minutes, 1 hour or 6 hours) and the refresh interval (1, 2, 5, 10, 15 or 30 seconds, default 2). Both choices are remembered by the browser. Polling pauses while the tab is hidden.

```bash
bin/monitor.sh prometheus logs --follow
bin/monitor.sh exporter logs --follow
bin/monitor.sh probe logs --follow
bin/monitor.sh stop
```

The component comes before `logs`. Snapshot logs include the last 100 lines. Following ends when the container exits, and `Ctrl+C` stops only the viewer. Containers are auto-removed after stopping, so their logs are unavailable afterward. Logs use the file driver with a 10 MB size limit per container. Stopping preserves the Prometheus volume. Repeating `stop` is safe when the stack is already stopped.

## Dashboard controls

```bash
bin/dashboard.py
```

This optional helper serves the same page at `http://127.0.0.1:9099/` and runs the commands behind its buttons. It is one Python file using only the standard library and runs on the host, not in a container, because it has to call Podman through the existing launchers. It runs in the foreground and nothing starts it at login. `Ctrl+C` stops only the helper; engines and monitoring keep running. Set `DASHBOARD_PORT` to use another port.

Served by the helper, the page header gains:

- **Monitoring:** its state and one Start or Stop button. While monitoring is off the page says so instead of reporting a query error. Start still needs the pinned images from `bin/monitor.sh pull`.
- **Engine:** one button per engine, a Halogen + NPU button and a Stop button. Halogen + NPU starts Halogen with `NPU_MODELS` set to `decider-0.8b,embeddinggemma-2,qwen3guard-stream-0.6b`, or to `DASHBOARD_NPU_MODELS` if that was exported before starting the helper; hover over the button to see the set. The host setup in [NPU models](../README.md#npu-models) is still required, and Stop releases the fabric clock as `bin/run.sh halogen stop` does. A click starts that engine with the launcher defaults, or with `CONTEXT` and `SPECULATIVE` if they were exported before starting the helper. While any engine is starting, ready or stopping the other buttons are disabled, so switching needs an explicit stop first. The starting engine shows seconds since its container started until its health check passes. Engine controls work while monitoring is off.
- **Logs:** a drawer with one tab per container that follows its log, starting from the last 100 lines. It opens on an engine's tab when that engine is started, so a failed start is visible. Scrolling up pauses following. Tabs for containers that do not exist are disabled, and a stopped container's log is gone once it is removed.

Pull, update, diagnose, smoke and status stay in the terminal. A refused or failed command shows its last output line in the header; hover over it for the full output. State comes from Podman and each engine's health address every two seconds, so engines started or stopped in a terminal show up too.

The helper adds the first loopback endpoint here that acts instead of only reading, so its boundary is deliberately narrow:

- It binds `127.0.0.1` only and accepts only its own `Host` name, which defeats DNS rebinding.
- It refuses any request a browser marks as coming from another site, requires its own `Origin` on every command, and sends no cross-origin headers. Other pages open in the browser can neither run commands nor read state or logs.
- Each request path selects one fixed command line: `bin/run.sh <engine> start|stop|logs --follow`, `env NPU_MODELS=<set> bin/run.sh halogen start` or `bin/monitor.sh start|stop` and `bin/monitor.sh <component> logs --follow`. No request text reaches a command; the NPU model set comes from the helper's environment. The one-engine rule stays in `bin/run.sh`; the helper relays its refusal.
- It has no authentication. Any local process, under any local user, can still start or stop these engines and monitoring and read their logs through it. Do not run it on a shared host, and do not tunnel or expose the port.
- `GET /metrics` serves NPU readings for Prometheus, described under [NPU readings](#npu-readings). Like `/state`, it is readable by local processes but not by other sites' pages.
- Logs are streamed to the page and not stored. Closing the drawer, switching tabs or closing the page ends that log viewer. The Gufo log seen during validation held request metadata, not prompt text. The other engines and other settings were not reviewed, so treat the drawer like a terminal showing those logs.

## Stack and boundaries

| Component | Pinned version | Loopback interface | Persistent data |
|---|---|---|---|
| Prometheus | 3.15.0 | `127.0.0.1:9090` | Volume `strix-halo-monitor-prometheus` |
| node-exporter | 1.12.1 | `127.0.0.1:9100` | None |
| blackbox-exporter | 0.29.0 | `127.0.0.1:9115` | None |

Images come from Prometheus's official registry. Exact digests are in [monitoring pins](../config/monitoring/pins.env). The launcher uses installed images only. Run `pull` before the first start, or after deliberately changing those pins. `bin/update.sh` still updates engine images only, not this monitoring stack. Image changes require an explicit monitoring stop and restart. Back up monitoring data before version changes because older images may not understand migrated databases.

All three containers use rootless Podman, read-only root filesystems, dropped capabilities and no-new-privileges. Only Prometheus has a writable data volume. Its container user is mapped to the host user with `keep-id`, without changing host permissions. There are no privileged containers, GPU device grants, Podman socket mounts or whole-host filesystem mounts.

Host networking lets the services reach each other on loopback without a proxy or special host-gateway address. Each process binds explicitly to `127.0.0.1`, rather than relying on a port-publishing rule. Host networking is not network isolation. These processes can reach other host-local services. The endpoints have no network authentication for local readers, so keep them local and do not tunnel or expose them publicly without adding appropriate access controls. The dashboard page is a local file, not a network service. It works because Prometheus answers cross-origin reads from any origin by default, so any page open in a local browser could read these metrics too. That is acceptable only while the stored telemetry stays free of prompts and other private content.

Only node-exporter gets additional host mounts, all read-only:

- `/proc/stat` for aggregate CPU counters.
- `/proc/meminfo` for physical RAM and swap counters.
- `/proc/vmstat` for aggregate virtual-memory counters.
- `/proc/diskstats` for disk activity.
- `/proc/pressure` for pressure-stall information.
- `/sys` for DRM and hwmon sensors, including their symlink targets under the device tree.

There is no host PID namespace or whole `/proc` mount. The exporter cannot inspect host process environments through these mounts. It does not receive model weights, user directories, engine cache directories or conversation logs. The selected collectors are CPU, meminfo, vmstat, diskstats, pressure, DRM and hwmon. Filesystem, process-list and broad default collectors are not enabled. Prometheus separately scrapes reviewed Halogen, Gufo and Strixite aggregate metrics over their existing loopback endpoints, and the dashboard helper's [NPU readings](#npu-readings). The readiness probe receives only its read-only configuration and probes Gufo's `/ready` and Strixite's `/health`, without recording response bodies. Its local probe endpoint accepts caller-supplied targets, another reason not to expose this host-network service beyond loopback.

The page loads no external scripts, fonts or styles and sends requests only to `127.0.0.1:9090`. Its panel definitions and queries are a JSON block inside the same file, which the offline query-policy tests read.

## Read the dashboard

Prometheus scrapes every target every two seconds with a two-second timeout, so the default two-second refresh shows each new sample. A one-second refresh only shortens the delay before a new sample appears. Current rate readings use an eight-second window, four scrapes. Charts widen it to at least the chart step. Headline shares marked "5 min" use a fixed five-minute window so they stay readable between requests. Rates describe activity over their window, not an instantaneous speed.

| Reading | Source and meaning |
|---|---|
| CPU activity | Rates of `/proc/stat` CPU-time counters, averaged across logical CPUs. Non-idle includes I/O wait. |
| Physical RAM | `/proc/meminfo` total, free, available, and cache plus buffers plus reclaimable slab. These overlapping counters are deliberately not stacked. |
| Mapped file pages | `/proc/meminfo` `Mapped`, file pages mapped into any process. Charted with the other memory counters; it jumps by the weight size when Halogen loads. |
| Swap | Kernel total and free swap counters, with used swap shown as their difference. Existing swapped pages can remain after inference stops. |
| GTT | AMDGPU `mem_info_gtt_total` and `mem_info_gtt_used`, exported in bytes. Includes all GPU users, not only inference. |
| Memory pressure | Rates of cumulative PSI waiting and stalled seconds. The resulting percentages are not the kernel's `avg10` field. |
| Disk activity | Read and write byte-counter rates summed over whole NVMe, SCSI, virtio and MMC devices. Partitions, loop devices and device-mapper views are excluded to avoid duplicate accounting. |
| GPU load | AMDGPU `gpu_busy_percent`, from DRM sysfs. |
| GPU temperature | AMDGPU hwmon temperature in Celsius, normalized from millidegrees. |
| PPT power | AMDGPU hwmon power in watts, normalized from microwatts. On this APU, do not call it isolated GPU power or wall power. |

**Kernel counters are not engine allocations or guaranteed desktop headroom.** Halogen's pinned file-backed weights can still appear reclaimable in `MemAvailable`. Its GTT charge also excludes some resident weight memory. Do not add GTT usage to physical RAM usage or interpret free GTT as free RAM. The host section does not estimate memory left for applications or invent a live engine allocation. The Halogen section adds one labelled estimate for its pinned weights, described in [Halogen telemetry](halogen-monitoring.md#pinned-weights-and-memavailable). The existing engine `status` command separately labels measured startup allocation reports as historical.

The Collectors status names any failing collector. A missing sensor reading shows a dash, not a manufactured zero. Current values use instant queries gated on successful scrapes, so a stopped exporter does not leave its last reading looking current. Historical charts retain earlier samples and show gaps. If Prometheus cannot be reached, the page shows an error in its header and dims the last drawn readings; this is not an engine failure.

All requested readings are accessible on the validated Strix Halo host without changing permissions. On another host, verify the driver and exporter semantics before trusting sensor values. In particular, native DRM exporters can report zero defaults for unsupported fields, and metric presence alone cannot establish that a different driver supports the sensor.

## NPU readings

The NPU section appears while Halogen serves NPU models and `bin/dashboard.py` runs, because the helper collects these readings and Prometheus scrapes them from `127.0.0.1:9099/metrics` as job `npu`. If `DASHBOARD_PORT` changes, change that target in `prometheus.yml` too. Opened as a file without the helper, the page has no NPU section.

| Reading | Source and meaning |
|---|---|
| NPU busy | The amdxdna driver's sensor query (`DRM_AMDXDNA_QUERY_SENSORS` through `/dev/accel/accel0`), which passes on the power-management firmware's busy percentage per NPU column. The dashboard shows the mean of the eight columns; Halogen spreads its work over all of them, so they read alike. |
| NPU power | The same query's total NPU power in watts. It is part of PPT power, not an addition to it. |
| Models in NPU memory | Halogen's `/health` `npu.loaded` for each configured model. Large models take turns, so a served model can read no. |
| NPU requests queued | Halogen's `/health` `npu.queued`. |
| Locked memory | `/proc/meminfo` `Unevictable` for the whole host, where NPU models lock their memory. About 0.1 GiB is locked without them. |

The firmware averages its readings. On October 14, 2026, back-to-back embedding requests read 37 to 41% busy and about 1.5 W, the decider 41 to 44% and 1.15 W. Busy dropped to zero within four seconds of the last request, while power fell off over tens of seconds. Opening the NPU device wakes it from runtime suspend for five seconds, so the helper reads the sensors only while Halogen reports NPU models and answers 503 otherwise; with NPU models stopped, the NPU suspended while Prometheus kept scraping. `xrt-smi` 2.21.75 shows only the power reading, because it asks for one sensor. Halogen's own `/metrics` has nothing about the NPU.

## Storage and overhead

Prometheus keeps history until either seven-day or 2 GiB size-based retention applies. This is a retention policy, not a hard filesystem quota. The write-ahead log, active chunks and temporary compaction overlap require additional space. Expired-block cleanup is asynchronous. Two-second scraping stores 2.5 times the samples of the earlier five-second setup, so the size limit covers a shorter period. No prompt or completion text is stored by this stack.

Find the actual data locations with:

```bash
podman volume inspect strix-halo-monitor-prometheus
```

On this host it is under `~/.local/share/containers/storage/volumes/`, managed by rootless Podman. Sparse files have larger apparent sizes, and history grows as more samples arrive. The volume survives ordinary stop and start. Containers do not mount `/home/bogdan/models` or either inference cache.

An exploratory 60-second idle measurement with the browser closed and the earlier five-second scraping observed:

| Process | RSS snapshot | Mean CPU, where one logical CPU is 100% |
|---|---|---|
| node-exporter | 24 MiB | 0.38% |
| Prometheus | 99 MiB | 0.28% |

CPU was calculated from each process's native `process_cpu_seconds_total` counter. Memory came from `process_resident_memory_bytes`. RSS can include shared pages. This initial host-only measurement predates engine scraping, the readiness probe and two-second scraping; it is not the current stack's exact cost and was not repeated. Removing Grafana removed its measured 355 MiB RSS. The added readiness probe measured approximately 35 MiB RSS and 0.067% of one logical CPU in a later idle window. Engine collection costs and updated whole-Prometheus readings are documented in the separate engine guides. Startup, an open dashboard page and inference activity can raise resource use. Each refresh sends roughly 30 to 70 small queries to Prometheus, depending on the active engine. No peak-memory or controlled throughput comparison was performed.

## Troubleshooting and cleanup

- **Start fails:** use the reported error to check whether an image is missing, a name is occupied, or port 9090, 9100 or 9115 is in use. The launcher refuses to replace existing containers or reuse volumes without its ownership label.
- **Partial startup:** HTTP readiness is bounded to 60 seconds, with two-second probes. Failure or interruption stops containers whose IDs this invocation captured and retains volumes. If interrupted during container creation before its ID returns, inspect `podman ps -a` and use `bin/monitor.sh stop` to clean up the owned stack. No engine is stopped by that command.
- **Unavailable sensor:** inspect exporter logs and the collector-health panel. Verify the source is readable on the host. Do not fix it by granting privileged mode, exposing the Podman socket or changing device permissions.
- **No CPU rate yet:** allow several five-second scrapes to arrive. The default dashboard shows the last 15 minutes, which may initially contain mostly empty space.
- **Controls unavailable:** the page was served by `bin/dashboard.py` and can no longer reach it. Start the helper again; readings continue meanwhile. Opened as a `file://` address the page has no controls by design.
- **Dashboard changes:** edit the panel JSON block in the checked-in page and reload the browser tab. Keep `SCRAPE` in the page equal to `scrape_interval` in the Prometheus configuration. A scrape or launcher change needs a stop and start.
- **Page shows a query error:** check `bin/monitor.sh status`. The page needs Prometheus on `127.0.0.1:9090` and a browser that permits a local file to read it. Firefox was verified.
- **Lost history:** check whether the monitoring volume was removed or retention expired. Ordinary container removal does not delete the named volume. Back it up while monitoring is stopped before replacing storage or upgrading databases.

To permanently delete only monitoring data, first decide that the history is no longer needed. Stop the stack, inspect the exact volume, then remove only this name:

```bash
bin/monitor.sh stop
podman volume inspect strix-halo-monitor-prometheus
podman volume rm strix-halo-monitor-prometheus
```

This deletion is irreversible without a backup. A `strix-halo-monitor-grafana` volume and a pulled Grafana image left by the earlier Grafana setup are no longer used. The launcher never removes them. Delete that volume and image by name once you no longer want them. Do not use a global Podman prune. Weights, engine caches and unrelated containers are outside monitoring cleanup.

## Validation and sources

`PYTHONDONTWRITEBYTECODE=1 python tests/monitor.py` checks argument rejection, ownership guards, detached launch, partial-start rollback and preservation of volumes. Its CLI stubs test project policy, not compatibility with Podman. `PYTHONDONTWRITEBYTECODE=1 python tests/dashboard.py` runs the helper against script stubs and checks that foreign hosts, other sites' requests and commands without its origin are refused before any command runs, that only the listed paths map to commands, and that closing a log connection ends its viewer. Real-service validation of the page ran every panel query against real Prometheus, compared readings with each engine's raw `/metrics` after real generations, and rendered the page in headless Firefox. Engine generation checks and validation details are recorded in [local validation](validation.md).

- [node-exporter container and collector documentation](https://github.com/prometheus/node_exporter/blob/v1.12.1/README.md).
- [Pinned DRM collector and metric definitions](https://github.com/prometheus/node_exporter/blob/v1.12.1/collector/drm_linux.go).
- [Prometheus HTTP API](https://prometheus.io/docs/prometheus/latest/querying/api/).
- [Prometheus retention behavior](https://prometheus.io/docs/prometheus/latest/storage/).
