#!/usr/bin/env python3
"""Manual paired Pi evaluation. Never included in ordinary offline checks."""
import argparse
from dataclasses import asdict, dataclass, field
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import tempfile
import time

from thinking_tasks import TASKS, Task

ROOT = Path(__file__).resolve().parents[1]


@dataclass
class Events:
    tools: dict[str, int] = field(default_factory=dict)
    tool_errors: int = 0
    turns: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cached_tokens: int = 0
    thinking_chars: int = 0
    stop_reasons: list[str] = field(default_factory=list)
    settled: bool = False
    aborted: bool = False


def events(text: str) -> Events:
    result = Events()
    # JSONL framing splits on LF, never on Unicode line separators in strings.
    for line in text.split("\n"):
        if not line.strip():
            continue
        event = json.loads(line)
        if not isinstance(event, dict) or not isinstance(event.get("type"), str):
            raise ValueError("Invalid Pi event")
        if event["type"] == "tool_execution_start":
            name = event["toolName"]
            result.tools[name] = result.tools.get(name, 0) + 1
        elif event["type"] == "tool_execution_end":
            result.tool_errors += int(bool(event.get("isError")))
        elif event["type"] == "agent_settled":
            result.settled = True
            result.aborted = bool(event.get("aborted"))
        elif event["type"] == "message_end" and event["message"].get("role") == "assistant":
            message = event["message"]
            result.turns += 1
            result.stop_reasons.append(message["stopReason"])
            usage = message["usage"]
            result.input_tokens += int(usage["input"])
            result.output_tokens += int(usage["output"])
            result.cached_tokens += int(usage["cacheRead"])
            result.thinking_chars += sum(len(block.get("thinking", "")) for block in message["content"] if block["type"] == "thinking")
    return result


def check_task(task: Task, directory: Path) -> bool:
    # Run the original checks, not a potentially edited copy supplied by the agent.
    result = subprocess.run([sys.executable, "-c", task.checks], cwd=directory,
                            capture_output=True, text=True, timeout=15)
    return result.returncode == 0


def self_check() -> None:
    for task in TASKS:
        with tempfile.TemporaryDirectory(prefix="thinking-baseline-") as directory:
            for name, body in task.files.items():
                (Path(directory) / name).write_text(body)
            assert not check_task(task, Path(directory)), f"Baseline passed: {task.name}"
    sample = json.dumps({"type": "message_end", "message": {
        "role": "assistant", "stopReason": "length", "content": [{"type": "thinking", "thinking": "a\u2028b"}],
        "usage": {"input": 7, "output": 9, "cacheRead": 3}}})
    measured = events(sample + '\n{"type":"tool_execution_start","toolName":"read"}\n{"type":"agent_settled","aborted":false}\n')
    assert measured.stop_reasons == ["length"] and measured.thinking_chars == 3
    assert measured.output_tokens == 9 and measured.cached_tokens == 3 and measured.settled
    assert json.loads(json.dumps(asdict(measured)))["tools"] == {"read": 1}
    print("Baseline rejection and Pi-event accounting checks passed.", flush=True)


