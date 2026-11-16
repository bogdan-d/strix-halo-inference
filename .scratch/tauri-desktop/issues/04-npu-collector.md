# 04: Preserve NPU history outside the desktop lifecycle

Status: ready-for-agent

Blocked by: [02](02-native-controls.md), [03](03-metrics-and-logs.md)

Spec: [Tauri desktop port](../spec.md)

## Scope

Separate the existing read-only NPU exporter from the Python dashboard command server. Its lifetime belongs to optional monitoring rather than the desktop window, so closing the app does not stop Prometheus NPU sampling. Initially reuse the standard-library Python collector rather than making a Rust ioctl rewrite a prerequisite. No new package dependency or automatic login service is required.

Preserve the existing /health gate before opening the NPU device, metric names, bounded labels and loaded-model/queue semantics. Resolve port 9099 ownership with the browser fallback and legacy helper explicitly; there must be one collector and one endpoint owner. Integrate bounded start/stop, failure cleanup and ownership checks into the existing monitoring lifecycle. Keep the old endpoint working until the replacement is validated.

## Acceptance criteria

- [ ] Prometheus receives the existing npu_busy_percent, npu_power_watts, npu_model_loaded and npu_queued contract when applicable.
- [ ] NPU history continues with monitoring running after the desktop app closes.
- [ ] When Halogen has no npu object, the collector does not open /dev/accel/accel0; stopping monitoring stops only its owned collector.
- [ ] Legacy helper coexistence, occupied ports, partial startup, repeated start/stop and app restart cannot create duplicate collectors or stop unrelated processes.
- [ ] Fixture checks and a real opt-in NPU run verify readings, scrape gating and idle-device behavior; untested cases are documented.

## Comments

2026-11-17: Recorded at the user’s request for subsequent implementation. No implementation or runtime validation has started.
