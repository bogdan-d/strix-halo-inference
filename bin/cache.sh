#!/usr/bin/env bash
# Show or clear the engines' prompt caches. Clearing deletes the files; the next turn of every conversation
# then processes its whole prompt once. Weights are never touched.
set -euo pipefail
usage() {
  echo 'Usage: bin/cache.sh halogen|gufo|strixite|all status|clear' >&2
  exit 2
}
[[ $# == 2 ]] || usage
case "$1" in
  halogen|gufo|strixite) ENGINES=("$1") ;;
  all) ENGINES=(halogen gufo strixite) ;;
  *) usage ;;
esac
ACTION="$2"
case "$ACTION" in status|clear) ;; *) usage ;; esac
CACHE_ROOT="$(realpath -m -- "${CACHE_ROOT:-$HOME/.cache/strix-halo-inference}")"
[[ "$CACHE_ROOT" != / && "$CACHE_ROOT" != "$(realpath -- "$HOME")" ]] || { echo 'CACHE_ROOT must be a dedicated cache directory.' >&2; exit 1; }

if [[ "$ACTION" == clear ]]; then
  mkdir -p -- "$CACHE_ROOT"
  # bin/run.sh holds this lock while it starts an engine, so nothing starts while a cache is cleared.
  exec 9>"$CACHE_ROOT/start.lock"
  flock -n 9 || { echo 'An engine start is in progress. Try again when it has finished.' >&2; exit 1; }
  # A running engine has its cache open. Check every engine before deleting anything.
  for ENGINE in "${ENGINES[@]}"; do
    ! podman container exists "strix-halo-$ENGINE" || { echo "Stop $ENGINE before clearing its cache: bin/run.sh $ENGINE stop" >&2; exit 1; }
  done
fi
for ENGINE in "${ENGINES[@]}"; do
  DIR="$CACHE_ROOT/$ENGINE"
  if [[ ! -d "$DIR" || -L "$DIR" ]]; then
    echo "$ENGINE: no cache at $DIR"
    continue
  fi
  SIZE="$(du -sh -- "$DIR" | cut -f1)"
  if [[ "$ACTION" == status ]]; then
    echo "$ENGINE: $SIZE in $DIR"
  else
    # Empty the directory but keep it: the launcher mounts it as the engine's /cache.
    find "$DIR" -mindepth 1 -maxdepth 1 -exec rm --preserve-root=all --one-file-system -r -- {} +
    echo "$ENGINE: cleared $SIZE from $DIR"
  fi
done
