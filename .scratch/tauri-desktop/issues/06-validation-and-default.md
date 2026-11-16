# 06: Validate the port and make it the default

Status: resolved

Blocked by: [01](01-desktop-shell.md), [02](02-native-controls.md), [03](03-metrics-and-logs.md), [04](04-npu-collector.md), [05](05-gpu-exclusion.md)

Spec: [Tauri desktop port](../spec.md)

## Scope

Finish validation before changing the desktop shortcut. Retain relevant script/panel tests and native fixtures. Verify desktop-launched environment, including NPU memlock and the existing noninteractive fabric-clock helper; any needed host configuration remains an explicit separate host change.

Run short real engine checks one engine at a time: start, readiness, generation, cancellation, stop and memory release. Check app close during lifecycle actions, ordinary app close with a running engine, log-viewer cleanup, monitoring restart, NPU collector continuity and coexistence with Den. Do not interrupt user workloads. Measure process-tree memory and refresh CPU with representative charts/logs, including minimized behavior; record methods and limitations.

After the gates pass, make this app the default KDE entry with a proper independent icon and task-manager identity. Keep the browser fallback documented. Update README.md, docs/monitoring.md and docs/desktop-shortcuts.md. No distribution packaging, auto-updates or login service.

## Acceptance criteria

- [x] Offline, panel and native checks pass, with warnings and any untested cases recorded.
- [x] Each engine passes the agreed short live lifecycle checks; the NPU path is checked from the desktop launch environment.
- [x] Closing the app leaves active engine and monitoring endpoints reachable and only ends owned UI log viewers.
- [x] Memory/CPU observations cover idle, active charts/logs and hidden-window behavior; historical telemetry and sensor readings agree with their sources.
- [x] The new default shortcut opens/focuses the app with the correct Wayland/task-manager icon; browser fallback and operational/debugging docs remain usable.

## Comments

2026-11-17: Recorded at the user’s request for subsequent implementation. No implementation or runtime validation has started.

2026-11-17: Completed release/type/Rust/native fixtures, six window restarts, existing policy suites, all three short live engine tests, real NPU checks, monitoring recovery and process-tree PSS/CPU measurements. Installed the canonical KDE entry/icon and updated the existing shortcut; Wayland app-ID and desktop-entry validation passed. Final measurements: about 324 MiB PSS for host charts, 377 MiB with logs/header graphs, and 0.39% of one CPU core while explicitly hidden. The minimize request remained visible to WebKit; gtk-launch emitted a non-blocking GLib activation warning. These and untested scopes are recorded in docs/desktop-validation.md. All test apps, engines, monitoring containers and collectors were stopped. See [desktop validation](../../../docs/desktop-validation.md) and [operations/debugging](../../../docs/desktop.md).
