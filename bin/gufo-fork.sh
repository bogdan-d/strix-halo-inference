#!/usr/bin/env bash
# Build the local Gufo image that merges LoRA adapters at load (docs/weight-profiles.md). It is the upstream
# toolboxes runtime image built from the pinned fork commit, so layout, user and extension SDK match GUFO_IMAGE.
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=../config/pins.env
source "$ROOT/config/pins.env"
SOURCE="${GUFO_FORK_SOURCE:-$ROOT/../gufo}"
[[ "$(git -C "$SOURCE" cat-file -t "$GUFO_FORK_REVISION" 2>/dev/null)" == commit ]] \
  || { echo "Commit $GUFO_FORK_REVISION is not in $SOURCE. Set GUFO_FORK_SOURCE to the fork checkout." >&2; exit 1; }
[[ "$(podman info --format '{{.Host.Security.Rootless}}')" == true ]] || { echo 'Use rootless Podman, not sudo.' >&2; exit 1; }
NAME="${GUFO_FORK_IMAGE%@*}"
TAG="$NAME:${GUFO_FORK_REVISION:0:12}"
# The Nix store volume caches the toolchain between builds. The fork's flake names its binary caches, and a rootless
# container cannot nest the Nix sandbox. The committed tree is built, never the working copy.
LOADED="$(podman run --rm --volume "${GUFO_FORK_NIX_VOLUME:-gufo-build-nix}:/nix" --volume "$SOURCE:/src:ro" \
  --env GIT_CONFIG_COUNT=1 --env GIT_CONFIG_KEY_0=safe.directory --env 'GIT_CONFIG_VALUE_0=*' \
  --env NIX_CONFIG=$'experimental-features = nix-command flakes\naccept-flake-config = true\nsandbox = false\nfilter-syscalls = false' \
  "$GUFO_FORK_NIX_IMAGE" sh -c '"$(nix build "$1" --override-input gufo-engine "$2" --no-link --print-out-paths)"' build \
  "github:gufo-org/toolboxes/$GUFO_FORK_TOOLBOXES_REVISION#stream-gufo-runtime-release" \
  "git+file:///src?rev=$GUFO_FORK_REVISION" | podman load | sed -n 's/^Loaded image: //p')"
[[ -n "$LOADED" ]] || { echo 'The image build produced nothing to load.' >&2; exit 1; }
# The definition names the image after the upstream registry; keep only the local name.
podman tag "$LOADED" "$TAG"
podman untag "$LOADED" "$LOADED"
REVISION="$(podman image inspect --format '{{index .Labels "org.gufo.engine.revision"}}' "$TAG")"
[[ "$REVISION" == "$GUFO_FORK_REVISION" ]] || { echo "Built image reports engine revision $REVISION." >&2; exit 1; }
BUILT="$NAME@$(podman image inspect --format '{{.Digest}}' "$TAG")"
echo "Built $TAG"
[[ "$BUILT" == "$GUFO_FORK_IMAGE" ]] || { echo "Set GUFO_FORK_IMAGE=$BUILT in config/pins.env." >&2; exit 1; }
