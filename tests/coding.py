#!/usr/bin/env python3
"""Matched three-engine coding comparison with mandatory Bubblewrap and strict JSON.

Run --smoke first. Summary JSONL contains no conversations or generated source.
"""

import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from threading import Event
import time
from urllib.request import urlopen

from thinking import ROOT, trial
from thinking_tasks import TASKS
from pi_sandbox import verify_sandbox

ENGINES = ("halogen", "gufo", "strixite")
GIB = 1024 ** 3


def memory() -> dict[str, int]:
    fields = {line.split(":")[0]: int(line.split()[1]) * 1024
              for line in Path("/proc/meminfo").read_text().splitlines()}
    return {"available": fields["MemAvailable"], "swap": fields["SwapTotal"] - fields["SwapFree"],
            "gtt": sum(int(path.read_text()) for path in Path("/sys/class/drm").glob("card[0-9]*/device/mem_info_gtt_used"))}


def sample_memory(done: Event) -> list[dict[str, int]]:
    samples = [memory()]
    while not done.wait(1):
        samples.append(memory())
    samples.append(memory())
    return samples


def release_memory(baseline: dict[str, int]) -> dict[str, int]:
    deadline = time.monotonic() + 30
    while True:
        current = memory()
        # Host-wide tolerances allow desktop activity and reclaimable page-cache changes.
        if current["gtt"] <= baseline["gtt"] + GIB and current["available"] >= baseline["available"] - 8 * GIB:
            return current
        if time.monotonic() >= deadline:
            raise RuntimeError(f"Memory did not return near baseline: {baseline=}, {current=}")
        time.sleep(1)


