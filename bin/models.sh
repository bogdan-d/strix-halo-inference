#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=../config/pins.env
source "$ROOT/config/pins.env"

[[ $# -ge 2 && $# -le 3 ]] || { echo "Usage: bin/models.sh download|verify|check ENGINE [PROFILE]" >&2; exit 2; }
PROFILE="${3:-default}"
ACTION="${1:-}"
ENGINE="${2:-}"
case "$ACTION" in download|verify|check) ;; *) echo 'Usage: bin/models.sh download|verify|check halogen|gufo|strixite|npu' >&2; exit 2 ;; esac
case "$ENGINE" in
  halogen) REPO="$HALOGEN_REPO"; REVISION="$HALOGEN_REVISION" ;;
  gufo) REPO="$GUFO_REPO"; REVISION="$GUFO_REVISION" ;;
  strixite) REPO="$STRIXITE_REPO"; REVISION="$STRIXITE_REVISION" ;;
  # NPU files come from one repository per model, named on each manifest line.
  npu) REPO=npu; REVISION= ;;
  *) echo 'Choose halogen, gufo, strixite or npu.' >&2; exit 2 ;;
esac
MODELS_DIR="${MODELS_DIR:-/home/bogdan/models}"
MANIFEST="$ROOT/config/$ENGINE-files.tsv"
DEST="$MODELS_DIR/$REPO"
if [[ "$ENGINE" != npu ]]; then
  SELECTION="$(python "$ROOT/bin/weights.py" "$ENGINE" manifest "$PROFILE")"
  mapfile -t FIELDS <<<"$SELECTION"
  DEST="$MODELS_DIR/${FIELDS[0]}"
  MANIFEST="$ROOT/config/${FIELDS[1]}"
  [[ "$PROFILE" == default ]] || REVISION=
else
  [[ "$PROFILE" == default ]] || { echo 'NPU has no weight profiles.' >&2; exit 2; }
fi
[[ -s "$MANIFEST" ]] || { echo "Missing or empty manifest: $MANIFEST. Provision this profile first." >&2; exit 1; }
# Optional Hugging Face token for gated repositories and higher rate limits: HF_TOKEN from the environment, else from the ignored .env.
if [[ "$ACTION" == download && -z "${HF_TOKEN:-}" && -f "$ROOT/.env" ]]; then
  HF_TOKEN="$(sed -n -E "s/^HF_TOKEN=[\"']?([^\"'[:space:]]*)[\"']?[[:space:]]*$/\1/p" "$ROOT/.env" | tail -n 1)"
fi
# The header is read from a file descriptor so the token stays out of the process list. curl sends a custom
# Authorization header only to the original host, not to the CDN that Hugging Face redirects file downloads to.
hf_curl() {
  if [[ -n "${HF_TOKEN:-}" ]]; then
    curl --header @<(printf 'Authorization: Bearer %s\n' "$HF_TOKEN") "$@"
  else
    curl "$@"
  fi
}
if [[ "$ACTION" == download ]]; then
  mkdir -p -- "$DEST"
  exec 9>"$DEST/.download.lock"
  flock -n 9 || { echo "Another download holds $DEST/.download.lock" >&2; exit 1; }
fi
while IFS=$'\t' read -r HASH SIZE FILE FILE_REPO FILE_REVISION SOURCE_FILE; do
  [[ "$HASH" =~ ^[0-9a-f]{64}$ && "$SIZE" =~ ^[1-9][0-9]*$ && -n "$FILE" && "$FILE" != /* && "/$FILE/" != *"/../"* ]] \
    || { echo "Invalid manifest row in $MANIFEST: $FILE" >&2; exit 2; }
  TARGET="$DEST/$FILE"
  SOURCE="$REPO/resolve/$REVISION/$FILE"
  # NPU paths start with the model id, which is not part of the path in its repository.
  if [[ -n "${FILE_REPO:-}" ]]; then
    SOURCE="$FILE_REPO/resolve/$FILE_REVISION/${SOURCE_FILE:-${FILE#*/}}"
  fi
  VERIFIED=0
  if [[ "$ACTION" == download && ! -f "$TARGET" ]]; then
    [[ -n "$REVISION" || -n "${FILE_REVISION:-}" ]] || { echo "Local weight missing: $TARGET. Provision this profile first." >&2; exit 1; }
    mkdir -p -- "$(dirname -- "$TARGET")"
    echo "Downloading $SOURCE"
    hf_curl --fail --location --retry 5 --connect-timeout 30 --speed-limit 1024 --speed-time 120 \
      --continue-at - --output "$TARGET.partial" \
      "https://huggingface.co/$SOURCE"
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
done < "$MANIFEST"
echo "$ENGINE: $ACTION complete ($DEST)"
