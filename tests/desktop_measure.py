#!/usr/bin/env python3
"""App process-tree PSS and CPU with real charts/logs, a minimize request and hiding. Requires monitoring on, engines off and an agent-debug build; closes only its own app."""
import json
import os
from pathlib import Path
import selectors
import statistics
import subprocess
import time
def process_memory(root_pid: int) -> dict:
    """Sum PSS across the app and all descendants, counting shared mappings proportionally."""
    parents = {}
    for path in Path('/proc').glob('[0-9]*/status'):
        try:
            fields = dict(line.split(':', 1) for line in path.read_text().splitlines())
            parents[int(path.parent.name)] = int(fields['PPid'])
        except (FileNotFoundError, ProcessLookupError):
            continue
    pids = {root_pid}
    while children := {pid for pid, parent in parents.items() if parent in pids} - pids:
        pids.update(children)
    processes = []
    for pid in sorted(pids):
        try:
            path = Path(f'/proc/{pid}')
            fields = dict(line.split(':', 1) for line in (path / 'smaps_rollup').read_text().splitlines()[1:])
            processes.append({'pid': pid, 'name': (path / 'comm').read_text().strip(), 'cpu_ticks': sum(map(int, (path / 'stat').read_text().rsplit(')',1)[1].split()[11:15])),
                              **{key: int(fields[key].split()[0]) for key in ('Pss', 'Rss', 'SwapPss')}})
        except (FileNotFoundError, ProcessLookupError):
            continue  # Short-lived Podman polling helpers may exit during the snapshot.
    if not any(p['pid'] == root_pid for p in processes):
        raise RuntimeError('App exited during memory sampling')
    return {'processes': processes, **{key: sum(p[key] for p in processes) for key in ('Pss', 'Rss', 'SwapPss', 'cpu_ticks')}}



def main():
    root=Path(__file__).resolve().parents[1]
    report={'units':'KiB', 'cpu_percent':'one core = 100%', 'stages':[]}
    with (root/'cache/test/desktop-measure.log').open('w') as log:
        app=subprocess.Popen([str(root/'bin/desktop.sh'),'run','--inspect'],env=dict(os.environ,INFERENCE_WINDOW_CHECK='measure'),stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
        try:
            with selectors.DefaultSelector() as selector:
                selector.register(app.stdout,selectors.EVENT_READ)
                deadline=time.monotonic()+80
                while app.poll() is None and time.monotonic()<deadline:
                    if not selector.select(timeout=1):continue
                    line=app.stdout.readline();log.write(line);log.flush()
                    if not line.startswith('METRIC_STAGE '):continue
                    visibility=json.loads(line.removeprefix('METRIC_STAGE '));label=visibility['name']
                    before=process_memory(app.pid);started=time.monotonic();samples=[]
                    for _ in range(5):
                        time.sleep(1);samples.append(process_memory(app.pid))
                    seconds=time.monotonic()-started
                    cpu=100*(samples[-1]['cpu_ticks']-before['cpu_ticks'])/os.sysconf('SC_CLK_TCK')/seconds
                    stage={**visibility,'pss_median':statistics.median(s['Pss'] for s in samples),'pss_min':min(s['Pss'] for s in samples),'pss_max':max(s['Pss'] for s in samples),'cpu_percent':round(cpu,2),'samples':samples}
                    report['stages'].append(stage)
                    print(json.dumps({k:v for k,v in stage.items() if k!='samples'}),flush=True)
            app.wait(timeout=5)
            assert app.returncode==0 and len(report['stages'])==4,report
        finally:
            if app.poll() is None:app.terminate();app.wait(timeout=5)
            (root/'cache/test/desktop-memory.json').write_text(json.dumps(report,indent=2)+'\n')
if __name__=='__main__':main()
