# 06: Validate the port and make it the default

Status: ready-for-agent

Blocked by: [01](01-desktop-shell.md), [02](02-native-controls.md), [03](03-metrics-and-logs.md), [04](04-npu-collector.md), [05](05-gpu-exclusion.md)

Spec: [Tauri desktop port](../spec.md)

## Scope

Finish validation before changing the desktop shortcut. Retain relevant script/panel tests and native fixtures. Verify desktop-launched environment, including NPU memlock and the existing noninteractive fabric-clock helper; any needed host configuration remains an explicit separate host change.

Run short real engine checks one engine at a time: start, readiness, generation, cancellation, stop and memory release. Check app close during lifecycle actions, ordinary app close with a running engine, log-viewer cleanup, monitoring restart, NPU collector continuity and coexistence with Den. Do not interrupt user workloads. Measure process-tree memory and refresh CPU with representative charts/logs, including minimized behavior; record methods and limitations.

After the gates pass, make this app the default KDE entry with a proper independent icon and task-manager identity. Keep the browser fallback documented. Update README.md, docs/monitoring.md and docs/desktop-shortcuts.md. No distribution packaging, auto-updates or login service.

## Acceptance criteria

- [ ] Offline, panel and native checks pass, with warnings and any untested cases recorded.
- [ ] Each engine passes the agreed short live lifecycle checks; the NPU path is checked from the desktop launch environment.
- [ ] Closing the app leaves active engine and monitoring endpoints reachable and only ends owned UI log viewers.
- [ ] Memory/CPU observations cover idle, active charts/logs and hidden-window behavior; historical telemetry and sensor readings agree with their sources.
- [ ] The new default shortcut opens/focuses the app with the correct Wayland/task-manager icon; browser fallback and operational/debugging docs remain usable.

## Comments

2026-11-17: Recorded at the user’s request for subsequent implementation. No implementation or runtime validation has started.
