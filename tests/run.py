#!/usr/bin/env python3
"""Check launcher policy with CLI stubs, not engine compatibility."""
import fcntl
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
elif sys.argv[1] == "ps":
    print(os.environ.get("ACTIVE", ""))
elif sys.argv[1] == "inspect":
    print("false" if os.environ.get("EXITED") else "true")
''')
    podman.chmod(0o755)
    curl = commands / "curl"
    curl.write_text('''#!/usr/bin/env python3
import fcntl, json, os, sys
if sys.argv[-1].endswith(("/health", "/ready")):
    with open(os.environ["CACHE_ROOT"] + "/start.lock", "a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    sys.exit(22 if os.environ.get("UNREADY") else 0)
elif sys.argv[-1].endswith("/v1/models"):
    print('{"data":[{"id":"qwen3.8-flash-next"}]}')
else:
    with open(os.environ["REQUEST_RECORD"], "w") as output:
        output.write(sys.argv[sys.argv.index("--data") + 1])
    print('{"choices":[{"message":{"content":"ready"}}]}')
''')
    curl.chmod(0o755)
    env = dict(os.environ, PATH=f"{commands}:{os.environ['PATH']}", CALLS=str(calls),
               CACHE_ROOT=str(temp / "cache"), MODELS_DIR=str(temp / "models"),
               REQUEST_RECORD=str(temp / "payload"), CONTEXT="262144", SPECULATIVE="on")

    def run(*args, **overrides):
        return subprocess.run([str(temp / "bin/run.sh"), *args], env=env | overrides,
                              capture_output=True, text=True, timeout=10)

    for args in ((), ("halogen",), ("start", "halogen"), ("gufo", "unknown"),
                 ("unknown", "start"), ("halogen", "stop", "extra")):
        result = run(*args)
        assert result.returncode == 2, (args, result)
        assert not calls.exists(), f"Invalid arguments invoked Podman: {args}"
    assert "Engine comes first" in run("start", "halogen").stderr
    for engine in ("halogen", "gufo", "strixite"):
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

    calls.unlink()
    result = run("strixite", "start", "--wait", UNRELATED_SECRET="never-forward")
    assert result.returncode == 0 and "strixite ready at http://127.0.0.1:5300/v1" in result.stdout, result
    assert "pi --provider strixite --model qwen3.8-flash-next" in result.stdout
    assert "Normal Pi tools are not sandboxed" in result.stdout
    recorded = [json.loads(line) for line in calls.read_text().splitlines()]
    launch = next(call for call in recorded if call[0] == "run")
    for flag, value in (("--publish", "127.0.0.1:5300:5300"), ("--label", "io.strix-halo-inference.managed=true"),
                        ("--capacity", "262144"), ("--rope-yarn-factor", "1"), ("--mtp", "on"),
                        ("--think-nudge", "off"), ("--low-memory", "fail"), ("--prompt-cache-dir", "/cache"),
                        ("--prompt-cache-gib", "16"), ("--prompt-cache-ram-margin-gib", "8"), ("--stop-timeout", "90")):
        assert launch[launch.index(flag) + 1] == value, launch
    assert f"{env['MODELS_DIR']}:/models:ro" in launch
    assert f"{env['CACHE_ROOT']}/strixite:/cache:rw" in launch
    assert "STRIX_MODELS_DIR=/models/wemoh/Qwen3.8-Flash-Next-strixw" in launch
    assert not any(arg in ("--privileged", "--security-opt", "--group-add", "--ipc=host") for arg in launch)
    assert not any("never-forward" in arg for arg in launch)

    calls.unlink()
    result = run("strixite", "start", SPECULATIVE="off", CONTEXT="65536")
    assert result.returncode == 0, result
    launch = next(json.loads(line) for line in calls.read_text().splitlines() if json.loads(line)[0] == "run")
    assert launch[launch.index("--mtp") + 1] == "off" and launch[launch.index("--capacity") + 1] == "65536"
    for engine, active in (("strixite", "strix-halo-halogen"), ("strixite", "strix-halo-gufo"),
                           ("halogen", "strix-halo-strixite"), ("gufo", "strix-halo-strixite")):
        calls.unlink()
        result = run(engine, "start", ACTIVE=active)
        assert result.returncode == 1 and "Stop the active engine first" in result.stderr, result
        assert not any(json.loads(line)[0] == "run" for line in calls.read_text().splitlines())
    calls.unlink()
    with open(temp / "cache/start.lock", "a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        result = run("strixite", "start")
        assert result.returncode == 1 and "Another engine start" in result.stderr, result
    assert not any(json.loads(line)[0] == "run" for line in calls.read_text().splitlines())
    calls.unlink()
    result = run("strixite", "start", CONTEXT="1024")
    assert result.returncode == 2 and "4096..262144" in result.stderr, result
    assert not any(json.loads(line)[0] == "run" for line in calls.read_text().splitlines())
    calls.unlink()
    for engine, seconds in (("halogen", "60"), ("gufo", "60"), ("strixite", "90")):
        assert run(engine, "stop").returncode == 0
        assert json.loads(calls.read_text().splitlines()[-1]) == ["stop", "--time", seconds, f"strix-halo-{engine}"]
    result = run("strixite", "smoke")
    assert result.returncode == 0, result
    payload = json.loads((temp / "payload").read_text())
    assert payload["reasoning_effort"] == "none" and payload["max_tokens"] == 32
    assert "presence_penalty" not in payload and "chat_template_kwargs" not in payload
print("Launcher argument, logs and readiness policy checks passed.")
