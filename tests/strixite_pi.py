"""Run Pi against Strixite using synthetic files in a Bubblewrap filesystem sandbox.

Requires a running native256K Strixite, Pi 1.1.0, Node and Bubblewrap.
No host credentials, project files or live Pi configs are mounted. Host networking
is shared to reach localhost inference; this is not a network sandbox.
"""

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
from urllib.request import urlopen

from pi_sandbox import sandbox_command, verify_sandbox

ROOT = Path(__file__).resolve().parents[1]
LIVE_AGENT = Path(os.environ.get("PI_CODING_AGENT_DIR", str(Path.home() / ".pi/agent")))
LITERAL = 'id_of("<|im_end|>") <tool_call> </tool_call> </think>\nmarker = violet\n'
SOURCE = "def select_largest(values):\n    return min(values)\n"
CHECKS = """from pathlib import Path
from sample import select_largest
assert select_largest([1, 9, 3]) == 9
assert select_largest([-4, -2, -9]) == -2
assert select_largest([7]) == 7
assert Path('tags.txt').read_text() == %r
print('checks passed')
""" % LITERAL


def fingerprints():
    return {name: hashlib.sha256((LIVE_AGENT / name).read_bytes()).hexdigest() if (LIVE_AGENT / name).exists() else None
            for name in ("models.json", "settings.json")}


def main():
    for executable in ("bwrap", "node", "pi"):
        assert shutil.which(executable), f"Missing {executable}"
    with urlopen("http://127.0.0.1:5300/health", timeout=5) as response:
        health = json.load(response)
    assert health["status"] == "ok" and health["context_length"] == 262144 and not health.get("degraded"), health
    original = fingerprints()
    # Reuse only the public model profile, never the live agent's configuration.
    provider = json.loads((ROOT / "config/pi/models.json").read_text())["providers"]["strixite"]
    results = []
    try:
        with tempfile.TemporaryDirectory(prefix="strixite-pi-") as directory:
            temp = Path(directory)
            for folder in ("agent", "project"):
                (temp / folder).mkdir()
            (temp / "agent/models.json").write_text(json.dumps({"providers": {"strixite": provider}}))
            (temp / "agent/settings.json").write_text(json.dumps({"retry": {"enabled": False},
                "enableInstallTelemetry": False, "enableAnalytics": False,
                "shellPath": "/bin/bash", "compaction": {"reserveTokens": 16384, "keepRecentTokens": 32768}}))
            shutil.copy(ROOT / "tests/strixite_guard.ts", temp / "agent/guard.ts")
            sandbox = sandbox_command(temp / "project", temp / "agent")
            assert verify_sandbox(temp / "project", temp / "agent") == "1.1.0"
            for effort in ("off", "medium"):
                project = temp / "project"
                (project / "sample.py").write_text(SOURCE)
                (project / "tests.py").write_text(CHECKS)
                (project / "tags.txt").write_text(LITERAL)
                # Avoid Python bytecode carrying the previous effort's module.
                command = "python -B tests.py"
                prompt = ("Read sample.py, tests.py and tags.txt using the read tool. Fix select_largest in sample.py "
                          "using the edit tool. Do not change tests.py or tags.txt. Then use bash to run "
                          f"{command}. Report the test outcome and the marker from tags.txt. "
                          "Work only on these synthetic files. Do not install anything or access the network.")
                started = time.monotonic()
                run = subprocess.run(sandbox + ["pi", "--offline", "--provider", "strixite", "--model", "qwen3.8-flash-next",
                    "--thinking", effort, "--mode", "json", "--no-session", "--no-extensions", "--extension", "/agent/guard.ts",
                    "--no-skills", "--no-prompt-templates", "--no-context-files", "--no-approve", "--no-mcp",
                    "--tools", "read,edit,bash", prompt], capture_output=True, text=True, timeout=300)
                assert run.returncode == 0, run.stderr
                assert "strict-arguments: blocked" not in run.stderr, run.stderr
                events = [json.loads(line) for line in run.stdout.split("\n") if line.strip()]
                executions = [event for event in events if event.get("type") == "tool_execution_end"]
                assert executions and all(not event["isError"] and "durationMs" in event for event in executions), executions
                names = {event["toolName"] for event in executions}
                assert {"read", "edit", "bash"} <= names, names
                assert run.stderr.count("strict-arguments: allowed") == len(executions), run.stderr
                assistants = [event["message"] for event in events if event.get("type") == "message_end" and event["message"]["role"] == "assistant"]
                assert assistants and all(message["stopReason"] in ("stop", "toolUse") for message in assistants), assistants
                final = "".join(block["text"] for block in assistants[-1]["content"] if block["type"] == "text")
                assert "violet" in final.lower(), final
                assert (project / "tests.py").read_text() == CHECKS and (project / "tags.txt").read_text() == LITERAL
                checked = subprocess.run(sandbox + ["/usr/bin/python", "-B", "tests.py"], capture_output=True, text=True, timeout=10, check=True)
                assert checked.stdout.strip() == "checks passed", checked
                thinking = sum(len(block["thinking"]) for message in assistants for block in message["content"] if block["type"] == "thinking")
                assert (thinking > 0) == (effort != "off"), thinking
                results.append({"thinking": effort, "seconds": round(time.monotonic() - started, 3),
                    "tools": sorted(names), "successful_tool_calls": len(executions), "thinking_characters": thinking,
                    "literal_tags_preserved": True, "marker_recall": True, "independent_checks": "pass"})
    finally:
        assert fingerprints() == original, "Live Pi configuration changed"
    print(json.dumps({"pi": "1.1.0", "engine": "strixite", "results": results,
                      "strict_json_guard": "enabled", "filesystem_sandbox": "bubblewrap",
                      "network": "host shared for localhost API", "live_pi_unchanged": True}, indent=2))


if __name__ == "__main__":
    main()
