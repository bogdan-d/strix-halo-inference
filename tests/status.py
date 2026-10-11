#!/usr/bin/env python3
"""Check status policy with fields verified against live Podman inspection."""
from contextlib import redirect_stdout
import importlib.util
import io
import json
import os
from pathlib import Path
from unittest.mock import patch
from urllib.error import URLError

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("engine_status", ROOT / "bin/status.py")
status = importlib.util.module_from_spec(spec)
spec.loader.exec_module(status)

container = {
    "ImageName": "publisher/engine@sha256:old-running-image",
    "Image": "running-image-id",
    "State": {"Status": "running", "Running": True},
    "Config": {
        "Labels": {"org.opencontainers.image.version": "old-running-version"},
        "Env": ["HALOGEN_CTX=65536", "HALOGEN_DRAFTER_DEFAULT=0", "HALOGEN_CACHE_DISK_GIB=8"],
        "Cmd": ["gufo", "serve", "--context", "65536", "--speculative", "off",
                "--cache-ram-bytes", "1073741824", "--cache-disk-bytes", "8589934592"],
    },
    "Mounts": [],
}


def inspect_or_logs(*args, **kwargs):
    if args[:2] == ("podman", "inspect"):
        return json.dumps([container])
    return ""


def check(engine, response=None, error=None):
    output = io.StringIO()
    with patch.object(status, "command", side_effect=inspect_or_logs), \
         patch.object(status, "urlopen", return_value=io.BytesIO(json.dumps(response).encode()), side_effect=error), \
         redirect_stdout(output):
        result = status.main(engine, f"strix-halo-{engine}", "http://127.0.0.1/health")
    return result, output.getvalue()


with patch.dict(os.environ, CONTEXT="262144", SPECULATIVE="on"):
    for engine, response in (("halogen", {"status": "ok"}), ("gufo", {"status": "ready"})):
        result, output = check(engine, response)
        assert result == 0, output
        assert "old-running-version" in output and "old-running-image" in output
        assert "Configured context: 65536" in output and "262144" not in output
        assert "Cache disk usage: unavailable" in output
        assert "Engine allocation: unavailable" in output
        assert "startup log, not live" not in output
        assert "pinned weights" in output
    result, output = check("gufo", {"status": "loading"})
    assert result == 1 and "not ready" in output
    result, output = check("gufo", error=URLError("unreachable"))
    assert result == 1 and "Readiness: unavailable" in output
    container["Config"]["Cmd"] = ["--capacity", "65536", "--mtp", "off", "--rope-yarn-factor", "1",
                                  "--prompt-cache-gib", "16", "--prompt-cache-ram-margin-gib", "8",
                                  "--think-nudge", "off", "--low-memory", "fail"]
    result, output = check("strixite", {"status": "ok", "context_length": 65536, "degraded": "cache reduced"})
    assert result == 0 and "Configured context: 65536" in output and "262144" not in output, output
    assert "Configured speculation: off" in output and "Configured YaRN factor: 1" in output
    assert "Cache disk limit: 16 GiB" in output and "Cache RAM margin (not a reservation): 8 GiB" in output
    assert "Degraded settings (health): cache reduced" in output
    result, output = check("strixite", {"status": "error"})
    assert result == 1 and "not ready" in output
    container["State"] = {"Status": "exited", "Running": False}
    result, output = check("gufo", error=AssertionError("Stopped engine must not be probed"))
    assert result == 1 and "engine not active" in output
    with patch.object(status, "command", side_effect=RuntimeError("No such container")), redirect_stdout(io.StringIO()):
        assert status.main("gufo", "missing", "http://127.0.0.1/ready") == 1
print("Status running-configuration, readiness and unavailable-reading checks passed.")