def run_engine(engine: str, base: Path, smoke: bool, repeats: int) -> None:
    launch_env = dict(os.environ, CACHE_ROOT=str(base / "engine-cache"), CONTEXT="262144",
                      SPECULATIVE="on", START_TIMEOUT="300")
    baseline = memory()
    done = Event()
    with ThreadPoolExecutor(max_workers=1) as pool:
        samples = pool.submit(sample_memory, done)
        cid = None
        try:
            started = subprocess.run([str(ROOT / "bin/run.sh"), engine, "start", "--wait"],
                                     env=launch_env, capture_output=True, text=True, timeout=360)
            match = re.search(r"^([a-f0-9]{64})$", started.stdout, re.M)
            cid = match[1] if match else None
            if started.returncode or not cid:
                raise RuntimeError(f"{engine} startup failed: {started.stdout}\n{started.stderr}")
            if engine == "strixite":
                with urlopen("http://127.0.0.1:5300/health", timeout=5) as response:
                    health = json.load(response)
                assert health["context_length"] == 262144 and not health.get("degraded"), health
            for repeat in range(1, repeats + 1):
                efforts = ("off", "medium") if smoke else ("off", "medium", "xhigh")
                if repeat % 2 == 0:
                    efforts = tuple(reversed(efforts))
                for task in TASKS[:1] if smoke else TASKS:
                    for effort in efforts:
                        result = trial(task, engine, effort, repeat, base, strict=True)
                        print(json.dumps(result), flush=True)
                        if smoke and (not result["passed"] or
                                      not {"read", "bash"} <= result["tools"].keys() or
                                      not {"edit", "write"}.intersection(result["tools"])):
                            raise RuntimeError("Sandboxed coding smoke gate failed. Do not continue the matrix.")
        finally:
            try:
                if not cid:
                    inspected = subprocess.run(["podman", "inspect", f"strix-halo-{engine}"],
                                               capture_output=True, text=True, timeout=10)
                    if inspected.returncode == 0:
                        container = json.loads(inspected.stdout)[0]
                        expected = str(base / "engine-cache" / engine)
                        if any(mount.get("Source") == expected for mount in container.get("Mounts", [])):
                            cid = container["Id"]
                if cid:
                    stop_timeout = 90 if engine == "strixite" else 60
                    subprocess.run(["podman", "stop", "--time", str(stop_timeout), cid],
                                   check=True, capture_output=True, timeout=stop_timeout + 30)
                released = release_memory(baseline)
            finally:
                done.set()
                readings = samples.result()
                print(json.dumps({"memory": {"engine": engine, "interval_seconds": 1,
                    "samples": len(readings), "before": baseline, "after": memory(),
                    "min_available_bytes": min(row["available"] for row in readings),
                    "peak_gtt_bytes": max(row["gtt"] for row in readings),
                    "peak_swap_bytes": max(row["swap"] for row in readings)}}), flush=True)
            print(json.dumps({"engine_stopped": engine, "memory_release_verified": True, "after": released}), flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--repeats", type=int, default=2)
    args = parser.parse_args()
    if not 1 <= args.repeats <= 10:
        parser.error("repeats must be 1..10")
    active = subprocess.check_output(["podman", "ps", "--filter", "label=io.strix-halo-inference.managed=true",
                                      "--format", "{{.Names}}"], text=True)
    if active.strip():
        raise SystemExit("Stop all managed inference engines before this comparison.")
    live = Path(os.environ.get("PI_CODING_AGENT_DIR", str(Path.home() / ".pi/agent")))
    originals = {name: (live / name).read_bytes() if (live / name).exists() else None
                 for name in ("models.json", "settings.json")}
    profile = json.loads((ROOT / "config/pi/models.json").read_text())
    for provider in profile["providers"].values():
        provider["models"][0]["samplingParamsByThinkingLevel"]["off"]["presence_penalty"] = 0.0
    results = ROOT / "results"
    existed = results.exists()
    results.mkdir(exist_ok=True)
    base = Path(tempfile.mkdtemp(prefix="coding-", dir=results))
    try:
        agent = base / "agent"
        agent.mkdir()
        (agent / "models.json").write_text(json.dumps(profile))
        (agent / "settings.json").write_text(json.dumps({"retry": {"enabled": False},
            "enableInstallTelemetry": False, "enableAnalytics": False, "shellPath": "/bin/bash",
            "compaction": {"reserveTokens": 16384, "keepRecentTokens": 32768}}))
        shutil.copy(ROOT / "tests/strixite_guard.ts", agent / "guard.ts")
        probe = base / "preflight"
        probe.mkdir()
        print(json.dumps({"metadata": {"pi": verify_sandbox(probe, agent), "smoke": args.smoke,
            "repeats": 1 if args.smoke else args.repeats, "context": 262144, "mtp": "on",
            "filesystem_sandbox": "bubblewrap", "strict_json_guard": "all engines",
            "network": "host shared for localhost API", "off_presence_penalty": 0,
            "profile_sha256": hashlib.sha256((agent / "models.json").read_bytes()).hexdigest(),
            "pins_sha256": hashlib.sha256((ROOT / "config/pins.env").read_bytes()).hexdigest(),
            "cache": "fresh per-engine disk directory, retained across trials; OS cache not flushed",
            "governor": Path("/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor").read_text().strip()}}), flush=True)
        for engine in ENGINES:
            run_engine(engine, base, args.smoke, 1 if args.smoke else args.repeats)
    finally:
        # Do not delete cache mounts if stopping an owned engine failed.
        running = subprocess.check_output(["podman", "ps", "--format", "{{.Names}}"], text=True).splitlines()
        if any(f"strix-halo-{engine}" in running for engine in ENGINES):
            raise SystemExit(f"Engine still running. Stop it before deleting temporary state at {base}")
        assert base.parent == results and base.name.startswith("coding-")
        subprocess.run(["rm", "--preserve-root=all", "--one-file-system", "-r", "--", str(base)], check=True)
        if not existed and not any(results.iterdir()):
            results.rmdir()
        for name, original in originals.items():
            current = (live / name).read_bytes() if (live / name).exists() else None
            assert current == original, f"Live Pi configuration changed: {name}"
    print(json.dumps({"complete": True, "live_pi_unchanged": True}), flush=True)


if __name__ == "__main__":
    main()
