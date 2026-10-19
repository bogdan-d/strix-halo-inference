#!/usr/bin/env python3
"""Check bin/cache.sh: it clears only stopped engines' cache contents, keeps the directories and respects the start lock."""
import fcntl
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]

with tempfile.TemporaryDirectory(prefix="strix-cache-") as directory:
    temp = Path(directory)
    commands = temp / "commands"
    commands.mkdir()
    # The engine named in RUNNING has a container; every other one does not.
    (commands / "podman").write_text('#!/bin/sh\n[ "$1 $2" = "container exists" ] && [ "$3" = "strix-halo-$RUNNING" ]\n')
    (commands / "podman").chmod(0o755)
    cache = temp / "cache"
    for engine in ("halogen", "gufo", "strixite"):
        (cache / engine / "nested").mkdir(parents=True)
        (cache / engine / "nested" / "entry").write_bytes(b"x" * 8192)
        (cache / engine / "LOCK").touch()
    (cache / "download-halogen.log").write_text("kept")
    env = dict(os.environ, PATH=f"{commands}:{os.environ['PATH']}", CACHE_ROOT=str(cache), RUNNING="")

    def run(*args: str, **overrides: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run([str(ROOT / "bin/cache.sh"), *args], env=env | overrides, capture_output=True, text=True, timeout=10)

    for args in ((), ("halogen",), ("clear", "halogen"), ("other", "clear"), ("halogen", "clear", "x")):
        assert run(*args).returncode == 2, args
    result = run("all", "status")
    assert result.returncode == 0 and result.stdout.count(str(cache)) == 3, result

    # A running engine refuses the whole request before anything is deleted.
    result = run("all", "clear", RUNNING="gufo")
    assert result.returncode == 1 and "Stop gufo" in result.stderr, result
    assert all(any((cache / engine).iterdir()) for engine in ("halogen", "gufo", "strixite"))
    with open(cache / "start.lock", "a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        result = run("halogen", "clear")
        assert result.returncode == 1 and "start is in progress" in result.stderr, result
    assert any((cache / "halogen").iterdir())

    result = run("halogen", "clear", RUNNING="gufo")
    assert result.returncode == 0 and "halogen: cleared" in result.stdout, result
    assert (cache / "halogen").is_dir() and not any((cache / "halogen").iterdir())
    assert (cache / "gufo/nested/entry").exists() and (cache / "download-halogen.log").read_text() == "kept"
    assert run("all", "clear").returncode == 0
    assert all((cache / engine).is_dir() and not any((cache / engine).iterdir()) for engine in ("halogen", "gufo", "strixite"))
    assert run("all", "status", CACHE_ROOT=os.environ["HOME"]).returncode == 1
print("Cache script checks passed.")
