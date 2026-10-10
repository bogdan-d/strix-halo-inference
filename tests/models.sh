#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
TEMP="$(mktemp -d)"
trap 'rm --preserve-root=all --one-file-system -r -- "$TEMP"' EXIT
export MODELS_DIR="$TEMP"

# A size-correct corrupt existing shard must be rejected, never overwritten.
IFS=$'\t' read -r _HASH SIZE FILE < <(awk -F '\t' '$2 < 20000000 {print; exit}' "$ROOT/config/gufo-files.tsv")
TARGET="$MODELS_DIR/unsloth/Qwen3.8-Flash-Next-GGUF/$FILE"
mkdir -p -- "$(dirname -- "$TARGET")"
truncate -s "$SIZE" -- "$TARGET"
BEFORE="$(sha256sum -- "$TARGET")"
if "$ROOT/bin/models.sh" download gufo > "$TEMP/output" 2>&1; then
  echo 'Corrupt shard was accepted' >&2
  exit 1
fi
grep -q 'SHA-256 mismatch' "$TEMP/output"
[[ "$BEFORE" == "$(sha256sum -- "$TARGET")" ]]

# A missing shard must fail the launcher's fast size check without network I/O.
if "$ROOT/bin/models.sh" check halogen > "$TEMP/output" 2>&1; then
  echo 'Missing model was accepted' >&2
  exit 1
fi
grep -q 'Missing' "$TEMP/output"
echo 'Model integrity refusal and missing-file checks passed.'
