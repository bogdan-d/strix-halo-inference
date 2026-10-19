#!/usr/bin/env python3
"""Check the dashboard helper's request policy with script stubs, not Podman or engine behavior."""
from http.client import HTTPConnection
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]

with tempfile.TemporaryDirectory(prefix="strix-dashboard-") as directory:
    temp = Path(directory)
    (temp / "bin").mkdir()
    (temp / "config/monitoring").mkdir(parents=True)
    commands = temp / "commands"
    commands.mkdir()
    calls = temp / "calls"
    viewer = temp / "viewer"
    shutil.copy(ROOT / "bin/dashboard.py", temp / "bin/dashboard.py")
    (temp / "config/monitoring/dashboard.html").write_text("fixture page")
    stub = '''#!/usr/bin/env python3
import json, os, sys, time
a = sys.argv[1:]
with open(os.environ["CALLS"], "a") as output:
    output.write(json.dumps([os.path.basename(sys.argv[0]), *a] + [f"NPU_MODELS={value}" for value in [os.environ.get("NPU_MODELS")] if value]) + "\\n")
if a[-1] == "--follow":
    with open(os.environ["VIEWER"], "w") as output:
        output.write(str(os.getpid()))
    print("first line", flush=True)
    time.sleep(30)
elif a == ["gufo", "start"]:
    print("Stop the active engine first: fixture")
    sys.exit(1)
else:
    print("done")
'''
    for name in ("run.sh", "monitor.sh", "cache.sh"):
        (temp / "bin" / name).write_text(stub)
        (temp / "bin" / name).chmod(0o755)
    (commands / "podman").write_text("#!/bin/sh\necho '[]'\n")
    (commands / "podman").chmod(0o755)
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    origin = f"http://127.0.0.1:{port}"
    (temp / "cache/halogen").mkdir(parents=True)
    (temp / "cache/halogen/entry").write_bytes(b"x" * 8192)
    env = dict(os.environ, PATH=f"{commands}:{os.environ['PATH']}", CALLS=str(calls), VIEWER=str(viewer), DASHBOARD_PORT=str(port),
               DASHBOARD_NPU_MODELS="decider-0.8b", CACHE_ROOT=str(temp / "cache"))
    env.pop("NPU_MODELS", None)
    helper = subprocess.Popen(["python3", str(temp / "bin/dashboard.py")], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def request(method: str, path: str, **headers: str) -> tuple[int, str, list[list[str]]]:
        calls.write_text("")
        connection = HTTPConnection("127.0.0.1", port, timeout=10)
        connection.request(method, path, headers={name.replace("_", "-"): value for name, value in headers.items()})
        response = connection.getresponse()
        body = response.read().decode()
        connection.close()
        return response.status, body, [json.loads(line) for line in calls.read_text().splitlines()]

    try:
        for _ in range(50):
            try:
                socket.create_connection(("127.0.0.1", port), timeout=1).close()
                break
            except OSError:
                time.sleep(0.1)
        assert request("GET", "/")[:2] == (200, "fixture page")
        status, body, _ = request("GET", "/state")
        current = json.loads(body)
        caches = current.pop("caches")
        assert caches["halogen"] >= 8192 and caches["gufo"] == caches["strixite"] == 0, caches
        assert status == 200 and current == {
            "monitoring": "off", "logs": [], "npu_models": "decider-0.8b",
            "engines": {engine: {"state": "stopped", "since": 0} for engine in ("halogen", "gufo", "strixite")}}, body
        # Other sites' pages, rebound host names and requests without this page's origin never reach a command.
        for method, path, headers in (
                ("GET", "/state", {"Host": "evil.example"}),
                ("GET", "/logs/halogen", {"Sec_Fetch_Site": "cross-site"}),
                ("POST", "/engine/halogen/start", {}),
                ("POST", "/engine/halogen/start", {"Origin": "http://evil.example"}),
                ("POST", "/engine/halogen/start", {"Origin": origin, "Host": "evil.example"}),
                ("POST", "/engine/halogen/start", {"Origin": origin, "Sec_Fetch_Site": "same-site"}),
                ("POST", "/engine/halogen/start-npu", {"Origin": "http://evil.example"})):
            status, _, recorded = request(method, path, **headers)
            assert status == 403 and not recorded, (method, path, headers, status, recorded)
        for method, path in (("POST", "/engine/halogen/pull"), ("POST", "/engine/other/start"), ("POST", "/engine/halogen/start/x"), ("POST", "/engine/gufo/start-npu"),
                             ("POST", "/cache/other/clear"), ("GET", "/cache/halogen/clear"),
                             ("POST", "/monitoring/pull"), ("POST", "/logs/halogen"), ("GET", "/logs/grafana"),
                             ("GET", "/engine/halogen/start"), ("GET", "/../bin/run.sh")):
            status, _, recorded = request(method, path, Origin=origin)
            assert status == 404 and not recorded, (method, path, status, recorded)
        for path, expected in (("/engine/halogen/start", ["run.sh", "halogen", "start"]),
                               ("/engine/halogen/start-npu", ["run.sh", "halogen", "start", "NPU_MODELS=decider-0.8b"]),
                               ("/engine/strixite/stop", ["run.sh", "strixite", "stop"]),
                               ("/cache/gufo/clear", ["cache.sh", "gufo", "clear"]),
                               ("/monitoring/start", ["monitor.sh", "start"]), ("/monitoring/stop", ["monitor.sh", "stop"])):
            status, body, recorded = request("POST", path, Origin=origin, Sec_Fetch_Site="same-origin")
            assert (status, body, recorded) == (200, "done\n", [expected]), (path, status, body, recorded)
        status, body, _ = request("POST", "/engine/gufo/start", Origin=origin)
        assert status == 409 and "Stop the active engine first" in body, (status, body)
        # Closing the page's connection ends the log viewer it started.
        calls.write_text("")
        connection = HTTPConnection("127.0.0.1", port, timeout=10)
        connection.request("GET", "/logs/prometheus")
        response = connection.getresponse()
        assert response.status == 200 and response.readline() == b"first line\n"
        assert json.loads(calls.read_text()) == ["monitor.sh", "prometheus", "logs", "--follow"]
        pid = int(viewer.read_text())
        response.close()
        connection.close()
        for _ in range(50):
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                break
            time.sleep(0.1)
        else:
            raise AssertionError("log viewer outlived its connection")
    finally:
        helper.terminate()
        helper.wait(timeout=10)
print("Dashboard helper origin, allowlist and log-viewer cleanup checks passed.")