def trial(task: Task, engine: str, effort: str, repeat: int, base: Path, env: dict[str, str]) -> dict:
    workspace = base / f"{engine}-{task.name}-{repeat}-{effort}"
    workspace.mkdir()
    for name, body in task.files.items():
        (workspace / name).write_text(body)
    (workspace / "checks.py").write_text(task.checks)
    model = "halogen-qwen3.8-flash-next" if engine == "halogen" else "qwen3.8-flash-next"
    args = ["pi", "--offline", "--mode", "json", "--provider", engine, "--model", model,
            "--thinking", effort, "--no-session", "--no-extensions", "--no-skills",
            "--no-prompt-templates", "--no-context-files", "--no-themes", "--no-approve",
            "--no-mcp", "--tools", "read,edit,write,bash", task.prompt]
    start = time.monotonic()
    process = subprocess.Popen(args, cwd=workspace, env=env, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, text=True, start_new_session=True)
    timed_out = False
    try:
        stdout, stderr = process.communicate(timeout=600)
    except subprocess.TimeoutExpired:
        timed_out = True
        os.killpg(process.pid, signal.SIGTERM)
        try:
            stdout, stderr = process.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            stdout, stderr = process.communicate()
    except BaseException:
        # Cancel tools as well as Pi before cleaning its workspace.
        os.killpg(process.pid, signal.SIGKILL)
        process.communicate()
        raise
    elapsed = time.monotonic() - start
    measured = events(stdout)
    checks_unchanged = (workspace / "checks.py").read_text() == task.checks
    checks_passed = check_task(task, workspace)
    complete = measured.settled and not measured.aborted and bool(measured.stop_reasons) and measured.stop_reasons[-1] == "stop"
    failed_messages = any(reason in ("length", "error", "aborted") for reason in measured.stop_reasons)
    return {"engine": engine, "task": task.name, "effort": effort, "repeat": repeat,
            "seconds": round(elapsed, 2), "pi_exit": process.returncode, "timeout": timed_out,
            "stderr_present": bool(stderr.strip()), "checks_passed": checks_passed,
            "checks_unchanged": checks_unchanged,
            "passed": checks_passed and checks_unchanged and complete and not failed_messages and not timed_out and process.returncode == 0,
            **asdict(measured)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-check", action="store_true")
    parser.add_argument("--repeats", type=int, default=2)
    args = parser.parse_args()
    if args.self_check:
        self_check()
        return
    if not 1 <= args.repeats <= 10:
        parser.error("repeats must be 1..10")
    active = subprocess.check_output(["podman", "ps", "--filter", "label=io.strix-halo-inference.managed=true", "--format", "{{.Names}}"], text=True)
    if active.strip():
        raise SystemExit("Stop managed inference engines before this isolated comparison.")
    agent_dir = Path(os.environ.get("PI_CODING_AGENT_DIR", str(Path.home() / ".pi/agent")))
    originals = {name: (agent_dir / name).read_bytes() if (agent_dir / name).exists() else None for name in ("models.json", "settings.json")}
    profile = (ROOT / "config/pi/models.json").read_bytes()
    pins = (ROOT / "config/pins.env").read_bytes()
    print(json.dumps({"metadata": {"pi": subprocess.check_output(["pi", "--version"], text=True).strip(),
        "profile_sha256": hashlib.sha256(profile).hexdigest(), "pins_sha256": hashlib.sha256(pins).hexdigest(),
        "context": 262144, "mtp": "on", "cache": "fresh disk directory per engine; retained across trials; OS file cache not flushed",
        "governor": Path("/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor").read_text().strip()}}), flush=True)
    results = ROOT / "results"
    existed = results.exists()
    results.mkdir(exist_ok=True)
    base = Path(tempfile.mkdtemp(prefix="thinking-", dir=results))
    try:
        agent = base / "agent"
        agent.mkdir()
        (agent / "models.json").write_bytes(profile)
        (agent / "settings.json").write_bytes((ROOT / "config/pi/settings.json").read_bytes())
        home = base / "home"
        home.mkdir()
        pi_env = {"PATH": os.environ["PATH"], "HOME": str(home), "LANG": "C.UTF-8",
                  "PI_CODING_AGENT_DIR": str(agent), "PI_OFFLINE": "1", "PI_TELEMETRY": "0",
                  "XDG_CACHE_HOME": str(base / "client-cache"), "NO_PROXY": "127.0.0.1,localhost"}
        launch_env = dict(os.environ, CACHE_ROOT=str(base / "engine-cache"), CONTEXT="262144", SPECULATIVE="on", START_TIMEOUT="300")
        for engine in ("halogen", "gufo"):
            cid = None
            try:
                started = subprocess.run([str(ROOT / "bin/run.sh"), engine, "start", "--wait"],
                                         env=launch_env, capture_output=True, text=True, timeout=360)
                match = re.search(r"^([a-f0-9]{64})$", started.stdout, re.M)
                cid = match[1] if match else None
                if started.returncode or not cid:
                    raise RuntimeError(f"{engine} startup failed: {started.stderr}")
                for repeat in range(1, args.repeats + 1):
                    order = ("medium", "xhigh") if repeat % 2 else ("xhigh", "medium")
                    for task in TASKS:
                        for effort in order:
                            print(json.dumps(trial(task, engine, effort, repeat, base, pi_env)), flush=True)
            finally:
                if not cid:
                    inspected = subprocess.run(["podman", "inspect", f"strix-halo-{engine}"], capture_output=True, text=True, timeout=10)
                    if inspected.returncode == 0:
                        container = json.loads(inspected.stdout)[0]
                        expected = str(base / "engine-cache" / engine)
                        if any(mount.get("Source") == expected for mount in container.get("Mounts", [])):
                            cid = container["Id"]
                if cid:
                    subprocess.run(["podman", "stop", "--time", "60", cid], check=True, capture_output=True, timeout=90)
    finally:
        # Only remove our verified temporary tree, never pre-existing results.
        assert base.parent == results and base.name.startswith("thinking-")
        running = json.loads(subprocess.check_output(["podman", "ps", "--format", "json"], text=True))
        if any(container["Names"][0] in ("strix-halo-halogen", "strix-halo-gufo") for container in running):
            raise RuntimeError(f"Engine still running. Temporary state retained at {base}")
        subprocess.run(["rm", "--preserve-root=all", "--one-file-system", "-r", "--", str(base)], check=True)
        if not existed and not any(results.iterdir()):
            results.rmdir()
        for name, original in originals.items():
            current = (agent_dir / name).read_bytes() if (agent_dir / name).exists() else None
            assert current == original, f"Live Pi configuration changed: {name}"
    print(json.dumps({"complete": True, "live_pi_unchanged": True}), flush=True)


if __name__ == "__main__":
    main()
