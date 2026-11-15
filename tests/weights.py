#!/usr/bin/env python3
"""Exercise profile manifests with tiny files, including pinned downloads and corrupt local weights."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    for name in ('bin', 'config', 'models', 'commands'):
        (root / name).mkdir()
    for name in ('models.sh', 'weights.py'):
        shutil.copy(ROOT / 'bin' / name, root / 'bin' / name)
    shutil.copy(ROOT / 'config/pins.env', root / 'config/pins.env')
    entry = {'label': 'Fixture', 'model': 'trial/weights.gguf', 'mtp': 'trial/mtp.gguf', 'manifest': 'trial.tsv'}
    (root / 'config/weights.json').write_text(json.dumps({'gufo': {'trial': entry}}))
    digest = hashlib.sha256(b'weights').hexdigest()
    (root / 'config/trial.tsv').write_text(f'{digest}\t7\ttrial/weights.gguf\tpublisher/repo\t' + 'a'*40 + '\tquant/source.gguf\n')
    curl = root / 'commands/curl'
    curl.write_text('''#!/usr/bin/env python3
import sys
from pathlib import Path
assert sys.argv[-1] == 'https://huggingface.co/publisher/repo/resolve/' + 'a'*40 + '/quant/source.gguf', sys.argv
Path(sys.argv[sys.argv.index('--output') + 1]).write_bytes(b'weights')
''')
    curl.chmod(0o755)
    env = dict(os.environ, MODELS_DIR=str(root / 'models'), PATH=f"{root / 'commands'}:{os.environ['PATH']}")
    def run(action):
        return subprocess.run([str(root / 'bin/models.sh'), action, 'gufo', 'trial'], env=env, capture_output=True, text=True)
    assert run('check').returncode != 0
    result = run('download')
    assert result.returncode == 0, result
    assert run('verify').returncode == 0
    target = root / 'models/trial/weights.gguf'
    target.write_bytes(b'corrupt')
    result = run('download')
    assert result.returncode != 0 and 'SHA-256 mismatch' in result.stderr and target.read_bytes() == b'corrupt', result
    target.unlink()
    (root / 'config/trial.tsv').write_text(f'{digest}\t7\ttrial/weights.gguf\n')
    result = run('download')
    assert result.returncode != 0 and 'Local weight missing' in result.stderr, result
    (root / 'config/trial.tsv').write_text(f'{digest}\t7\t../outside.gguf\n')
    result = run('download')
    assert result.returncode == 2 and 'Invalid manifest row' in result.stderr, result
print('Profile manifest download, verification and preservation checks passed.')
