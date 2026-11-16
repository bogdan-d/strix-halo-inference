# Porting Den's desktop app to strix-halo-inference

Planned on 2026-11-17 from source inspection of this repository and the sibling Den desktop app. Implementation has not started. No builds, engine starts, generation requests, collector reads or host changes were performed for the analysis. Preserve existing NPU history and streamed logs. This spec is self-contained; the original Den research note is not required.

Source baselines: inference main at f9c4517; Den main at e7749d8. Den reference files are in the sibling strix-halo-den checkout and are not runtime dependencies. Recheck code and dependency versions before implementation.

## Tickets and order

- [01 — Desktop shell and agent debugging](issues/01-desktop-shell.md): independent window, identity, build and inspector; start here.
- [02 — Native engine and monitoring controls](issues/02-native-controls.md): after 01.
- [03 — Historical metrics, host header and streamed logs](issues/03-metrics-and-logs.md): after 01 and 02.
- [04 — Independent NPU metrics collector](issues/04-npu-collector.md): after 02 and 03; preserve Prometheus history when the app closes.
- [05 — Cross-app GPU exclusion](issues/05-gpu-exclusion.md): after 02; address the one-way launcher guard and investigate simultaneous starts.
- [06 — Validate and make the desktop app default](issues/06-validation-and-default.md): after 01–05.

The numbered order is the default execution sequence. Dependent tickets remain pending until their listed prerequisites are resolved. All are specified for agent implementation; no implementation is authorized merely by recording this plan.

## Recommended result

A separate Tauri 2 application with one bundled dashboard WebView, a Rust control backend, the existing inference dashboard's charts, and Den's compact live-metrics header. It has its own application ID, icon, window state, browser profile, logs and inspector record. Den remains independent. Copy the small reusable desktop pieces initially; do not introduce a shared framework or a runtime dependency on the Den checkout.

Keep rootless Podman, engine images, model pins, weight manifests, cache locations and engine-specific launch configuration. Existing scripts remain the authority for engine lifecycle, model checks and cache operations. Expected script changes are narrowly scoped to NPU collector ownership and the cross-repository GPU guard, not an engine rewrite. No distribution packaging, updater, login service or host toolchain installation is needed for this personal-use app.

Closing the app leaves engines and monitoring running. It terminates only its own log viewers. Close is deferred while a start, stop or cache operation is in progress. Closing the UI must not stop a container's detached conmon or port-forwarding process.

## Reuse from Den

- [runtime.rs](../../../strix-halo-den/desktop/app/src/runtime.rs): window size/maximized/fullscreen persistence, native F11, focus-only single-instance behavior and rotated native logs. Adapt naming and storage; omit download/export helpers.
- [main.rs](../../../strix-halo-den/desktop/app/src/main.rs): Wayland app-ID registration and explicit inspector enablement. Use one normal WebView window instead of copying the child-WebView sizing and navigation machinery.
- [dashboard.rs](../../../strix-halo-den/desktop/app/src/dashboard.rs): command authorization, async process execution, finite timeouts and process-group cleanup. Adapt locks and result mapping to inference's existing per-target action states.
- [metrics.rs](../../../strix-halo-den/desktop/app/src/metrics.rs) and [shell.ts](../../../strix-halo-den/desktop/app/frontend/shell.ts): host readings, CPU/GPU temperatures, bounded two-minute graphs and saved numeric/graph preference. Integrate the strip into the existing dashboard header; no separate shell WebView or tab bar is necessary.
- [desktop.sh](../../../strix-halo-den/bin/desktop.sh), [Containerfile](../../../strix-halo-den/containers/desktop/Containerfile) and current dependency pins: reproducible Podman builds and release/debug/inspection entry points. Recheck stable versions when implementation starts. Omit ComfyUI's audio-sink preflight from a dashboard-only app.
- [browser.py](../../../strix-halo-den/tests/browser.py): retain the WebKit inspector discovery/evaluation/screenshot/console/network/input support, adapted to the new app's profile and view label. Do not copy ComfyUI prompt/generation helpers into the inference app's desktop helper.

Exclude the Library view, ComfyUI view and recovery logic, media handling, workflow downloads, ComfyUI job polling, unsaved-work dialogs and multi-WebView event forwarding. With one view, check that the Tauri unstable feature can be removed.

