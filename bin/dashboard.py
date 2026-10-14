#!/usr/bin/env python3
"""Serve the dashboard page on loopback and run the fixed commands behind its buttons."""
import ctypes
import fcntl
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import re
import select
import struct
import subprocess
import threading
from urllib.request import ProxyHandler, build_opener

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "config/monitoring/dashboard.html"
RUN, MONITOR = str(ROOT / "bin/run.sh"), str(ROOT / "bin/monitor.sh")
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
ACTIONS = {f"/engine/{engine}/{verb}": (engine, verb, [RUN, engine, verb]) for engine in ENGINES for verb in ("start", "stop")} | {
    "/engine/halogen/start-npu": ("halogen", "start", ["env", f"NPU_MODELS={NPU_MODELS}", RUN, "halogen", "start"])} | {
    f"/monitoring/{verb}": ("monitoring", verb, [MONITOR, verb]) for verb in ("start", "stop")}
LOGS = {f"/logs/{engine}": [RUN, engine, "logs", "--follow"] for engine in ENGINES} | {
    f"/logs/{component}": [MONITOR, component, "logs", "--follow"] for component in COMPONENTS}
ACTION_TIMEOUT = 180

# Targets with a start or stop in flight, so their state reads as starting or stopping meanwhile.
BUSY: dict[str, str] = {}
LOCK = threading.Lock()
DIRECT = build_opener(ProxyHandler({}))

# The amdxdna sensor query, from include/uapi/drm/amdxdna_accel.h: DRM_IOCTL_AMDXDNA_GET_INFO with
# DRM_AMDXDNA_QUERY_SENSORS fills an array of struct amdxdna_drm_query_sensor. The driver fills these from the SoC's
# power-management firmware: one total-power sensor, then one busy percentage per NPU column.
ACCEL = "/dev/accel/accel0"
GET_INFO = 0xC0106447  # DRM_IOWR(DRM_COMMAND_BASE + 7, 16-byte struct amdxdna_drm_get_info)
QUERY_SENSORS = 4
SENSOR = struct.Struct("64sIIII64s16sbB6x")  # label, input, max, average, highest, status, units, unitm, type
POWER, COLUMN = 0, 1


def healthy(url: str) -> bool:
    try:
        with DIRECT.open(url, timeout=1) as response:
            return response.status == 200
    except OSError:
        return False


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
        engines[engine] = {"state": current, "since": container["StartedAt"] if container else 0}
    running = sum(containers.get(f"strix-halo-monitor-{component}", {}).get("State") == "running" for component in COMPONENTS)
    monitoring = busy.get("monitoring") or {0: "off", len(COMPONENTS): "on"}.get(running, "partial")
    logs = [engine for engine in ENGINES if f"strix-halo-{engine}" in containers]
    logs += [component for component in COMPONENTS if f"strix-halo-monitor-{component}" in containers]
    return {"monitoring": monitoring, "engines": engines, "logs": logs, "npu_models": NPU_MODELS}


def sensors() -> list[tuple[int, float]]:
    """Each sensor's type and reading in base units. The driver drops sensors that do not fit, so ask for room to spare."""
    buffer = ctypes.create_string_buffer(SENSOR.size * 16)
    request = bytearray(struct.pack("IIQ", QUERY_SENSORS, len(buffer), ctypes.addressof(buffer)))
    fd = os.open(ACCEL, os.O_RDWR)
    try:
        fcntl.ioctl(fd, GET_INFO, request)
    finally:
        os.close(fd)
    _, size, _ = struct.unpack("IIQ", request)
    readings = []
    for offset in range(0, size - size % SENSOR.size, SENSOR.size):
        _, value, _, _, _, _, _, unitm, kind = SENSOR.unpack_from(buffer.raw, offset)
        readings.append((kind, value * 10.0 ** unitm))
    return readings


def npu_metrics() -> str | None:
    """NPU readings while Halogen serves NPU models, else None. Reading the sensors wakes a suspended NPU for five
    seconds, so a scrape every two seconds would keep it awake while nothing uses it."""
    try:
        with DIRECT.open(ENGINES["halogen"], timeout=2) as response:
            npu = json.load(response).get("npu")
    except (OSError, ValueError, AttributeError):
        return None
    if not isinstance(npu, dict):
        return None
    lines = []
    try:
        readings = sensors()
    except OSError:
        readings = []
    busy = [value for kind, value in readings if kind == COLUMN]
    if busy:
        lines += ["# TYPE npu_busy_percent gauge", f"npu_busy_percent {sum(busy) / len(busy):g}"]
    power = [value for kind, value in readings if kind == POWER]
    if power:
        lines += ["# TYPE npu_power_watts gauge", f"npu_power_watts {power[0]:g}"]
    loaded = set(npu.get("loaded") or [])
    models = [model for model in npu.get("models") or [] if isinstance(model, str) and re.fullmatch(r"[a-z0-9][a-z0-9.-]*", model)]
    if models:
        lines.append("# TYPE npu_model_loaded gauge")
        lines += [f'npu_model_loaded{{model="{model}"}} {int(model in loaded)}' for model in models]
    if isinstance(npu.get("queued"), int):
        lines += ["# TYPE npu_queued gauge", f"npu_queued {npu['queued']}"]
    return "\n".join(lines) + "\n"


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
        elif self.path == "/state":
            try:
                self.reply(200, json.dumps(state()), "application/json")
            except (subprocess.SubprocessError, OSError, ValueError, KeyError) as error:
                self.reply(500, f"Cannot read container state: {error}\n")
        elif self.path == "/metrics":
            # Prometheus reads a refused scrape as down, which hides the NPU section while no NPU model is served.
            metrics = npu_metrics()
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
            BUSY[target] = "starting" if verb == "start" else "stopping"
        try:
            result = subprocess.run(command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                    text=True, timeout=ACTION_TIMEOUT)
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
