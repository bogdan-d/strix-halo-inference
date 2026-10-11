#!/usr/bin/env python3
"""Use real promtool to check dashboard reset, freshness and availability policy."""
import json
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
dashboard = json.loads((ROOT / "config/monitoring/dashboards/halogen.json").read_text())


def expression(title: str, index: int = 0) -> str:
    panel = next(panel for panel in dashboard["panels"] if panel["title"] == title)
    return panel["targets"][index]["expr"].replace("$__rate_interval", "1m")


def series(name: str, values: str) -> dict[str, str]:
    return {"series": name + '{job="halogen",instance="127.0.0.1:8731"}', "values": values}


def check(inputs: list[dict[str, str]], query: str, expected: float | None) -> dict:
    samples = [] if expected is None else [{"labels": '{job="halogen",instance="127.0.0.1:8731"}', "value": expected}]
    return {"interval": "10s", "input_series": inputs,
            "promql_expr_test": [{"expr": f"sum without (__name__) ({query})", "eval_time": "1m", "exp_samples": samples}]}


base = [series("up", "1+0x6"), series("halogen:engine_up", "1+0x6")]
counter = series("llamacpp:tokens_predicted_total", "0 100 200 300 400 0 100")
tests = [
    # Restart must not become negative throughput or a broken speed ratio.
    check(base + [counter], "(" + expression("Aggregate wall-time throughput", 1) + ") > bool 0", 1),
    check(base + [counter, series("llamacpp:tokens_predicted_seconds_total", "0 1 2 3 4 0 1")],
          expression("Processing speed over completed requests", 1), 100),
    # Reachable HTTP is insufficient if the engine probe says no.
    check([series("up", "1+0x6"), series("halogen:engine_up", "0+0x6"), counter],
          expression("Aggregate wall-time throughput", 1), None),
    check([series("up", "0+0x6"), series("halogen:engine_up", "1+0x6"), counter],
          expression("Token counters, since front-end start", 2), None),
    check([series("up", "1+0x6"), series("halogen:engine_up", "0+0x6")], expression("Engine probe"), 0),
    # Idle processing windows and no draft proposals must not show NaN or zero speed.
    check(base + [series("llamacpp:tokens_predicted_total", "0+0x6"),
                  series("llamacpp:tokens_predicted_seconds_total", "0+0x6")],
          expression("Processing speed over completed requests", 1), None),
    check(base + [series("halogen:draft_tokens_total", "0+0x6"),
                  series("halogen:draft_tokens_accepted_total", "0+0x6")],
          expression("Draft acceptance share"), None),
    check(base + [series("halogen:cache_stats_age_seconds", "20+0x6"),
                  series("halogen:cache_entries", "7+0x6")],
          expression("Cache entries, fresh snapshot"), None),
    check(base + [series("halogen:cache_stats_age_seconds", "2+0x6"),
                  series("halogen:cache_entries", "7+0x6")],
          expression("Cache entries, fresh snapshot"), 7),
]
pins = dict(line.split("=", 1) for line in (ROOT / "config/monitoring/pins.env").read_text().splitlines() if line and not line.startswith("#"))
with tempfile.TemporaryDirectory(prefix="halogen-promql-") as directory:
    path = Path(directory) / "tests.json"
    path.write_text(json.dumps({"evaluation_interval": "10s", "tests": tests}))
    subprocess.run(["podman", "run", "--rm", "--pull=never", "--network=none", "--read-only",
                    "--cap-drop=all", "--security-opt=no-new-privileges", "--entrypoint=/bin/promtool",
                    "-v", f"{path}:/tests.json:ro", pins["PROMETHEUS_IMAGE"], "test", "rules", "/tests.json"], check=True, timeout=30)
print("Halogen reset, stale-cache, idle-window and availability policies passed.")
