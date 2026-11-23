#!/usr/bin/env python3
"""Serve the dashboard page on loopback and run the fixed commands behind its buttons."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import select
import subprocess
import threading
from urllib.request import ProxyHandler, build_opener

from weights import profiles, dashboard_profiles

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "config/monitoring/dashboard.html"
RUN, MONITOR, CACHE = str(ROOT / "bin/run.sh"), str(ROOT / "bin/monitor.sh"), str(ROOT / "bin/cache.sh")
# Prompt caches. Keep equal to bin/run.sh and bin/cache.sh.
CACHE_ROOT = Path(os.environ.get("CACHE_ROOT") or Path.home() / ".cache/strix-halo-inference")
PORT = int(os.environ.get("DASHBOARD_PORT", "9099"))
HOSTS = {f"127.0.0.1:{PORT}", f"localhost:{PORT}"}
ORIGINS = {f"http://{host}" for host in HOSTS}
# Health addresses. Keep equal to bin/run.sh.
ENGINES = {
    "halogen": "http://127.0.0.1:8731/health",
    "gufo": "http://127.0.0.1:8080/ready",
    "strixite": "http://127.0.0.1:5300/health",
}
COMPONENTS = ("prometheus", "exporter", "probe")
# The NPU model set behind the "Halogen + NPU" button. bin/run.sh validates it.
NPU_MODELS = os.environ.get("DASHBOARD_NPU_MODELS", "decider-0.8b,embeddinggemma-2,qwen3guard-stream-0.6b")
# The only commands a request can run. The path selects an entry; no request text reaches an argument.
ACTIONS = {f"/engine/{engine}/stop": (engine, "stop", [RUN, engine, "stop"]) for engine in ENGINES} | {
    f"/cache/{engine}/clear": (engine, "clear", [CACHE, engine, "clear"]) for engine in ENGINES} | {
    f"/monitoring/{verb}": ("monitoring", verb, [MONITOR, verb]) for verb in ("start", "stop")}
LOGS = {f"/logs/{engine}": [RUN, engine, "logs", "--follow"] for engine in ENGINES} | {
    f"/logs/{component}": [MONITOR, component, "logs", "--follow"] for component in COMPONENTS}
PROFILES = {engine: profiles(engine) for engine in ENGINES}
for engine, entries in PROFILES.items():
    default_vision = "on" if engine == "strixite" else "off"
    for verb in (("start", "start-npu") if engine == "halogen" else ("start",)):
        base = f"/engine/{engine}/{verb}"
        env = ["env", f"NPU_MODELS={NPU_MODELS}"] if verb == "start-npu" else ["env"]
        start = [RUN, engine, "start"]
        ACTIONS[base] = (engine, "start", [*env, f"VISION={default_vision}", *start])
        for name, entry in entries.items():
            args = [*start, "--weights", name]
            path = f"{base}/{name}"
            ACTIONS[path] = (engine, "start", [*env, f"VISION={default_vision}", *args])
            for vision in (("off", "on") if entry.get("projector_manifest") else ("off",)):
                ACTIONS[f"{path}/{vision}"] = (engine, "start", [*env, f"VISION={vision}", *args])
ACTION_TIMEOUT = 180

# Targets with a start, stop or cache clear in flight, so their state reads as starting, stopping or clearing meanwhile.
BUSY: dict[str, str] = {}
LOCK = threading.Lock()
DIRECT = build_opener(ProxyHandler({}))


def healthy(url: str) -> bool:
    try:
        with DIRECT.open(url, timeout=1) as response:
            return response.status == 200
    except OSError:
        return False


def disk_bytes(path: Path) -> int:
    """Bytes on disk under path, as du counts them. Zero when it does not exist."""
    total = 0
    for directory, _, files in os.walk(path):
        for name in files:
            try:
                total += os.lstat(os.path.join(directory, name)).st_blocks * 512
            except OSError:
                pass
    return total


def state() -> dict[str, object]:
    """Derive everything from Podman and health checks, so it stays true across helper restarts and CLI use."""
    listed = subprocess.run(["podman", "ps", "--all", "--format", "json"], capture_output=True, text=True, timeout=10, check=True)
    containers = {name: container for container in json.loads(listed.stdout) for name in container["Names"]}
    with LOCK:
        busy = dict(BUSY)
    engines: dict[str, dict[str, object]] = {}
    for engine, health in ENGINES.items():
        container = containers.get(f"strix-halo-{engine}")
        if engine in busy:
            current = busy[engine]
        elif container is None:
            current = "stopped"
        elif container["State"] != "running":
            current = "stopping"
        else:
            current = "ready" if healthy(health) else "starting"
        labels = (container or {}).get("Labels") or {}
        engines[engine] = {"state": current, "since": container["StartedAt"] if container else 0,
                           "vision": labels.get("io.strix-halo-inference.vision"),
                           "pi_model": labels.get("io.strix-halo-inference.pi-model"),
                           "weights": labels.get("io.strix-halo-inference.weights", "unknown") if container else None}
    running = sum(containers.get(f"strix-halo-monitor-{component}", {}).get("State") == "running" for component in COMPONENTS)
    monitoring = busy.get("monitoring") or {0: "off", len(COMPONENTS): "on"}.get(running, "partial")
    logs = [engine for engine in ENGINES if f"strix-halo-{engine}" in containers]
    logs += [component for component in COMPONENTS if f"strix-halo-monitor-{component}" in containers]
    caches = {engine: disk_bytes(CACHE_ROOT / engine) for engine in ENGINES}
    weights = {engine: dashboard_profiles(engine, entries) for engine, entries in PROFILES.items()}
    return {"weights": weights, "monitoring": monitoring, "engines": engines, "logs": logs, "npu_models": NPU_MODELS, "caches": caches}




class Handler(BaseHTTPRequestHandler):
    def allowed(self) -> bool:
        """Refuse DNS rebinding and requests made by other sites' pages. Nothing here sends cross-origin headers."""
        if self.headers.get("Host") not in HOSTS or self.headers.get("Sec-Fetch-Site", "none") not in ("same-origin", "none"):
            return False
        return self.command == "GET" or self.headers.get("Origin") in ORIGINS

    def reply(self, status: int, body: bytes | str, kind: str = "text/plain; charset=utf-8") -> None:
        data = body.encode() if isinstance(body, str) else body
        self.send_response(status)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def follow(self, command: list[str]) -> None:
        """Stream a log viewer's output until it ends or the page closes the connection."""
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        with subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, bufsize=0) as viewer:
            assert viewer.stdout is not None
            try:
                while True:
                    readable, _, _ = select.select([viewer.stdout, self.connection], [], [])
                    if self.connection in readable:
                        break
                    chunk = os.read(viewer.stdout.fileno(), 65536)
                    if not chunk:
                        break
                    self.wfile.write(chunk)
            except OSError:
                pass
            finally:
                viewer.terminate()

    def do_GET(self) -> None:
        if not self.allowed():
            self.reply(403, "Forbidden\n")
        elif self.path == "/":
            self.reply(200, PAGE.read_bytes(), "text/html; charset=utf-8")
        elif self.path in ("/dashboard.js", "/dashboard.css"):
            name = self.path[1:]
            self.reply(200, (PAGE.parent / name).read_bytes(), "text/javascript" if name.endswith(".js") else "text/css")
        elif self.path == "/state":
            try:
                self.reply(200, json.dumps(state()), "application/json")
            except (subprocess.SubprocessError, OSError, ValueError, KeyError) as error:
                self.reply(500, f"Cannot read container state: {error}\n")
        elif self.path == "/metrics":
            # Prometheus reads a refused scrape as down, which hides the NPU section while no NPU model is served.
            try:
                with DIRECT.open("http://127.0.0.1:9098/metrics", timeout=3) as response:
                    metrics = response.read(65536).decode()
            except OSError:
                metrics = None
            if metrics is None:
                self.reply(503, "No NPU models served.\n")
            else:
                self.reply(200, metrics, "text/plain; version=0.0.4")
        elif self.path in LOGS:
            self.follow(LOGS[self.path])
        else:
            self.reply(404, "Not found\n")

    def do_POST(self) -> None:
        if not self.allowed():
            return self.reply(403, "Forbidden\n")
        if self.path not in ACTIONS:
            return self.reply(404, "Not found\n")
        target, verb, command = ACTIONS[self.path]
        with LOCK:
            if target in BUSY:
                return self.reply(409, f"{target} is already {BUSY[target]}.\n")
            BUSY[target] = {"start": "starting", "stop": "stopping", "clear": "clearing"}[verb]
        try:
            result = subprocess.run(command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                    text=True, timeout=ACTION_TIMEOUT,
                                    env={key: value for key, value in os.environ.items() if key not in ("WEIGHTS", "GUFO_MODEL", "NPU_MODELS", "VISION")})
            self.reply(200 if result.returncode == 0 else 409, result.stdout)
        except subprocess.TimeoutExpired:
            self.reply(504, f"No result after {ACTION_TIMEOUT} seconds. Inspect the {target} status in a terminal.\n")
        finally:
            with LOCK:
                del BUSY[target]

    def log_message(self, format: str, *args: object) -> None:
        # State polls arrive every two seconds. Record only the requests that act.
        if self.command == "POST":
            super().log_message(format, *args)


if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"Dashboard: http://127.0.0.1:{PORT}/ (Ctrl+C stops only this helper, not engines or monitoring)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print()
