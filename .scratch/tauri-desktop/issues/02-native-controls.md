# 02: Native engine and monitoring controls

Status: ready-for-agent

Blocked by: [01](01-desktop-shell.md)

Spec: [Tauri desktop port](../spec.md)

## Scope

Replace the dashboard helper’s command/state transport with typed Rust commands. Preserve Halogen, Gufo and Strixite starts/stops, selected weight profiles, Halogen + NPU, monitoring lifecycle, cache sizes/confirmation and errors. Keep run.sh, cache.sh, monitor.sh and weights.py authoritative for their current responsibilities; do not change model pins or engine settings.

Preserve per-target busy states, operation timeouts, inherited-environment filtering and live Podman/health-derived state. Use short-lived weights.py calls with sensible refresh frequency rather than reimplementing profile rules or spawning Python on every two-second poll. Avoid recursive cache scans every poll. Defer app close while lifecycle/cache operations are active. Ordinary app close leaves engines and monitoring running. Preserve the browser fallback through shared frontend behavior and a small transport boundary, not duplicated panel/control implementations.

## Acceptance criteria

- [ ] Every permitted action maps to fixed validated argv; unknown engines/actions/profiles cannot execute arbitrary commands.
- [ ] Selected profiles and NPU model choices override the same inherited variables as today; refused starts retain actionable output.
- [ ] State follows CLI-launched/stopped containers, running weight labels and partial monitoring; controls work when monitoring is off.
- [ ] Cache clearing keeps its second-click confirmation and launcher restrictions.
- [ ] Policy/timeout/operation tests cover the current tests/dashboard.py contract as applicable to IPC; close during start/stop cannot terminate detached container monitors.

## Comments

2026-11-17: Recorded at the user’s request for subsequent implementation. No implementation or runtime validation has started.
