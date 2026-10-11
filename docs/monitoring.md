# Optional host monitoring

Run a local Grafana dashboard independently of inference. Start and stop monitoring from this checkout:

```bash
bin/monitor.sh pull
bin/monitor.sh start
bin/monitor.sh status
```

Open [the host dashboard](http://127.0.0.1:3000/d/strix-halo-host). No login is required. Anonymous access is read-only, and dashboard changes belong in the checked-in configuration. Nothing starts automatically at login. An inference engine does not require monitoring to be running.

The same stack also provides separate [Halogen inference telemetry](halogen-monitoring.md) and [Gufo inference telemetry](gufo-monitoring.md) dashboards. When upgrading an existing setup, stop monitoring, run `pull` to install the new readiness-probe image, then restart monitoring to load the scrape configuration. Starting monitoring does not start an engine.

```bash
bin/monitor.sh grafana logs
bin/monitor.sh prometheus logs --follow
bin/monitor.sh exporter logs --follow
bin/monitor.sh probe logs --follow
bin/monitor.sh stop
```

The component comes before `logs`. Snapshot logs include the last 100 lines. Following ends when the container exits, and `Ctrl+C` stops only the viewer. Containers are auto-removed after stopping, so their logs are unavailable afterward. Logs use the file driver with a 10 MB size limit per container. Stopping preserves both monitoring volumes. Repeating `stop` is safe when the stack is already stopped.

## Stack and boundaries

| Component | Pinned version | Loopback interface | Persistent data |
|---|---|---|---|
| Grafana | 13.2.3 | `127.0.0.1:3000` | Volume `strix-halo-monitor-grafana` |
| Prometheus | 3.15.0 | `127.0.0.1:9090` | Volume `strix-halo-monitor-prometheus` |
| node-exporter | 1.12.1 | `127.0.0.1:9100` | None |
| blackbox-exporter | 0.29.0 | `127.0.0.1:9115` | None |

Images come from Grafana and Prometheus's official registries. Exact digests are in [monitoring pins](../config/monitoring/pins.env). The launcher uses installed images only. Run `pull` before the first start, or after deliberately changing those pins. `bin/update.sh` still updates engine images only, not this monitoring stack. Image changes require an explicit monitoring stop and restart. Back up monitoring data before version changes because older images may not understand migrated databases.

All four containers use rootless Podman, read-only root filesystems, dropped capabilities and no-new-privileges. Prometheus and Grafana have separate writable data volumes. Their container users are mapped to the host user with `keep-id`, without changing host permissions. There are no privileged containers, GPU device grants, Podman socket mounts or whole-host filesystem mounts.

Host networking lets the services reach each other on loopback without a proxy or special host-gateway address. Each process binds explicitly to `127.0.0.1`, rather than relying on a port-publishing rule. Host networking is not network isolation. These processes can reach other host-local services. The endpoints have no network authentication for local readers, so keep them local and do not tunnel or expose them publicly without adding appropriate access controls. Grafana's login form, basic authentication and sign-up are disabled. Its initial administrator password is randomly generated, not a public default.

Only node-exporter gets additional host mounts, all read-only:

- `/proc/stat` for aggregate CPU counters.
- `/proc/meminfo` for physical RAM and swap counters.
- `/proc/vmstat` for aggregate virtual-memory counters.
- `/proc/diskstats` for disk activity.
- `/proc/pressure` for pressure-stall information.
- `/sys` for DRM and hwmon sensors, including their symlink targets under the device tree.

There is no host PID namespace or whole `/proc` mount. The exporter cannot inspect host process environments through these mounts. It does not receive model weights, user directories, engine cache directories or conversation logs. The selected collectors are CPU, meminfo, vmstat, diskstats, pressure, DRM and hwmon. Filesystem, process-list and broad default collectors are not enabled. Prometheus separately scrapes reviewed Halogen and Gufo aggregate metrics over their existing loopback endpoints. The readiness probe receives only its read-only configuration and probes Gufo's `/ready`, without recording response bodies. Its local probe endpoint accepts caller-supplied targets, another reason not to expose this host-network service beyond loopback.

Grafana uses built-in panels and its built-in Prometheus data source. No additional plugins are installed. Plugin preinstallation, update checks, analytics reporting and the unused alerting subsystem are disabled.

## Read the dashboard

The dashboard refreshes every five seconds. Prometheus scrapes the host exporter every five seconds with a three-second scrape timeout. Rate charts need several samples after startup and use Grafana's rate interval. They describe activity over that interval, not an instantaneous speed.

| Reading | Source and meaning |
|---|---|
| CPU activity | Rates of `/proc/stat` CPU-time counters, averaged across logical CPUs. Non-idle includes I/O wait. |
| Physical RAM | `/proc/meminfo` total, free, available, and cache plus buffers plus reclaimable slab. These overlapping counters are deliberately not stacked. |
| Swap | Kernel total and free swap counters, with used swap shown as their difference. Existing swapped pages can remain after inference stops. |
| GTT | AMDGPU `mem_info_gtt_total` and `mem_info_gtt_used`, exported in bytes. Includes all GPU users, not only inference. |
| Memory pressure | Rates of cumulative PSI waiting and stalled seconds. The resulting percentages are not the kernel's `avg10` field. |
| Disk activity | Read and write byte-counter rates for whole NVMe, SCSI, virtio and MMC devices. Partitions, loop devices and device-mapper views are excluded to avoid duplicate accounting. |
| GPU load | AMDGPU `gpu_busy_percent`, from DRM sysfs. |
| GPU temperature | AMDGPU hwmon temperature in Celsius, normalized from millidegrees. |
| PPT power | AMDGPU hwmon power in watts, normalized from microwatts. On this APU, do not call it isolated GPU power or wall power. |

**Kernel counters are not engine allocations or guaranteed desktop headroom.** Halogen's pinned file-backed weights can still appear reclaimable in `MemAvailable`. Its GTT charge also excludes some resident weight memory. Do not add GTT usage to physical RAM usage or interpret free GTT as free RAM. This host-only dashboard intentionally does not estimate memory left for applications or invent a live engine allocation. The existing engine `status` command separately labels measured startup allocation reports as historical.

Collector health shows failures per collector. Sensor availability checks metric presence while the host scrape is up. Missing readings are unavailable, not manufactured zero measurements. Current-value panels use instant queries and gate readings on successful host scrapes, so a stopped exporter does not leave its last reading looking current. Historical charts retain earlier samples and show gaps. Prometheus failure appears as a data-source error, not an engine failure.

All requested readings are accessible on the validated Strix Halo host without changing permissions. On another host, verify the driver and exporter semantics before trusting sensor values. In particular, native DRM exporters can report zero defaults for unsupported fields, and metric presence alone cannot establish that a different driver supports the sensor.

## Storage and overhead

Prometheus keeps history until either seven-day or 2 GiB size-based retention applies. This is a retention policy, not a hard filesystem quota. The write-ahead log, active chunks and temporary compaction overlap require additional space. Expired-block cleanup is asynchronous. Grafana stores its provisioned dashboard metadata and settings in its separate volume, not the time-series history. No prompt or completion text is stored by this stack.

Find the actual data locations with:

```bash
podman volume inspect strix-halo-monitor-prometheus strix-halo-monitor-grafana
```

On this host they are under `~/.local/share/containers/storage/volumes/`, managed by rootless Podman. Early allocated disk usage was approximately 0.5 MiB for Prometheus and 1.6 MiB for Grafana. Sparse files have larger apparent sizes, and history grows as more samples arrive. Volumes survive ordinary stop and start. Containers do not mount `/home/bogdan/models` or either inference cache.

An exploratory 60-second idle measurement with the browser closed and five-second scraping observed:

| Process | RSS snapshot | Mean CPU, where one logical CPU is 100% |
|---|---|---|
| node-exporter | 24 MiB | 0.38% |
| Prometheus | 99 MiB | 0.28% |
| Grafana | 355 MiB | 0.58% |

CPU was calculated from each process's native `process_cpu_seconds_total` counter. Memory came from `process_resident_memory_bytes`. Summed RSS was approximately 478 MiB and includes potentially shared pages. This initial host-only measurement predates engine scraping and the fourth container; it is not the current stack's exact net physical-memory cost. The added readiness probe measured approximately 35 MiB RSS and 0.067% of one logical CPU in a later idle window. Engine collection costs and updated whole-Prometheus readings are documented in the separate engine guides. Startup, an open dashboard and inference activity can raise resource use. No peak-memory or controlled throughput comparison was performed.

## Troubleshooting and cleanup

- **Start fails:** use the reported error to check whether an image is missing, a name is occupied, or port 3000, 9090, 9100 or 9115 is in use. The launcher refuses to replace existing containers or reuse volumes without its ownership label.
- **Partial startup:** HTTP readiness is bounded to 60 seconds, with two-second probes. Failure or interruption stops containers whose IDs this invocation captured and retains volumes. If interrupted during container creation before its ID returns, inspect `podman ps -a` and use `bin/monitor.sh stop` to clean up the owned stack. No engine is stopped by that command.
- **Unavailable sensor:** inspect exporter logs and the collector-health panel. Verify the source is readable on the host. Do not fix it by granting privileged mode, exposing the Podman socket or changing device permissions.
- **No CPU rate yet:** allow several five-second scrapes to arrive. The default dashboard shows the last 15 minutes, which may initially contain mostly empty space.
- **Dashboard changes:** edit the checked-in JSON, not Grafana's database. File provisioning refreshes regularly. A data-source or launcher change needs a stop and start.
- **Lost history:** check whether a monitoring volume was removed or retention expired. Ordinary container removal does not delete these named volumes. Back up both volumes while monitoring is stopped before replacing storage or upgrading databases.

To permanently delete only monitoring data, first decide that the history and Grafana settings are no longer needed. Stop the stack, inspect the exact volumes, then remove only these names:

```bash
bin/monitor.sh stop
podman volume inspect strix-halo-monitor-prometheus strix-halo-monitor-grafana
podman volume rm strix-halo-monitor-prometheus strix-halo-monitor-grafana
```

This deletion is irreversible without a backup. Do not use a global Podman prune. Weights, engine caches and unrelated containers are outside monitoring cleanup.

## Validation and sources

`PYTHONDONTWRITEBYTECODE=1 python tests/monitor.py` checks argument rejection, ownership guards, detached launch, partial-start rollback and preservation of volumes. Its CLI stubs test project policy, not compatibility with Grafana or Podman. Real-service validation checked the provisioned dashboard, every panel query, host-counter agreement and retained history across restart. Engine generation checks and validation details are recorded in [local validation](validation.md).

- [node-exporter container and collector documentation](https://github.com/prometheus/node_exporter/blob/v1.12.1/README.md).
- [Pinned DRM collector and metric definitions](https://github.com/prometheus/node_exporter/blob/v1.12.1/collector/drm_linux.go).
- [Grafana file provisioning](https://grafana.com/docs/grafana/latest/administration/provisioning/).
- [Prometheus retention behavior](https://prometheus.io/docs/prometheus/latest/storage/).
