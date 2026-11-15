#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
TEMP="$(mktemp -d)"
trap 'rm --preserve-root=all --one-file-system -r -- "$TEMP"' EXIT
export MODELS_DIR="$TEMP/models"
# This test is offline: any download attempt fails it instead of fetching weights.
mkdir -- "$TEMP/bin"
printf '#!/bin/sh\necho "Offline test tried to download: $*" >&2\nexit 97\n' > "$TEMP/bin/curl"
chmod +x -- "$TEMP/bin/curl"
export PATH="$TEMP/bin:$PATH"

# A size-correct corrupt existing file must be rejected, never overwritten. It is the manifest's first entry,
# so no earlier missing file is downloaded before it is checked. truncate makes it sparse, whatever its size.
for ENGINE in gufo strixite; do
  if [[ "$ENGINE" == gufo ]]; then REPO=unsloth/Qwen3.8-Flash-Next-GGUF; else REPO=wemoh/Qwen3.8-Flash-Next-strixw; fi
  IFS=$'\t' read -r _HASH SIZE FILE < "$ROOT/config/$ENGINE-files.tsv"
  TARGET="$MODELS_DIR/$REPO/$FILE"
  mkdir -p -- "$(dirname -- "$TARGET")"
  truncate -s "$SIZE" -- "$TARGET"
  BEFORE="$(sha256sum -- "$TARGET")"
  if "$ROOT/bin/models.sh" download "$ENGINE" > "$TEMP/output" 2>&1; then
    echo 'Corrupt model file was accepted' >&2
    exit 1
  fi
  grep -q 'SHA-256 mismatch' "$TEMP/output"
  [[ "$BEFORE" == "$(sha256sum -- "$TARGET")" ]]
done

# A missing shard must fail the launcher's fast size check without network I/O.
for ENGINE in halogen strixite; do
  if "$ROOT/bin/models.sh" check "$ENGINE" > "$TEMP/output" 2>&1; then
    echo 'Missing model was accepted' >&2
    exit 1
  fi
  grep -q 'Missing' "$TEMP/output"
done
echo 'Model integrity refusal and missing-file checks passed.'
