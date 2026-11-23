#!/usr/bin/env python3
"""Collector gate and decoding contract, without opening the real device."""
from pathlib import Path
import io
import sys
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'bin'))
import npu_metrics as npu

for health in (b'{}', b'{"npu":null}', b'{"npu":false}'):
    with patch.object(npu.DIRECT, 'open', return_value=io.BytesIO(health)), patch.object(npu, 'sensors') as sensor:
        assert npu.npu_metrics() is None
        sensor.assert_not_called()
health = b'{"npu":{"models":["decider-0.8b","bad\\\"label"],"loaded":["decider-0.8b"],"queued":2}}'
with patch.object(npu.DIRECT, 'open', return_value=io.BytesIO(health)), patch.object(npu, 'sensors', return_value=[(0, 3.5), (1, 20), (1, 40)]):
    result = npu.npu_metrics()
    assert 'npu_busy_percent 30' in result and 'npu_power_watts 3.5' in result
    assert 'npu_model_loaded{model="decider-0.8b"} 1' in result and 'bad' not in result
    assert 'npu_queued 2' in result
# Decode actual packed sensor records through the ioctl buffer contract.
def ioctl(fd, command, request):
    import ctypes, struct
    _, size, address = struct.unpack('IIQ', request)
    record = npu.SENSOR.pack(b'power', 3500, 0, 0, 0, b'', b'W', -3, 0)
    ctypes.memmove(address, record, len(record))
    request[:] = struct.pack('IIQ', npu.QUERY_SENSORS, len(record), address)
with patch.object(npu.os, 'open', return_value=42), patch.object(npu.os, 'close'), patch.object(npu.fcntl, 'ioctl', side_effect=ioctl):
    assert npu.sensors() == [(0, 3.5)]
print('NPU gating, label and packed-sensor decoding checks passed.')

# Lifecycle uses a separate endpoint and fixture collector, never the real device or monitoring process.
import json
import os
import socket
import subprocess
import tempfile
import urllib.error
import urllib.request
root = Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix='npu-exporter-', dir=root/'cache/test') as directory:
    fixture = Path(directory)
    (fixture/'bin').mkdir()
    with socket.socket() as reservation:
        reservation.bind(('127.0.0.1',0)); port = reservation.getsockname()[1]
    script = fixture/'bin/npu-exporter.py'
    script.write_text((root/'bin/npu-exporter.py').read_text().replace('PORT = 9098',f'PORT = {port}'))
    (fixture/'bin/npu_metrics.py').write_text('def npu_metrics(): return None\n')
    def run(action):
        return subprocess.run([sys.executable,str(script),action],capture_output=True,text=True,timeout=8)
    try:
        assert run('start').returncode == 0
        record = (fixture/'cache/monitoring/npu.json').read_text()
        assert run('start').returncode == 0 and (fixture/'cache/monitoring/npu.json').read_text() == record
        try:
            urllib.request.urlopen(f'http://127.0.0.1:{port}/metrics',timeout=2)
            raise AssertionError('idle NPU must refuse scrape')
        except urllib.error.HTTPError as error:
            assert error.code == 503
        assert run('stop').returncode == 0 and run('stop').returncode == 0
        with socket.socket() as foreign:
            # The stopped HTTP server may still have a connection in TIME_WAIT.
            foreign.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            foreign.bind(('127.0.0.1',port));foreign.listen()
            assert run('start').returncode != 0
        # A fabricated record for an unrelated live PID must never authorize killing it.
        with subprocess.Popen(['sleep','10']) as unrelated:
            pid=unrelated.pid
            start=Path(f'/proc/{pid}/stat').read_text().rsplit(')',1)[1].split()[19]
            (fixture/'cache/monitoring/npu.json').write_text(json.dumps({'pid':pid,'start':start}))
            assert run('stop').returncode == 0 and unrelated.poll() is None
            unrelated.terminate();unrelated.wait(timeout=2)
        assert run('start').returncode == 0 and run('status').returncode == 0
    finally:
        assert run('stop').returncode == 0
print('NPU collector repeated start/stop, occupied port and unrelated-PID safety checks passed.')