## Existing frontend and backend contract

The target's [dashboard.html](../../config/monitoring/dashboard.html) contains panel definitions, SVG charts and JSDoc-typed JavaScript. It has four transport points: Prometheus query(), helper state polling, action POSTs and the log stream. These are the migration boundaries; the panel meanings and rendering do not need a redesign.

The target's [dashboard.py](../../bin/dashboard.py) owns these behaviors:

- Halogen, Gufo and Strixite start/stop, including validated weight profiles and Halogen's optional NPU model set.
- Monitoring start/stop, per-engine prompt-cache size/clear and the existing second-click deletion confirmation.
- State derived from Podman and health endpoints, including externally launched containers, partial monitoring state, current operation, start time and running weight label.
- Per-target operation locks, 180-second action timeouts, refused-command output, and removal of inherited WEIGHTS, GUFO_MODEL and NPU_MODELS before explicit UI choices are applied.
- Six log sources: the three engines plus Prometheus, node-exporter and blackbox-exporter.
- The NPU metrics endpoint discussed below.

Move state/actions/log control to typed native commands with fixed engine/action enums, validated profile names and local-view permissions. Keep [weights.py](../../bin/weights.py) as the profile and extension-availability authority via short-lived calls. Avoid three Python launches and recursive cache walks on every two-second state refresh: refresh those slower-changing values separately and after relevant actions, while validating selected profiles again at launch.

Extract executable script and styles into bundled assets for the strict CSP. Preserve a single source for the panel JSON: [dashboard_panels.py](../../tests/dashboard_panels.py) and the engine metric tests currently read it from the HTML. The asset build must not strip the inert JSON script when replacing the executable script. Keep the browser dashboard available as a fallback without maintaining a second copy of panel definitions or frontend behavior.

Existing localStorage keys for range, refresh and selected profiles can stay, but the new WebView origin/profile will not automatically inherit browser preferences. Initial defaults are acceptable unless preference import is explicitly requested.

## Metrics transport and semantics

Keep Prometheus, node-exporter and blackbox-exporter. Their launch and scrape definitions are in [monitor.sh](../../bin/monitor.sh) and [prometheus.yml](../../config/monitoring/prometheus.yml). Two-minute in-memory header graphs complement the existing 15-minute, one-hour and six-hour charts; they cannot replace the stored history and PromQL rate calculations.

Prefer retaining the existing read-only browser fetches to http://127.0.0.1:9090, explicitly allowing just that origin in connect-src and verifying its existing CORS behavior in WebKitGTK. This preserves browser HTTP connection reuse, aborts and agent-visible network diagnostics. It does not add command endpoints. A fixed-endpoint Rust query adapter is a fallback if native-origin access fails; do not route dozens of queries through Den's small raw HTTP reader by default. The dashboard currently issues roughly 30–70 queries per refresh according to its monitoring docs.

Preserve scrape-health gates, unavailable-as-dash behavior, gaps, counter-reset handling, the eight-second default rate window, fixed five-minute overrides, aligned chart steps and per-engine meanings. Halogen, Gufo and Strixite do not use identical speed/context accounting. Keep the panel tests as the contract. Polling must not overlap when visibility or refresh settings change; verify this explicitly rather than assuming setTimeout alone prevents overlapping manual refreshes.

Keep optional-monitoring behavior: native controls and header sensors work while monitoring is off; historical panels explain that monitoring is off. Preserve the Halogen-specific MemAvailable caveat in its existing panels. In the inference header, label total-minus-MemAvailable as kernel-accounted RAM usage and expose the Halogen qualification when relevant; do not apply a Halogen correction to ComfyUI, Gufo or Strixite.

## NPU collection: preserve the existing feature

The Python dashboard helper is currently also the only NPU exporter. Prometheus scrapes 127.0.0.1:9099/metrics. Removing the helper without a replacement silently hides the NPU section. Busy/power come from amdxdna's sensor ioctl; loaded-model and queue information comes from Halogen's /health. See [dashboard.py](../../bin/dashboard.py) and [monitoring.md](../../docs/monitoring.md).

