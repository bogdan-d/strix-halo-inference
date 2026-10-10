#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=../config/pins.env
source "$ROOT/config/pins.env"

ACTION="${1:-}"
ENGINE="${2:-}"
case "$ACTION" in download|verify|check) ;; *) echo 'Usage: bin/models.sh download|verify|check halogen|gufo' >&2; exit 2 ;; esac
case "$ENGINE" in
  halogen) REPO="$HALOGEN_REPO"; REVISION="$HALOGEN_REVISION" ;;
  gufo) REPO="$GUFO_REPO"; REVISION="$GUFO_REVISION" ;;
  *) echo 'Choose halogen or gufo.' >&2; exit 2 ;;
esac
MODELS_DIR="${MODELS_DIR:-/home/bogdan/models}"
DEST="$MODELS_DIR/$REPO"
if [[ "$ACTION" == download ]]; then
  mkdir -p -- "$DEST"
  exec 9>"$DEST/.download.lock"
  flock -n 9 || { echo "Another download holds $DEST/.download.lock" >&2; exit 1; }
fi
while IFS=$'\t' read -r HASH SIZE FILE; do
  TARGET="$DEST/$FILE"
  VERIFIED=0
  if [[ "$ACTION" == download && ! -f "$TARGET" ]]; then
    mkdir -p -- "$(dirname -- "$TARGET")"
    echo "Downloading $REPO/$FILE at $REVISION"
    curl --fail --location --retry 5 --connect-timeout 30 --speed-limit 1024 --speed-time 120 \
      --continue-at - --output "$TARGET.partial" \
      "https://huggingface.co/$REPO/resolve/$REVISION/$FILE"
    [[ "$(stat -c %s -- "$TARGET.partial")" == "$SIZE" ]] || { echo "Wrong download size: $FILE" >&2; exit 1; }
    printf '%s  %s\n' "$HASH" "$TARGET.partial" | sha256sum --check --status || { echo "SHA-256 mismatch: $FILE. Partial file preserved." >&2; exit 1; }
    mv -n -- "$TARGET.partial" "$TARGET"
    [[ ! -e "$TARGET.partial" ]] || { echo "Destination appeared during download: $TARGET. Files left untouched." >&2; exit 1; }
    VERIFIED=1
  fi
  [[ -f "$TARGET" ]] || { echo "Missing $TARGET. Run bin/models.sh download $ENGINE" >&2; exit 1; }
  [[ "$(stat -c %s -- "$TARGET")" == "$SIZE" ]] || { echo "Wrong size: $TARGET. Existing file left untouched." >&2; exit 1; }
  if [[ "$ACTION" != check ]]; then
    if [[ "$VERIFIED" == 0 ]]; then
      printf '%s  %s\n' "$HASH" "$TARGET" | sha256sum --check --status || { echo "SHA-256 mismatch: $TARGET. Existing file left untouched." >&2; exit 1; }
    fi
    echo "Verified $FILE"
  fi
done < "$ROOT/config/$ENGINE-files.tsv"
echo "$ENGINE: $ACTION complete ($DEST)"
