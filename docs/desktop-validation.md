# Desktop validation

Validated on CachyOS/KDE Wayland on 2026-11-17, using rootless Podman builds and the installed host WebKitGTK runtime. No runtime packages, kernel settings, limits or sudo policy were changed. Engine starts used the existing launcher policy, including Halogen's existing fabric-clock helper when NPU models were requested.

## Checks exercised

- Release build and TypeScript strict checking passed. Six Rust tests cover metrics decoding, invalid/missing readings, fixed actions, busy-lock lifetime, externally started container state, partial monitoring, helper failures/timeouts and single-instance focus messaging. Native fixtures additionally cover profile/action validation, inherited-environment filtering, refusal propagation, close during an operation, streamed UTF-8 logs, reload/drawer/app-close viewer cleanup and saved state. The release omits the native test probe.
- Six real window restarts passed: resize, maximize, fullscreen from normal, fullscreen from maximized, exiting fullscreen and normal restore. F11 was dispatched through GTK's native key path. Ordinary launches did not write an inspector record.
- Inspector discovery, evaluation, screenshots, console and network capture worked against `@main`. Direct Prometheus queries succeeded in the real WebView. No frontend console errors were observed during the checked launches. Historical host charts and real Prometheus log following rendered successfully. A monitoring stop/start produced one expected connection-refused console entry during the transition; charts and controls recovered automatically with an empty error notice.
- Existing launcher, monitoring, cache, weights and browser-helper tests passed. All three promtool suites passed their reset/freshness/readiness/idle semantics checks; panel definitions were preserved in the HTML. The monitoring fixture covers collector-start failure rollback. NPU tests verify health gating without a device open, packed sensor decoding, bounded model labels, repeated start/stop, occupied-port failure and refusal to kill an unrelated PID.
- All three engines started and stopped through native app actions at their existing default weight profiles and native 262144 context. Halogen and Gufo passed `tests/live.py`; Strixite passed `tests/strixite_live.py`, including short-prompt generation, API tools and disconnect cancellation. Strixite released a disconnected request in about 0.25 seconds. These are short decode checks, not deep-prefill or long-context cancellation coverage.
- Halogen's desktop-launched NPU path worked with the existing 40 GiB hard memlock limit and noninteractive fabric-clock helper. A real `embeddinggemma-2` request returned a 768-dimensional embedding. The collector served busy/power/model/queue metrics. Closing and reopening the app left Halogen and the independent collector reachable. After Halogen stopped, the helper released the clock, the collector returned 503 and the NPU suspended while Prometheus remained running.
- Engines ran sequentially. Each stop left roughly 113–114 GiB MemAvailable and no active inference container before the next engine started. The launchers reported their existing non-crun-runtime notice; GPU-backed generation succeeded without changing the runtime. Halogen also emitted its existing warning that pinned weights can remain counted as reclaimable by the kernel; the dashboard retains that caveat.

The installed desktop entry passed `desktop-file-validate`. A Wayland protocol trace confirmed `xdg_toplevel.set_app_id("local.strix-halo.inference")`, matching the canonical desktop entry and icon. Launching the entry reused the existing app. The `gtk-launch` CLI probe emitted a GLib-GIO `g_dbus_connection_call_sync_internal` object-path assertion, but still launched/focused the app successfully. This warning came from the CLI launcher, not the app; its cause remains uninvestigated. If KDE menu launching shows the same problem, investigate the desktop activation path separately. The task-manager icon association is verified by that identity match, not a separate compositor screenshot.

## Performance method

The native measurement probe uses the actual bundled dashboard, real Prometheus host charts, header graphs and a live Prometheus log subscription. It records five one-second process-tree PSS samples per stage, with CPU time from `/proc` accounting including waited children. CPU percentage uses one core as 100%, not the whole 32-thread machine. Engines are stopped, so these figures cover the host dashboard, not every additional engine chart or a long session. The inspector is enabled for the measurement launch. Raw logs and samples are local under `cache/test/desktop-memory*` and are not committed.

| Stage | Median process-tree PSS | CPU, one core = 100% |
|---|---:|---:|
| Host charts, numeric header | 324.2 MiB | 5.06% |
| Host charts, header graphs and logs | 376.9 MiB | 9.68% |
| After minimize request (visibility unchanged) | 376.9 MiB | 4.27% |
| Explicitly hidden window | 376.6 MiB | 0.39% |

These are one final launch, five one-second samples per stage, not long-run bounds. Explicitly hiding the window set `document.hidden=true` and paused the page polls; the log subscription stayed open. WebKit retained its allocations while hidden. The minimize request left `document.hidden=false` and native visibility true, so it is not reported as a successful hidden-window test.

## Limits

The composited window's minimize request did not produce a minimized state in Tauri, and WebKit continued reporting `document.hidden=false`. A minimized-window polling pause is therefore not established on this Wayland setup. The probe distinguishes a minimize request from explicitly hiding the window. No KWin-specific workaround or pause-on-focus-loss policy was added.

The NPU test establishes device access, metric decoding, API operation and gating, not calibrated accuracy of firmware busy/power readings under a sustained load. Low memory at arbitrary context lengths, multiple simultaneous clients, HiDPI/multiple monitors and logout during lifecycle operations were not tested.

Inference and Den still have independent startup locks. The new inference guard rejects an already-running ComfyUI container, but simultaneous starts in both apps remain a documented race. No Den launcher change was made. Both real desktop binaries were also run simultaneously with fixture backends and separate scratch profiles: Den exposed its shell/dashboard views, Inference exposed its single main view, both storage directories stayed independent, and both closed cleanly. This coexistence check did not start ComfyUI or an inference engine.