The recommended feature-preserving design is a small read-only NPU exporter whose lifetime belongs to optional monitoring, not to the desktop window. Reuse the existing standard-library Python collector initially, extracted from its dashboard command server; a Rust rewrite is optional and would need separate sensor-decoding/hardware validation. This keeps the app's control backend native without making a kernel ioctl rewrite a prerequisite. It introduces no new package dependency and no automatic login service. Keep the existing exporter until the replacement and endpoint ownership are verified; do not remove history as a shortcut.

Preserve the existing health gate: open the NPU device only when Halogen reports an npu object. Opening the device wakes it for about five seconds, so unconditional polling can keep an idle NPU awake. Stopping reads alone does not guarantee suspension while an engine is actively using it. Keep the Prometheus metric names and labels, and account for the legacy dashboard's ownership of port 9099 during migration. There must be only one collector/endpoint owner, without two processes racing to bind the same port.

An app-owned /metrics listener would be a smaller alternative, but NPU samples would stop when the window closes. In-process-only readings would additionally lose historical NPU charts. Those are explicit reductions in behavior, not the default port plan.

## Logs: preserve streaming

Keep the current follow semantics through a native subscription carrying bounded chunks over a [Tauri channel](https://v2.tauri.app/develop/calling-frontend/#channels). Add an explicit cancel operation and terminate/reap the owned viewer when the drawer closes, source changes, renderer exits or app closes. Bound the UI buffer by size as well as entries, and leave engine/container processes alone.

The existing [dashboard test](../../tests/dashboard.py) verifies viewer cleanup on connection close. Port that guarantee to subscription/renderer lifecycle tests. Den's periodically fetched tail snapshots are simpler, but can omit a burst larger than the tail between polls, so they are not equivalent to the current stream.

## Safety and operational findings

- Cross-repository GPU exclusion is currently one-way: Den's [run.sh](../../../strix-halo-den/bin/run.sh) refuses to start beside an inference engine, but inference's [run.sh](../../bin/run.sh) only checks inference-managed containers. Plan a launcher-level ComfyUI check plus clear UI refusal. Separate pre-start checks do not eliminate simultaneous-start races; inspect coordination before claiming strict cross-app exclusion. No launcher was modified in this analysis.
- Desktop-launched NPU starts must inherit a sufficient hard memlock limit and reach the existing sudo -n fabric-clock helper. Check these from the desktop launch environment, not just a terminal. Do not automatically change host limits or sudo configuration.
- Close during start/stop must be handled without terminating lifecycle helpers halfway through. Validate that the engine stays reachable after app exit; the sibling documents an earlier cgroup-cleanup failure in its [desktop shortcut guide](../../docs/desktop-shortcuts.md).
- Give the app an independent ID, icon, instance socket, WebView storage, window-state file and inspector record. Keep desktop data separate from per-engine caches that cache clearing deletes.
- Reuse WebKit inspector debugging from day one. Its unauthenticated endpoint remains off by default and uses Den's randomized loopback binding for explicit inspection sessions.

## Implementation sequence and completion gates

1. Scaffold the independent single-WebView app, build it in Podman, and prove bundled rendering plus inspector access, icon identity, F11, window persistence and coexistence with Den.
2. Port frontend transport and native controls. Keep launchers/model checks authoritative and preserve profile selection, environment filtering, operation states, cache confirmation and errors. Retain browser fallback.
3. Preserve Prometheus charts and stream logs. Integrate Den's compact host header, avoiding duplicate sampling. Keep the panel JSON contract and optional-monitoring behavior.
4. Decouple the NPU exporter from the dashboard controller, preserve its health gate and history, and resolve legacy endpoint ownership. Add the narrow cross-app launch guard.
5. Validate offline policy tests and native fixtures, followed by real start/readiness, short generation, cancellation, stop and memory-release checks one engine at a time. Include NPU startup/collector wake behavior and app-close-during-action checks. Do not interrupt a user workload to perform them.
6. Measure app/process-tree memory and refresh CPU with representative charts and logs. Verify polling while hidden and recovery when Prometheus stops. Only then update the desktop shortcut and user-facing README/monitoring/desktop docs to make the app default.

No runtime memory, chart compatibility, NPU ioctl behavior or real engine lifecycle was measured for this analysis. These remain implementation gates, not established outcomes. The source inspection found no reason to redesign the engines or the historical metrics model.
