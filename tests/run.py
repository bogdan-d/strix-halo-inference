#!/usr/bin/env python3
"""Check launcher policy with CLI stubs, not engine compatibility."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]

with tempfile.TemporaryDirectory(prefix="strix-halo-run-") as directory:
    temp = Path(directory)
    commands = temp / "commands"
    commands.mkdir()
    calls = temp / "calls"
    (temp / "bin").mkdir()
    (temp / "config").mkdir()
    shutil.copy(ROOT / "bin/run.sh", temp / "bin/run.sh")
    shutil.copy(ROOT / "config/pins.env", temp / "config/pins.env")
    models = temp / "bin/models.sh"
    models.write_text("#!/bin/sh\nexit 0\n")
    models.chmod(0o755)
    podman = commands / "podman"
    podman.write_text('''#!/usr/bin/env python3
import json, os, sys
with open(os.environ["CALLS"], "a") as output:
    output.write(json.dumps(sys.argv[1:]) + "\\n")
if sys.argv[1:3] == ["container", "exists"] and os.environ.get("MISSING"):
    sys.exit(1)
if sys.argv[1] == "info":
    print("true" if "Rootless" in sys.argv[-1] else "runc")
elif sys.argv[1] == "run":
    print("fixture-container")
elif sys.argv[1] == "inspect":
    print("false" if os.environ.get("EXITED") else "true")
''')
    podman.chmod(0o755)
    curl = commands / "curl"
    curl.write_text('''#!/usr/bin/env python3
import fcntl, os, sys
with open(os.environ["CACHE_ROOT"] + "/start.lock", "a") as lock:
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
sys.exit(22 if os.environ.get("UNREADY") else 0)
''')
    curl.chmod(0o755)
    env = dict(os.environ, PATH=f"{commands}:{os.environ['PATH']}", CALLS=str(calls),
               CACHE_ROOT=str(temp / "cache"))

    def run(*args, **overrides):
        return subprocess.run([str(temp / "bin/run.sh"), *args], env=env | overrides,
                              capture_output=True, text=True, timeout=10)

    for args in ((), ("halogen",), ("start", "halogen"), ("gufo", "unknown"),
                 ("unknown", "start"), ("halogen", "stop", "extra")):
        result = run(*args)
        assert result.returncode == 2, (args, result)
        assert not calls.exists(), f"Invalid arguments invoked Podman: {args}"
    assert "Engine comes first" in run("start", "halogen").stderr
    for engine in ("halogen", "gufo"):
        result = run(engine, "pull")
        assert result.returncode == 0, result
        assert engine in calls.read_text(), calls.read_text()
        calls.unlink()
    assert run("halogen", "logs", "--follow", "extra").returncode == 2
    assert not calls.exists()
    for options in ((), ("--follow",)):
        assert run("gufo", "logs", *options).returncode == 0
        recorded = [json.loads(line) for line in calls.read_text().splitlines()]
        assert recorded[-1] == ["logs", "--tail", "100", *options, "strix-halo-gufo"]
        assert not any(call[0] in ("start", "stop", "run") for call in recorded)
        calls.unlink()
    result = run("halogen", "logs", "--follow", MISSING="1")
    assert result.returncode == 1 and "No container logs available" in result.stderr
    assert all(json.loads(line)[0] != "logs" for line in calls.read_text().splitlines())
    calls.unlink()
    assert run("halogen", "start", "--wait", START_TIMEOUT="0").returncode == 2
    assert not calls.exists()
    result = run("gufo", "start", "--wait")
    assert result.returncode == 0 and "gufo ready" in result.stdout, result
    assert "pi --provider gufo --model qwen3.8-flash-next" in result.stdout
    result = run("halogen", "start", "--wait", UNREADY="1", START_TIMEOUT="1")
    assert result.returncode == 1 and "Startup timeout" in result.stderr, result
    result = run("halogen", "start", "--wait", EXITED="1")
    assert result.returncode == 1 and "exited before readiness" in result.stderr, result
    assert not any(json.loads(line)[0] == "stop" for line in calls.read_text().splitlines())
print("Launcher argument, logs and readiness policy checks passed.")
