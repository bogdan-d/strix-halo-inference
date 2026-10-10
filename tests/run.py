#!/usr/bin/env python3
"""Check launcher policy with CLI stubs, not engine compatibility."""
import json
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]

with tempfile.TemporaryDirectory(prefix="strix-halo-run-") as directory:
    temp = Path(directory)
    commands = temp / "commands"
    commands.mkdir()
    calls = temp / "calls"
    podman = commands / "podman"
    podman.write_text('''#!/usr/bin/env python3
import json, os, sys
with open(os.environ["CALLS"], "a") as output:
    output.write(json.dumps(sys.argv[1:]) + "\\n")
if sys.argv[1:3] == ["container", "exists"] and os.environ.get("MISSING"):
    sys.exit(1)
''')
    podman.chmod(0o755)
    env = dict(os.environ, PATH=f"{commands}:{os.environ['PATH']}", CALLS=str(calls))

    def run(*args, **overrides):
        return subprocess.run([str(ROOT / "bin/run.sh"), *args], env=env | overrides,
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
print("Launcher argument validation and dispatch passed.")
