#!/usr/bin/env python3
"""Check project lifecycle safety with CLI stubs, not provider compatibility."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]

with tempfile.TemporaryDirectory(prefix="strix-monitor-") as directory:
    temp = Path(directory)
    (temp / "bin").mkdir()
    (temp / "config/monitoring").mkdir(parents=True)
    commands = temp / "commands"
    commands.mkdir()
    calls = temp / "calls"
    shutil.copy(ROOT / "bin/monitor.sh", temp / "bin/monitor.sh")
    shutil.copy(ROOT / "config/monitoring/pins.env", temp / "config/monitoring/pins.env")
    podman = commands / "podman"
    podman.write_text('''#!/usr/bin/env python3
import json, os, sys
a = sys.argv[1:]
with open(os.environ["CALLS"], "a") as output:
    output.write(json.dumps(a) + "\\n")
if a[:2] == ["container", "exists"]:
    sys.exit(0 if os.environ.get("EXISTING") else 1)
if a[:2] == ["volume", "exists"]:
    sys.exit(0 if os.environ.get("UNOWNED_VOLUME") else 1)
if "inspect" in a:
    print("false" if os.environ.get("UNOWNED_VOLUME") or os.environ.get("UNOWNED_CONTAINER") or os.environ.get("EXITED") else "true")
elif a[0] == "run":
    name = a[a.index("--name")+1]
    if os.environ.get("FAIL_RUN") and name.endswith(os.environ["FAIL_RUN"]):
        sys.exit(1)
    print("owned-" + name)
''')
    podman.chmod(0o755)
    curl = commands / "curl"
    curl.write_text("#!/bin/sh\nexit 0\n")
    curl.chmod(0o755)
    env = dict(os.environ, PATH=f"{commands}:{os.environ['PATH']}", CALLS=str(calls))

    def run(*args, **overrides):
        calls.write_text("")
        result = subprocess.run([str(temp / "bin/monitor.sh"), *args], env=env | overrides,
                                capture_output=True, text=True, timeout=10)
        return result, [json.loads(line) for line in calls.read_text().splitlines()]

    for args in ((), ("unknown",), ("start", "--fg"), ("grafana", "start"),
                 ("grafana", "logs", "extra"), ("stop", "extra")):
        result, recorded = run(*args)
        assert result.returncode == 2 and not recorded, (args, result)
    result, recorded = run("start", EXISTING="1")
    assert result.returncode == 1 and not any(a[0] in ("run", "stop") for a in recorded)
    result, recorded = run("start", UNOWNED_VOLUME="1")
    assert result.returncode == 1 and not any(a[0] == "run" for a in recorded)
    result, recorded = run("start", FAIL_RUN="prometheus")
    assert result.returncode == 1, result
    assert [a[-1] for a in recorded if a[0] == "stop"] == ["owned-strix-halo-monitor-exporter", "owned-strix-halo-monitor-probe"]
    assert not any(a[:2] == ["volume", "rm"] for a in recorded)
    result, recorded = run("start", EXITED="1")
    assert result.returncode == 1 and len([a for a in recorded if a[0] == "stop"]) == 4
    result, recorded = run("start")
    assert result.returncode == 0, result
    launched = [a for a in recorded if a[0] == "run"]
    assert len(launched) == 4 and all("--detach" in a for a in launched)
    assert not any(a[0] == "stop" for a in recorded)
    result, recorded = run("stop", EXISTING="1", UNOWNED_CONTAINER="1")
    assert result.returncode == 1 and not any(a[0] == "stop" for a in recorded)
    result, recorded = run("grafana", "logs", "--follow", EXISTING="1", UNOWNED_CONTAINER="1")
    assert result.returncode == 1 and not any(a[0] == "logs" for a in recorded)
    result, recorded = run("grafana", "logs", "--follow", EXISTING="1")
    assert result.returncode == 0 and recorded[-1] == ["logs", "--tail", "100", "--follow", "strix-halo-monitor-grafana"]
    assert not any(a[0] == "stop" for a in recorded)
print("Monitoring ownership, detached startup and rollback policy checks passed.")
