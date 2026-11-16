#!/usr/bin/env bash
# Build in Podman; run the native GUI against the host's existing WebKitGTK runtime.
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
IMAGE=localhost/strix-halo-inference/desktop-build:rust1.100
CACHE="$ROOT/cache/desktop"
# Node 26.13.1 LTS / Debian bookworm-slim.
NODE=docker.io/library/node@sha256:5df79989ed685e09f0a98019db4cebfb22fb9df1a53c0161664a011f7ff6b0f1
fail() {
  echo "$1" >&2
  if command -v notify-send >/dev/null; then notify-send --app-name=Inference 'Inference could not start' "$1"; fi
  exit 1
}
ACTION="${1:-run}"
[[ $# == 0 ]] || shift
PROFILE=release
FEATURES=()
INSPECT=0
for option in "$@"; do
  case "$option" in
    --debug) PROFILE=debug;;
    --agent-debug) FEATURES=(--features agent-debug);;
    --inspect) INSPECT=1;;
    *) echo "Unknown option: $option" >&2; exit 2;;
  esac
done
case "$ACTION" in
  install)
    [[ -x "$CACHE/target/release/inference-desktop" ]] || fail 'Build the release app before installing its shortcut'
    DATA="${XDG_DATA_HOME:-$HOME/.local/share}"
    ID=local.strix-halo.inference
    mkdir -p "$DATA/applications" "$DATA/icons/hicolor/128x128/apps" "$HOME/Desktop"
    install -m 644 "$ROOT/desktop/app/icons/icon.png" "$DATA/icons/hicolor/128x128/apps/$ID.png"
    python3 - "$ROOT" "$DATA/applications/$ID.desktop" <<'PYENTRY'
import sys
from pathlib import Path
root, entry = sys.argv[1:]
executable = (root + '/bin/desktop.sh').replace('\\', '\\\\').replace('"', '\\"').replace('`', '\\`').replace('$', '\\$').replace('%', '%%')
Path(entry).write_text('[Desktop Entry]\nType=Application\nName=Strix Halo Inference\nComment=Inference engines and system metrics\nExec="' + executable + '" run\nIcon=local.strix-halo.inference\nStartupWMClass=local.strix-halo.inference\nTerminal=false\nCategories=Development;\n')
PYENTRY
    ln -sfn "$DATA/applications/$ID.desktop" "$DATA/applications/strix-halo-inference-dashboard.desktop"
    ln -sfn "$DATA/applications/$ID.desktop" "$HOME/Desktop/strix-halo-inference-dashboard.desktop"
    echo "Installed $DATA/applications/$ID.desktop"
    ;;
  frontend)
    exec podman run --rm --userns keep-id --cap-drop=all --security-opt=no-new-privileges \
      -v "$ROOT:/src:rw" -w /src/desktop/app -e npm_config_cache=/src/cache/desktop/npm \
      "$NODE" npm exec --yes --ignore-scripts --package=npm@12.2.2 -- \
      sh -c 'npm ci --ignore-scripts && npm run build'
    ;;
  image)
    exec podman build --tag "$IMAGE" --file "$ROOT/containers/desktop/Containerfile" "$ROOT/containers/desktop"
    ;;
  build|lock|check|test)
    if [[ "$ACTION" != lock ]]; then "$ROOT/bin/desktop.sh" frontend; fi
    mkdir -p "$CACHE/cargo" "$CACHE/target"
    case "$ACTION" in
      build) COMMAND=(cargo build --locked); [[ "$PROFILE" == debug ]] || COMMAND+=(--release);;
      lock) COMMAND=(cargo generate-lockfile --offline);;
      check) COMMAND=(cargo check --locked);;
      test) COMMAND=(cargo test --locked);;
    esac
    COMMAND+=("${FEATURES[@]}")
    exec podman run --rm --userns keep-id \
      --cap-drop=all --security-opt=no-new-privileges \
      -v "$ROOT:/src:rw" -w /src/desktop/app -v "$CACHE/cargo:/cargo:rw" -v "$CACHE/target:/target:rw" \
      -e CARGO_HOME=/cargo -e CARGO_TARGET_DIR=/target \
      "$IMAGE" "${COMMAND[@]}"
    ;;
  run)
    [[ -x "$CACHE/target/$PROFILE/inference-desktop" ]] || fail 'Run bin/desktop.sh image and bin/desktop.sh build first'
    export INFERENCE_ROOT="$ROOT"
    # Never inherit an accidentally enabled fixed-port inspector into a normal launch.
    unset WEBKIT_INSPECTOR_HTTP_SERVER WEBKIT_INSPECTOR_SERVER
    if [[ "$INSPECT" == 1 ]]; then
      read -r a b c d e < <(od -An -N5 -tu1 /dev/urandom)
      export WEBKIT_INSPECTOR_HTTP_SERVER="127.$((a % 254 + 1)).$((b % 254 + 1)).$((c % 254 + 1)):$((20000 + (d * 256 + e) % 40000))"
    fi
    exec "$CACHE/target/$PROFILE/inference-desktop"
    ;;
  *) echo 'Usage: bin/desktop.sh [run [--inspect] [--debug]|install|image|frontend|lock|build [--debug] [--agent-debug]|check|test]' >&2; exit 2;;
esac
