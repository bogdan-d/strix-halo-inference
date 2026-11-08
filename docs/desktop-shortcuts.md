# Desktop shortcuts for the dashboards

Start the ComfyUI dashboard of strix-halo-den and the engine dashboard of [strix-halo-inference](https://github.com/bogdan-d/strix-halo-inference) from the KDE desktop or application menu, without a terminal. The same note is in both repositories; the shortcuts live in the home directory, outside both.

A click starts the repository's `bin/dashboard.py` in the background, unless it already runs, and opens its page: `http://127.0.0.1:8189/` for strix-halo-den, `http://127.0.0.1:9099/` for strix-halo-inference. Right-click the icon and choose **Stop dashboard** to end the helper and its log viewers. Containers it started keep running, as with `Ctrl+C` in a terminal. Logging out also ends the helpers. Nothing starts at login.

The launcher deliberately does not use a systemd user unit. Stopping a unit kills its whole cgroup, which includes Podman's `conmon` and port forwarder for every container started from the dashboard. On this host that left ComfyUI running but unreachable, then stuck as exited until `podman rm`. Instead the launcher detaches the helper with `setsid` and stops its process group with `SIGTERM`. `SIGINT` does not work: Bash starts background jobs in scripts with `SIGINT` ignored, and Python keeps it ignored.

## Set up

Save this as `~/.local/bin/strix-halo-dashboard` and make it executable with `chmod +x ~/.local/bin/strix-halo-dashboard`. Adjust the two repository paths if they differ.

```bash
#!/usr/bin/env bash
# Start a Strix Halo dashboard helper in the background, unless it already runs, and open its page.
# With "stop", end the helper and its log viewers only; containers it started keep running.
# Not a systemd unit: stopping a unit kills its whole cgroup, including Podman's conmon for containers started from it.
set -euo pipefail
case "${1:-}" in
  den) ROOT=/var/mnt/xdata/code/strix-halo/strix-halo-den PORT=8189 ;;
  inference) ROOT=/var/mnt/xdata/code/strix-halo/strix-halo-inference PORT=9099 ;;
  *) echo 'Usage: strix-halo-dashboard den|inference [stop]' >&2; exit 2 ;;
esac
NAME="strix-halo-$1-dashboard"
RUNTIME="${XDG_RUNTIME_DIR:?}"
PIDFILE="$RUNTIME/$NAME.pid" LOG="$RUNTIME/$NAME.log"
URL="http://127.0.0.1:$PORT/"

# The recorded helper's PID, if it still runs. Guards against a reused PID.
helper() {
  local pid
  pid="$(cat -- "$PIDFILE" 2>/dev/null)" || return 1
  [[ "$pid" =~ ^[0-9]+$ ]] && tr '\0' ' ' <"/proc/$pid/cmdline" 2>/dev/null | grep -qF -- "$ROOT/bin/dashboard.py" && echo "$pid"
}

if [[ "${2:-}" == stop ]]; then
  if PID="$(helper)"; then
    # The helper leads its own process group; this also ends its log viewers. conmon and pasta run in their own sessions.
    kill -TERM -- "-$PID"
  fi
  rm --preserve-root=all --one-file-system -f -- "$PIDFILE"
  exit
fi
if ! helper >/dev/null; then
  # setsid detaches it from this launcher, so it outlives it and gets its own process group.
  PYTHONUNBUFFERED=1 setsid "$ROOT/bin/dashboard.py" >"$LOG" 2>&1 </dev/null &
  echo "$!" >"$PIDFILE"
fi
for _ in {1..50}; do
  if curl --fail --silent --output /dev/null --max-time 1 "$URL"; then
    exec xdg-open "$URL"
  fi
  sleep 0.1
done
notify-send --app-name="Strix Halo" "Dashboard did not start" "See $LOG"
exit 1
```

Then create one menu entry per dashboard and link each onto the desktop:

```bash
entry() { # id name comment icon
  cat > ~/.local/share/applications/strix-halo-$1-dashboard.desktop <<DESKTOP
[Desktop Entry]
Type=Application
Name=$2
Comment=$3
Exec=$HOME/.local/bin/strix-halo-dashboard $1
Icon=$4
Terminal=false
Categories=Development;
Actions=stop;

[Desktop Action stop]
Name=Stop dashboard
Exec=$HOME/.local/bin/strix-halo-dashboard $1 stop
DESKTOP
  ln -sfn ~/.local/share/applications/strix-halo-$1-dashboard.desktop ~/Desktop/strix-halo-$1-dashboard.desktop
}
entry den "Strix Halo Den" "Start the ComfyUI dashboard and open it on http://127.0.0.1:8189" applications-graphics
entry inference "Strix Halo Inference" "Start the inference engines dashboard and open it on http://127.0.0.1:9099" utilities-system-monitor
desktop-file-validate ~/.local/share/applications/strix-halo-*-dashboard.desktop
```

The launcher needs only Bash, coreutils, curl, `setsid`, `xdg-open` and `notify-send`, all present on this CachyOS KDE host. The helper's output goes to `$XDG_RUNTIME_DIR/strix-halo-<id>-dashboard.log`; if the page does not answer within five seconds, a desktop notification points there. The same commands work from a terminal: `strix-halo-dashboard den`, `strix-halo-dashboard den stop`.

Tested on 2026-11-08: a second click reuses the running helper; ComfyUI started from the dashboard stayed reachable after **Stop dashboard**, and a newly started helper then stopped it cleanly with memory released; the inference dashboard started and stopped. Starting an inference engine from a desktop-launched dashboard was not exercised.
