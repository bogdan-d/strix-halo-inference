# Desktop shortcut

The **Strix Halo Inference** entry opens the native Tauri dashboard. Build the app, then install or refresh the per-user shortcut:

```bash
bin/desktop.sh image
bin/desktop.sh build
bin/desktop.sh install
```

`install` writes `local.strix-halo.inference.desktop` under `${XDG_DATA_HOME:-~/.local/share}/applications`, installs its icon under that data directory's `icons/hicolor/128x128/apps`, and links the existing `strix-halo-inference-dashboard.desktop` names in Applications and `~/Desktop` to it. It needs no sudo and installs no runtime packages. Run it explicitly after moving the checkout, because the entry uses its absolute path.

The canonical desktop filename, icon name and native Wayland app ID match, so KDE associates the task-manager icon with the application. A second launch focuses the existing window. Closing the window leaves engines and monitoring running; a close during an operation asks you to wait. F11 toggles fullscreen, and normal size/maximized/fullscreen state is restored on the next launch. See the [desktop guide](desktop.md) for builds, logs and agent inspection.

There is no systemd user service or login autostart. Keeping the GUI out of a service whose whole cgroup is killed preserves Podman's detached container monitors and port forwarders. This avoids the earlier browser-helper cgroup cleanup failure documented in Git history.

For the browser fallback, run `bin/dashboard.py` and open `http://127.0.0.1:9099/`. `Ctrl+C` stops that helper and its viewers, leaving engines and monitoring running. The legacy `~/.local/bin/strix-halo-dashboard inference` wrapper, if still installed, remains a browser-fallback launcher; the desktop entry no longer calls it. Den's shortcut is independent and is not modified by the inference installer.
