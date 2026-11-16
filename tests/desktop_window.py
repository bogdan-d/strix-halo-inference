#!/usr/bin/env python3
"""Real GTK F11 and persisted window-state checks; build with --agent-debug first."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
ROOT=Path(__file__).resolve().parents[1]
SCRATCH=ROOT/'cache/test/window-state'
SCRATCH.mkdir(parents=True,exist_ok=True)
with tempfile.TemporaryDirectory(prefix='profile-',dir=SCRATCH) as directory:
    root=Path(directory)
    (root/'bin').mkdir()
    (root/'bin/run.sh').write_text('#!/bin/sh\nexit 1\n')
    (root/'bin/weights.py').write_text('print("default\\tmissing\\tDefault")\n')
    (root/'bin/podman').write_text('#!/bin/sh\necho "[]"\n')
    (root/'bin/podman').chmod(0o755)
    env=dict(os.environ,INFERENCE_ROOT=str(root),PATH=str(root/'bin')+':'+os.environ['PATH'],CACHE_ROOT=str(root/'cache'))
    env.pop('WEBKIT_INSPECTOR_HTTP_SERVER',None)
    for stage,maximized,fullscreen in [('resize',False,False),('maximize',True,False),('fullscreen',False,True),('maximized-fullscreen',True,True),('unfullscreen',False,False),('normal',False,False)]:
        result=subprocess.run([str(ROOT/'cache/desktop/target/release/inference-desktop')],env=env|{'INFERENCE_WINDOW_CHECK':stage},capture_output=True,text=True,timeout=15)
        (SCRATCH/f'{stage}.log').write_text(result.stdout+result.stderr)
        report=next((json.loads(line.removeprefix('WINDOW_CHECK ')) for line in (result.stdout+result.stderr).splitlines() if line.startswith('WINDOW_CHECK ')),None)
        assert result.returncode==0 and report and report.get('ok'),(stage,result.stdout,result.stderr)
        saved=json.loads((root/'cache/desktop/window-state.json').read_text())
        assert saved=={'width':1000,'height':700,'maximized':maximized,'fullscreen':fullscreen},(stage,saved)
        assert not (root/'cache/desktop/inspector').exists()
        print(stage,saved,flush=True)
