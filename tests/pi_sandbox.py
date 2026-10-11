"""Shared, fail-closed filesystem/process boundary for model-driven coding tests.

Host networking is shared for localhost inference. No network isolation is claimed.
Run this file directly to check the actual Bubblewrap boundary without inference.
"""

from pathlib import Path
import shutil
import subprocess
import tempfile
from unittest.mock import patch

BREW = Path("/home/linuxbrew/.linuxbrew")


def sandbox_command(workspace: Path, agent: Path) -> list[str]:
    if not shutil.which("bwrap") or not BREW.is_dir():
        raise RuntimeError("Coding tests require Bubblewrap and the existing Homebrew installation. No unsandboxed fallback.")
    workspace, agent = workspace.resolve(strict=True), agent.resolve(strict=True)
    if not workspace.is_dir() or not agent.is_dir() or workspace == agent or workspace in agent.parents or agent in workspace.parents:
        raise ValueError("Workspace and temporary agent configuration must be separate directories")
    config_mounts = []
    for file in sorted(agent.iterdir()):
        if file.is_symlink() or not file.is_file():
            raise ValueError(f"Expected a regular temporary configuration file: {file}")
        config_mounts += ["--ro-bind", str(file), f"/agent/{file.name}"]
    return ["bwrap", "--unshare-all", "--share-net", "--die-with-parent", "--new-session",
            "--ro-bind", "/usr", "/usr", "--ro-bind", str(BREW), str(BREW),
            "--symlink", "usr/bin", "/bin", "--symlink", "usr/lib", "/lib",
            "--symlink", "usr/lib", "/lib64", "--proc", "/proc", "--dev", "/dev",
            "--tmpfs", "/tmp", "--dir", "/etc", "--tmpfs", "/home/pi",
            # Pi needs ephemeral auth files and settings locks beside immutable inputs.
            "--bind", str(workspace), "/workspace", "--tmpfs", "/agent", *config_mounts,
            "--chdir", "/workspace", "--clearenv",
            "--setenv", "PATH", f"{BREW}/bin:/usr/bin:/bin",
            "--setenv", "HOME", "/home/pi", "--setenv", "LANG", "C.UTF-8",
            "--setenv", "PI_CODING_AGENT_DIR", "/agent", "--setenv", "PI_OFFLINE", "1",
            "--setenv", "PYTHONDONTWRITEBYTECODE", "1"]


def verify_sandbox(workspace: Path, agent: Path) -> str:
    result = subprocess.run(sandbox_command(workspace, agent) + ["/bin/bash", "-c",
        "test ! -e /home/bogdan && test ! -e /models && test ! -e /var/mnt && "
        "test ! -e /dev/kfd && test -w /workspace && "
        "{ test ! -e /agent/models.json || test ! -w /agent/models.json; } && pi --version"],
        capture_output=True, text=True, timeout=30, check=True)
    return result.stdout.strip()


def self_check() -> None:
    with tempfile.TemporaryDirectory(prefix="pi-sandbox-") as directory:
        root = Path(directory)
        workspace, agent = root / "workspace", root / "agent"
        workspace.mkdir()
        agent.mkdir()
        canary = root / "private-canary"
        canary.write_text("must remain outside the sandbox")
        (agent / "models.json").write_text("{}")
        assert verify_sandbox(workspace, agent)
        probe = """import os
from pathlib import Path
assert not Path(%r).exists()
assert not Path('/workspace/../private-canary').exists()
assert 'SANDBOX_SECRET' not in os.environ
assert Path('/agent/models.json').read_text() == '{}'
try:
    Path('/agent/models.json').write_text('changed')
except OSError:
    pass
else:
    raise AssertionError('Agent settings writable')
Path('/workspace/allowed').write_text('inside')
Path('/agent/runtime-marker').write_text('ephemeral')
""" % str(canary)
        subprocess.run(sandbox_command(workspace, agent) + ["/usr/bin/python", "-c", probe],
                       env={"PATH": "/usr/bin:/bin", "SANDBOX_SECRET": "must-not-leak"}, check=True, timeout=10)
        assert (workspace / "allowed").read_text() == "inside"
        assert canary.read_text() == "must remain outside the sandbox"
        assert (agent / "models.json").read_text() == "{}"
        assert not (agent / "runtime-marker").exists()
        with patch.object(shutil, "which", return_value=None):
            try:
                sandbox_command(workspace, agent)
            except RuntimeError:
                pass
            else:
                raise AssertionError("Missing Bubblewrap allowed a fallback")
    print("Bubblewrap hidden-path, environment, writable-workspace and read-only-settings checks passed.")


if __name__ == "__main__":
    self_check()
