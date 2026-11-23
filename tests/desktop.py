#!/usr/bin/env python3
"""Exercise real native IPC against fixed script fixtures, without running engines."""
import json
import os
from pathlib import Path
import socket
import subprocess
import tempfile
import time
import browser

ROOT = Path(__file__).resolve().parents[1]
SCRATCH = ROOT / 'cache/test'
SCRATCH.mkdir(parents=True, exist_ok=True)


def wait_for(test, seconds=10):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        result = test()
        if result:
            return result
        time.sleep(.1)
    raise AssertionError('Condition timed out')


def main():
    with tempfile.TemporaryDirectory(prefix='desktop-fixture-', dir=SCRATCH) as directory:
        root = Path(directory)
        (root/'bin').mkdir()
        (root/'commands').mkdir()
        (root/'cache/desktop').mkdir(parents=True)
        (root/'containers.json').write_text('[]')
        (root/'bin/weights.py').write_text("""import json, sys
engine, action = sys.argv[1:]
assert action == 'dashboard'
print(json.dumps([{'id': 'default', 'available': True, 'label': 'Fixture', 'vision_available': engine != 'gufo',
                   'vision_download': f'bin/models.sh download {engine} default --projector'}]))
""")
        (root/'commands/podman').write_text('#!/usr/bin/env python3\nfrom pathlib import Path\nprint(Path("containers.json").read_text())\n')
        (root/'commands/curl').write_text('#!/bin/sh\nexit 0\n')
        stub = '''#!/usr/bin/env python3
import json,os,sys,time
from pathlib import Path
a=sys.argv[1:]
if a[-1]=='--follow':
    Path('viewer.pid').write_text(str(os.getpid()))
    while True:
        print('fixture log ñ',flush=True);time.sleep(.1)
assert not any(n in os.environ for n in ('WEIGHTS','GUFO_MODEL'))
Path('action.json').write_text(json.dumps({'argv':a,'npu':os.environ.get('NPU_MODELS'),'vision':os.environ.get('VISION')}))
time.sleep(2)
print('fixture refused');sys.exit(1)
'''
        for name in ('run.sh','cache.sh','monitor.sh'):
            # Native backend invokes bash, as the real launchers are Bash scripts.
            (root/'bin'/name).write_text('#!/bin/bash\nexec python3 "'+str(root/'action.py')+'" "$@"\n')
        (root/'action.py').write_text(stub)
        for name in ('podman','curl'):
            (root/'commands'/name).chmod(0o755)
        with socket.socket() as reservation:
            reservation.bind(('127.0.0.1',0)); port=reservation.getsockname()[1]
        address=f'127.0.0.1:{port}'
        env=dict(os.environ,INFERENCE_ROOT=str(root),WEBKIT_INSPECTOR_HTTP_SERVER=address,
                 PATH=str(root/'commands')+':'+os.environ['PATH'],CACHE_ROOT=str(root/'cache'),
                 WEIGHTS='wrong',GUFO_MODEL='wrong',NPU_MODELS='wrong',VISION='wrong',DASHBOARD_NPU_MODELS='decider-0.8b')
        os.environ['INFERENCE_INSPECTOR']=address
        with (SCRATCH/'desktop-fixture.log').open('w') as log:
            app=subprocess.Popen([str(ROOT/'cache/desktop/target/release/inference-desktop')],env=env,stdout=log,stderr=log)
            try:
                wait_for(lambda:(root/'cache/desktop/inspector').exists())
                time.sleep(.7)
                view=browser.view('@main')
                wait_for(lambda:view.evaluate('!!state'))
                assert view.evaluate('state.engines.halogen.state')=='stopped'
                assert view.evaluate('document.querySelector("#metrics b").textContent')!='—'
                assert subprocess.run([str(ROOT/'cache/desktop/target/release/inference-desktop')],env=env,capture_output=True,timeout=5).returncode==0
                # Real command validation refuses injection before a helper can run.
                for action in ({'kind':'start','engine':'other','profile':'default','npu':False},
                               {'kind':'start','engine':'halogen','profile':'../bad','npu':False},
                               {'kind':'start','engine':'gufo','profile':'default','npu':True},
                               {'kind':'start','engine':'gufo','profile':'default','npu':False,'vision':True},
                               {'kind':'start','engine':'halogen','profile':'default','npu':False,'vision':'invalid'}):
                    assert view.evaluate(f'window.__TAURI__.core.invoke("dashboard_action",{{action:{json.dumps(action)}}}).then(()=>false,()=>true)')
                assert not (root/'action.json').exists()
                assert view.evaluate('document.querySelector("#vision-strixite").checked')
                assert view.evaluate('document.querySelector("#vision-gufo").disabled && !document.querySelector("#vision-gufo").checked')
                assert view.evaluate('!document.querySelector("#vision-hint-gufo").hidden && document.querySelector("#vision-hint-gufo").textContent.includes("download gufo default --projector")')
                assert view.evaluate('!document.querySelector(".engine-start[data-id=gufo]").disabled')
                view.evaluate('document.querySelector(".engine-start[data-id=gufo]").click();true')
                wait_for(lambda:view.evaluate('document.querySelector("#notice").textContent.includes("fixture refused")'))
                assert json.loads((root/'action.json').read_text())=={'argv':['gufo','start','--weights','default'],'npu':None,'vision':'off'}
                (root/'action.json').unlink()
                assert view.evaluate('!document.querySelector("#vision-halogen").checked')
                view.evaluate('document.querySelector("#vision-halogen").click();document.querySelector("#npu").click();true')
                wait_for(lambda:(root/'action.json').exists())
                view.evaluate('window.__TAURI__.window.getCurrentWindow().close(); true')
                time.sleep(.2)
                assert app.poll() is None, 'close interrupted a lifecycle operation'
                wait_for(lambda:view.evaluate('document.querySelector("#notice").textContent.includes("fixture refused")'))
                assert json.loads((root/'action.json').read_text())=={'argv':['halogen','start','--weights','default'],'npu':'decider-0.8b','vision':'on'}
                view.evaluate('tail("halogen");true')
                wait_for(lambda:view.evaluate('document.querySelector("#log").textContent.includes("fixture log ñ")'))
                pid=int((root/'viewer.pid').read_text())
                view.evaluate('closeLogs();true')
                wait_for(lambda:not Path(f'/proc/{pid}').exists())
                view.evaluate('tail("prometheus");true')
                wait_for(lambda:int((root/'viewer.pid').read_text())!=pid)
                pid=int((root/'viewer.pid').read_text())
                view.call('Page.reload',{'ignoreCache':True})
                wait_for(lambda:not Path(f'/proc/{pid}').exists())
                wait_for(lambda:view.evaluate('!!window.inferenceTransport'))
                view.evaluate('document.querySelector("#metrics").click();true')
                assert view.evaluate('localStorage.getItem("metrics-view")')=='graphs'
                view.evaluate('tail("halogen");true')
                wait_for(lambda:int((root/'viewer.pid').read_text())!=pid)
                pid=int((root/'viewer.pid').read_text())
                browser.close_view(view)
                app.wait(timeout=5)
                wait_for(lambda:not Path(f'/proc/{pid}').exists())
                saved=json.loads((root/'cache/desktop/window-state.json').read_text())
                assert saved['width']==1200 and saved['height']==800,saved
                assert app.returncode==0
                print('Native IPC policy, environment, refused actions, busy-close guard, logs/reload cleanup, single-instance and state-save checks passed.')
            finally:
                if app.poll() is None:
                    app.terminate();app.wait(timeout=5)

if __name__=='__main__':
    main()
