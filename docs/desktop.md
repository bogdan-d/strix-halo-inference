# Inference desktop

The desktop app bundles the existing dashboard in one Tauri 2 WebView. Rust runs the fixed engine/monitoring/cache commands through the existing launchers; it needs no Python dashboard server. The optional browser dashboard shares the same chart and control code. Engines, model pins, weights and prompt caches keep their existing locations and settings.

## Build and run

The host uses its existing GTK 3 and WebKitGTK 4.1 runtime. Build tools run only in rootless Podman. No host compiler, Node or Python package installation is needed.

```bash
bin/desktop.sh image
bin/desktop.sh build
bin/desktop.sh run
```

`build` produces `cache/desktop/target/release/inference-desktop`. `--debug` selects the development build. Rebuild after changing bundled assets. No updater, distribution packaging or login service is installed.

The app restores normal size, maximization and fullscreen state. Press F11 to toggle fullscreen. A second launch focuses the existing window for this checkout. The app ID is `local.strix-halo.inference`, independent of Den. Browser storage, window state, inspector record and rotated native logs live under `cache/desktop/`, outside engine prompt caches.

Closing the window leaves engines and monitoring running. Closing during a start, stop or cache operation is refused until that operation finishes. Ordinary close cancels and reaps only the app's log viewers. Start/stop remains explicit; changing a weight selection never replaces a running engine. Profile availability and cache sizes refresh every 30 seconds and after operations; live container state refreshes every two seconds.

Choose **Image input** on the engine card before clicking **Start** or Halogen’s **Start with NPU**. The checkbox defaults off for Halogen and Gufo and on for Strixite when its vision files are installed. A disabled checkbox with a download command means that the selected profile needs vision files. You can start it with text input while those files are missing. Once running, the card shows the configured vision mode and, for Gufo, the Pi model ID to select.

Click anywhere in the header metrics to toggle the two-minute graphs. The mode persists; history does not. Temperature is CPU / GPU. APU power includes CPU power. RAM* is kernel-accounted usage (`MemTotal - MemAvailable`); Halogen's pinned weights can still appear reclaimable, so this understates use while Halogen has them loaded. GTT overlaps RAM and is never added to it. These header readings work without monitoring; the historical dashboard charts require `bin/monitor.sh start`.

## Agent debugging

```bash
bin/desktop.sh run --inspect
tests/browser.py views
tests/browser.py eval @main - <<<'document.title'
tests/browser.py shot @main cache/test/dashboard.png
tests/browser.py console @main
tests/browser.py network @main 3 reload
tests/browser.py click @main '#logs'
```

The helper supports evaluation, screenshots, console history, network capture, synthetic clicks/drags/typing/keys and raw inspector methods. Its docstring lists commands. This is WebKit's inspector protocol, not CDP. Input is DOM-dispatched and untrusted, so it cannot drive native dialogs or the native F11 shortcut. Network capture has no prior history or response bodies. Commands serialize per view; a long capture holds the inspector until it finishes.

Inspection is chosen at startup. Close an ordinary app before launching `--inspect`; a second launch only focuses it. The inspector is unauthenticated and permits code execution in the privileged dashboard. Explicit inspection uses a random loopback address/port recorded in a mode-600 file; ordinary launch clears inherited inspector variables and opens no inspector. Local processes can still discover it. Do not publish its address. Rerun discovery/evaluation/screenshot/console checks after WebKitGTK upgrades.

## Checks

```bash
bin/desktop.sh test
tests/browser.py desktop-check
bin/desktop.sh build --agent-debug
tests/browser.py desktop-window-check
bin/desktop.sh build
python3 tests/npu_exporter.py
python3 tests/dashboard.py
python3 tests/run.py
python3 tests/monitor.py
python3 tests/halogen_metrics.py
python3 tests/gufo_metrics.py
python3 tests/strixite_metrics.py
```

The native IPC fixture uses independent storage and stub launchers, not real engines. With monitoring running and engines stopped, `tests/browser.py desktop-memory` measures charts, logs, a minimize request and an explicitly hidden window. The window check uses native GTK key events and six real restarts; its probe exists only in `--agent-debug` builds. Restore a normal release build afterward. The existing live engine tests require an already-ready engine and run short generation and cancellation checks; run one engine at a time and never interrupt a user workload.

## Implementation boundaries

The page's existing JSDoc-typed chart implementation remains a single checked JavaScript source at `config/monitoring/dashboard.js`. The native transport and header are strict TypeScript. Both pass TypeScript 7 checking during every build. This avoids rewriting the proven chart implementation merely to change its syntax. Panel JSON remains in `dashboard.html`, where the Prometheus tests read it. The browser fallback serves the shared CSS and JavaScript with no build step.

The WebView directly queries the read-only Prometheus API at `127.0.0.1:9090`; its CORS behavior was checked in WebKitGTK. CSP permits that one network origin, local assets and Tauri IPC. Inline styles are allowed for the existing chart styling; inline scripts are not. Native commands also check the bundled origin and view label. No native command accepts arbitrary executable paths or shell text. Logs stream through Tauri channels, with explicit cancellation, renderer/reload cleanup and a bounded display buffer.

NPU collection belongs to monitoring. `bin/npu-exporter.py` serves read-only metrics on `127.0.0.1:9098`; it uses the existing standard-library Python ioctl reader, with Halogen's health gate before opening the device. Monitoring starts/stops it independently of the GUI. Locked lifecycle files, a process identity check and Linux pidfds guard shutdown against PID reuse. The browser helper keeps port 9099 and proxies its legacy `/metrics` path to the collector. Restart old browser helpers after updating; stop/start monitoring to reload the scrape target. No second collector should scrape the device through an old helper.

Inference refuses starts while Den's named ComfyUI container runs. This closes the previous one-way check, but the launchers use independent startup locks: simultaneous starts across both repositories are still a race. A shared lock needs a coordinated Den change; this port does not claim strict cross-app exclusion.

## Dependency pins

Direct dependencies were rechecked against crates.io and npm on 2026-11-17: Tauri 2.12.6, tauri-build 2.7.5, serde 1.0.229, serde_json 1.0.154, Tokio 1.54.1, libc 0.2.191, WebKitGTK bindings 2.0.2, TypeScript 7.0.2 and npm 12.2.2. GTK bindings remain 0.18.2 because that is the API version shared by Tauri/wry and WebKitGTK; the newer 0.19 line is not a compatible substitution. Rust 1.100 and Node 26.13.1 LTS build images are digest-pinned. Cargo.lock and package-lock.json fix the resolved dependency graph. [Tauri releases](https://github.com/tauri-apps/tauri/releases), [TypeScript releases](https://github.com/microsoft/TypeScript/releases) and [Node 26.13.1](https://nodejs.org/en/blog/release/v26.13.1/) document the selected release lines.

See [desktop validation](desktop-validation.md) for measurements and exercised behavior.
