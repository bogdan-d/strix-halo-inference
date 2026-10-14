#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=../config/pins.env
source "$ROOT/config/pins.env"
# Halogen checks every NPU file against the record in its image and refuses others, so the manifest is derived
# from the pinned image rather than written by hand. Rerun after a Halogen pin change and review the diff.
# Without arguments, the models already in the manifest are kept.
MANIFEST="$ROOT/config/npu-files.tsv"
RECORD="$(podman run --rm --pull=never --network none --entrypoint cat "$HALOGEN_IMAGE" /opt/halogen/npu/models.txt)"
exec python - "$MANIFEST" "$RECORD" "$@" <<'PY'
import re
import sys
from pathlib import Path

manifest, record, wanted = Path(sys.argv[1]), sys.argv[2], sys.argv[3:]
if not wanted:
    if not manifest.exists():
        sys.exit("Name the NPU models to record, for example: bin/npu-manifest.sh decider-0.8b embeddinggemma-2")
    # A selected model lists its own weight file; a devices-only dependency does not.
    paths = [line.split("\t")[2] for line in manifest.read_text().splitlines()]
    wanted = sorted(path.split("/")[0] for path in paths if path == f"{path.split('/')[0]}/{path.split('/')[0]}.hnpw")
models, files = {}, {}
for line in record.splitlines():
    fields = line.split()
    if fields[:1] == ["model"]:
        models[fields[1]] = dict(field.split("=", 1) for field in fields[2:])
    elif fields[:1] == ["file"]:
        files.setdefault(fields[1], []).append(fields[2:5])
rows = set()
for model in wanted:
    if model not in models:
        sys.exit(f"The pinned Halogen image has no NPU model {model}. Known: {', '.join(sorted(models))}")
    # A model naming devices=<other> runs on that model's devices/ files, as Halogen fetches them.
    needed = [(model, lambda path: True)]
    if models[model].get("devices", model) != model:
        needed.append((models[model]["devices"], lambda path: path.startswith("devices/")))
    for owner, keep in needed:
        for path, size, sha in files[owner]:
            if not re.fullmatch(r"[0-9a-f]{64}", sha) or not size.isdigit() or ".." in path.split("/"):
                sys.exit(f"Unexpected record line for {owner}: {path}")
            if keep(path):
                rows.add((sha, size, f"{owner}/{path}", models[owner]["repo"], models[owner]["revision"]))
manifest.write_text("".join("\t".join(row) + "\n" for row in sorted(rows, key=lambda row: row[2])))
print(f"Wrote {len(rows)} files for {', '.join(sorted(wanted))} to {manifest}")
PY
