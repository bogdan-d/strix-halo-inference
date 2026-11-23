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
    entry = {'label': 'Fixture', 'model': 'trial/weights.gguf', 'mtp': 'trial/mtp.gguf', 'manifest': 'trial.tsv', 'projector_manifest': 'projector.tsv'}
    (root / 'config/weights.json').write_text(json.dumps({'gufo': {'trial': entry}}))
    digest = hashlib.sha256(b'weights').hexdigest()
    (root / 'config/trial.tsv').write_text(f'{digest}\t7\ttrial/weights.gguf\tpublisher/repo\t' + 'a'*40 + '\tquant/source.gguf\n')
    (root / 'config/projector.tsv').write_text(f'{digest}\t7\ttrial/vision/mmproj-BF16.gguf\tpublisher/repo\t' + 'a'*40 + '\tquant/source.gguf\n')
    curl = root / 'commands/curl'
    curl.write_text('''#!/usr/bin/env python3
import sys
from pathlib import Path
assert sys.argv[-1] == 'https://huggingface.co/publisher/repo/resolve/' + 'a'*40 + '/quant/source.gguf', sys.argv
Path(sys.argv[sys.argv.index('--output') + 1]).write_bytes(b'weights')
''')
    curl.chmod(0o755)
    env = dict(os.environ, MODELS_DIR=str(root / 'models'), PATH=f"{root / 'commands'}:{os.environ['PATH']}")
    def run(action, *options):
        return subprocess.run([str(root / 'bin/models.sh'), action, 'gufo', 'trial', *options], env=env, capture_output=True, text=True)
    assert run('check').returncode != 0
    result = run('download')
    assert result.returncode == 0, result
    assert run('verify').returncode == 0
    projector = root / 'models/trial/vision/mmproj-BF16.gguf'
    assert not projector.exists()
    missing = run('check', '--projector')
    assert missing.returncode != 0 and 'download gufo trial --projector' in missing.stderr, missing
    assert run('download', '--projector').returncode == 0 and projector.read_bytes() == b'weights'
    assert run('verify', '--projector').returncode == 0
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
    # Installed profiles need only their text files. Use sparse stand-ins at the real manifest paths.
    catalog = json.loads((ROOT / 'config/weights.json').read_text())
    for engine in ('halogen', 'strixite'):
        for name, profile in catalog[engine].items():
            for row in (ROOT / 'config' / profile['manifest']).read_text().splitlines():
                _, size, filename, *_ = row.split('\t')
                target = root / 'models' / profile['directory'] / filename
                target.parent.mkdir(parents=True, exist_ok=True)
                with target.open('ab') as output:
                    output.truncate(int(size))
            args = [str(ROOT / 'bin/models.sh'), 'check', engine, name]
            subprocess.run(args, env=env, check=True, capture_output=True)
            missing = subprocess.run([*args, '--projector'], env=env, capture_output=True, text=True)
            assert missing.returncode and 'Missing' in missing.stderr, missing
        listing = subprocess.check_output([str(ROOT / 'bin/run.sh'), engine, 'weights'], env=env, text=True)
        assert all(row.split('\t')[1] == 'installed' for row in listing.splitlines()), listing
        # Discover newly installed projector files without a restart. Every row must match.
        manifest = ROOT / 'config' / catalog[engine]['default']['projector_manifest']

        def selected():
            data = subprocess.check_output(['python3', str(ROOT / 'bin/weights.py'), engine, 'dashboard'], env=env)
            return next(row for row in json.loads(data) if row['id'] == 'default')

        assert selected()['available'] and not selected()['vision_available']
        for row in manifest.read_text().splitlines():
            _, size, filename, *_ = row.split('\t')
            target = root / 'models' / filename
            target.parent.mkdir(parents=True, exist_ok=True)
            assert not selected()['vision_available']
            with target.open('wb') as output:
                output.truncate(int(size))
        assert selected()['vision_available']
        with target.open('ab') as output:
            output.write(b'x')
        assert not selected()['vision_available']
print('Profile manifest download, verification and preservation checks passed.')
