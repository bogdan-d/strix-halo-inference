#!/usr/bin/env python3
"""Monitoring-owned NPU endpoint, with a locked lifecycle and PID-reuse-safe shutdown."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import fcntl
import json
import os
from pathlib import Path
import select
import signal
import subprocess
import sys
import time
from npu_metrics import npu_metrics

ROOT = Path(__file__).resolve().parents[1]
STORE = ROOT / 'cache/monitoring'
RECORD = STORE / 'npu.json'
PORT = 9098


def identity(pid):
    return Path(f'/proc/{pid}/stat').read_text().rsplit(')', 1)[1].split()[19]


def owned():
    """Hold a pidfd before checking identity; never signal a recycled PID."""
    try:
        record = json.loads(RECORD.read_text())
        fd = os.pidfd_open(record['pid'])
    except (OSError, ValueError, KeyError):
        return None
    try:
        if identity(record['pid']) == record['start'] and str(Path(__file__).resolve()).encode() in Path(f"/proc/{record['pid']}/cmdline").read_bytes().split(b'\0'):
            return fd
    except OSError:
        pass
    os.close(fd)
    return None


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.headers.get('Host') not in (f'127.0.0.1:{PORT}', f'localhost:{PORT}'):
            status, text = 403, 'Forbidden\n'
        elif self.path == '/health':
            status, text = 200, 'inference-npu-exporter\n'
        elif self.path == '/metrics':
            text = npu_metrics()
            status, text = (503, 'No NPU models served.\n') if text is None else (200, text)
        else:
            status, text = 404, 'Not found\n'
        data = text.encode()
        self.send_response(status)
        self.send_header('Content-Type', 'text/plain; version=0.0.4')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *_):
        pass


def serve():
    # Bind before publishing ownership. A foreign listener causes a visible failure.
    server = ThreadingHTTPServer(('127.0.0.1', PORT), Handler)
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
    RECORD.write_text(json.dumps({'pid': os.getpid(), 'start': identity(os.getpid())}))
    try:
        server.serve_forever()
    finally:
        server.server_close()
        RECORD.unlink(missing_ok=True)


def main():
    STORE.mkdir(parents=True, exist_ok=True)
    os.umask(0o077)
    action = sys.argv[1] if len(sys.argv) == 2 else ''
    if action == 'serve':
        # Direct invocations cannot create a second collector either.
        with (STORE / 'npu.serve.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            serve()
        return
    if action not in ('start', 'stop', 'status'):
        sys.exit('Usage: bin/npu-exporter.py start|stop|status')
    with (STORE / 'npu.control.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        fd = owned()
        if action == 'status':
            if fd is None:
                sys.exit('NPU collector: stopped')
            os.close(fd)
            print('NPU collector: running (127.0.0.1:9098)')
        elif action == 'stop':
            if fd is not None:
                try:
                    signal.pidfd_send_signal(fd, signal.SIGTERM)
                    if not select.select([fd], [], [], 5)[0]:
                        sys.exit('NPU collector did not stop within 5 seconds')
                finally:
                    os.close(fd)
            RECORD.unlink(missing_ok=True)
        elif fd is not None:
            os.close(fd)
            print('NPU collector already running')
        else:
            with (STORE / 'npu.log').open('wb') as log:
                child = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), 'serve'], stdin=subprocess.DEVNULL, stdout=log, stderr=log, start_new_session=True)
            for _ in range(50):
                if child.poll() is not None:
                    sys.exit('NPU collector failed; see cache/monitoring/npu.log')
                fd = owned()
                if fd is not None:
                    os.close(fd)
                    print('NPU collector started')
                    return
                time.sleep(.1)
            child.terminate()
            child.wait(timeout=5)
            sys.exit('NPU collector startup timed out')


if __name__ == '__main__':
    main()
