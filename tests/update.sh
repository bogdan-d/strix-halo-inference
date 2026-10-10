#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
TEMP="$(mktemp -d)"
trap 'rm --preserve-root=all --one-file-system -r -- "$TEMP"' EXIT
mkdir -p -- "$TEMP/bin" "$TEMP/config" "$TEMP/commands" "$TEMP/cache/halogen" "$TEMP/cache/gufo"
cp -- "$ROOT/bin/update.sh" "$TEMP/bin/update.sh"
cp -- "$ROOT/config/pins.env" "$TEMP/config/pins.env"
cp -- "$ROOT/config/pins.env" "$TEMP/expected.env"
export FIXTURE_ROOT="$TEMP" CACHE_ROOT="$TEMP/cache"
export PATH="$TEMP/commands:$PATH"

# CLI stubs exercise our transaction policy, not registry or GitHub compatibility.
# Metadata fields and changelog headings were checked against the real endpoints.
cat > "$TEMP/commands/skopeo" <<'PY'
#!/usr/bin/env python
import json,os,re,sys
from pathlib import Path
pins=dict(re.findall(r'^([A-Z_]+)=(\S+)$', (Path(os.environ['FIXTURE_ROOT'])/'expected.env').read_text(), re.M))
prefix='GUFO' if 'gufo-runtime' in sys.argv[-1] else 'HALOGEN'
name,digest=pins[prefix+'_IMAGE'].split('@')
print(json.dumps({'Name':name,'Digest':digest,'Architecture':'amd64','Os':'linux',
                  'Labels':{'org.opencontainers.image.version':pins[prefix+'_VERSION']}}))
PY
cat > "$TEMP/commands/curl" <<'PY'
#!/usr/bin/env python
import json,os,re,sys
from pathlib import Path
pins=dict(re.findall(r'^([A-Z_]+)=(\S+)$', (Path(os.environ['FIXTURE_ROOT'])/'expected.env').read_text(), re.M))
url=sys.argv[-1]
if 'raw.githubusercontent.com' in url:
    print('# Changelog\n\n## '+pins['HALOGEN_VERSION']+'\n\nSelected changelog.\n\n## 0.0.1\n\nOlder changelog.\n\n200',end='')
elif 'peonist-ai' in url:
    print('{}\n404',end='')
else:
    print(json.dumps({'tag_name':'v'+pins['GUFO_VERSION'],'draft':False,'prerelease':False,
                      'body':'### Performance\n\n* **qwen-flash:** faster decode kernels'})+'\n200',end='')
PY
cat > "$TEMP/commands/podman" <<'PY'
#!/usr/bin/env python
import os,sys
from pathlib import Path
if sys.argv[1]=='info':
    print('true')
elif sys.argv[1]=='ps':
    print(os.environ.get('ACTIVE',''))
elif sys.argv[1]=='pull':
    with (Path(os.environ['FIXTURE_ROOT'])/'pulls').open('a') as file:
        file.write(sys.argv[-1]+'\n')
    if os.environ.get('FAIL_PULL')=='1' and 'gufo-runtime' in sys.argv[-1]:
        sys.exit(7)
else:
    sys.exit(2)
PY
chmod +x "$TEMP/commands/"{skopeo,curl,podman}

"$TEMP/bin/update.sh" --check > "$TEMP/output"
cmp -- "$TEMP/config/pins.env" "$TEMP/expected.env"
[[ ! -e "$TEMP/config/.update.lock" && ! -e "$TEMP/pulls" ]]
grep -q 'Selected changelog' "$TEMP/output"
if grep -q 'Older changelog' "$TEMP/output"; then
  echo 'Printed changes for the wrong release' >&2; exit 1
fi

# Make the image pins older than the verified fixture to exercise a real pin transition.
python - "$TEMP/config/pins.env" <<'PY'
import re,sys
from pathlib import Path
p=Path(sys.argv[1])
p.write_text(re.sub(r'@sha256:[0-9a-f]{64}', '@sha256:'+'0'*64, p.read_text()))
PY
cp -- "$TEMP/config/pins.env" "$TEMP/before.env"
if FAIL_PULL=1 "$TEMP/bin/update.sh" > "$TEMP/output" 2>&1; then
  echo 'Failed pull was accepted' >&2; exit 1
fi
cmp -- "$TEMP/config/pins.env" "$TEMP/before.env"

printf 'preserve me\n' > "$TEMP/cache/halogen/marker"
if ACTIVE=strix-halo-halogen "$TEMP/bin/update.sh" --fresh-cache > "$TEMP/output" 2>&1; then
  echo 'Active engine allowed cache rotation' >&2; exit 1
fi
grep -q 'Stop the active engine' "$TEMP/output"
cmp -- "$TEMP/config/pins.env" "$TEMP/before.env"
[[ -f "$TEMP/cache/halogen/marker" ]]

"$TEMP/bin/update.sh" --fresh-cache > "$TEMP/output"
cmp -- "$TEMP/config/pins.env" "$TEMP/expected.env"
[[ ! -e "$TEMP/cache/halogen" && ! -e "$TEMP/cache/gufo" ]]
[[ "$(find "$TEMP/cache" -path '*/halogen/marker' -type f | wc -l)" == 1 ]]
grep -q 'Running containers are unchanged' "$TEMP/output"

python - "$TEMP/config/pins.env" <<'PY'
import re,sys
from pathlib import Path
p=Path(sys.argv[1])
p.write_text(re.sub(r'^GUFO_VERSION=.*$', 'GUFO_VERSION=999.0.0', p.read_text(), flags=re.M))
PY
cp -- "$TEMP/config/pins.env" "$TEMP/before.env"
if "$TEMP/bin/update.sh" > "$TEMP/output" 2>&1; then
  echo 'Version downgrade was accepted' >&2; exit 1
fi
grep -q 'Refusing gufo downgrade' "$TEMP/output"
cmp -- "$TEMP/config/pins.env" "$TEMP/before.env"
echo 'Update transaction, release selection, cache guard and downgrade checks passed.'
