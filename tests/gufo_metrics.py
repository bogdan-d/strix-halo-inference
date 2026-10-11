#!/usr/bin/env python3
"""Test Gufo dashboard semantics with real promtool and synthetic metric sequences."""
import json
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
dashboard = json.loads((ROOT / "config/monitoring/dashboards/gufo.json").read_text())


def expression(title: str, index: int = 0) -> str:
    panel = next(panel for panel in dashboard["panels"] if panel["title"] == title)
    return panel["targets"][index]["expr"].replace("$__rate_interval", "1m")


def series(name: str, values: str, job: str = "gufo") -> dict[str, str]:
    instance = "127.0.0.1:8080" if job == "gufo" else "127.0.0.1:9115"
    return {"series": name + f'{{job="{job}",instance="{instance}"}}', "values": values}


def check(inputs: list[dict[str, str]], query: str, expected: float | None, job: str = "gufo") -> dict:
    instance = "127.0.0.1:8080" if job == "gufo" else "127.0.0.1:9115"
    samples = [] if expected is None else [{"labels": f'{{job="{job}",instance="{instance}"}}', "value": expected}]
    return {"interval": "10s", "input_series": inputs,
            "promql_expr_test": [{"expr": f"sum without (__name__) ({query})", "eval_time": "1m", "exp_samples": samples}]}


base = [series("up", "1+0x6"), series("up", "1+0x6", "gufo-ready"),
        series("probe_success", "1+0x6", "gufo-ready")]
counter = series("llamacpp:tokens_predicted_total", "0 100 200 300 400 0 100")
tests = [
    check(base + [counter], "(" + expression("Aggregate wall-time throughput", 1) + ") > bool 0", 1),
    # HTTP probe collection success is not model readiness.
    check(base[:2] + [series("probe_success", "0+0x6", "gufo-ready"), counter],
          expression("Token counters, since process start", 2), None),
    check([series("up", "0+0x6", "gufo-ready"), series("probe_success", "1+0x6", "gufo-ready")],
          expression("Model readiness"), None, "gufo-ready"),
    check([series("up", "1+0x6", "gufo-ready"), series("probe_success", "0+0x6", "gufo-ready")],
          expression("Model readiness"), 0, "gufo-ready"),
    check(base[1:] + [series("up", "0+0x6"), counter], expression("Token counters, since process start", 2), None),
    # Latest positive speed must remain historical while idle, not be differentiated as a counter.
    check(base + [series("llamacpp:predicted_tokens_seconds", "50+0x6"),
                  series("llamacpp:requests_processing", "0+0x6")],
          expression("Latest positive request processing speed", 1), 50),
    check(base + [series("llamacpp:predicted_tokens_seconds", "0+0x6")],
          expression("Latest positive request processing speed", 1), None),
    check(base + [series("llamacpp:n_tokens_max", "100 150 150 150 150 150 150")],
          expression("Largest completed sequence, since process start"), 150),
    check(base + [series("llamacpp:spec_decode_num_accepted_tokens_total", "0+0x6"),
                  series("llamacpp:spec_decode_num_draft_tokens_total", "0+0x6")],
          expression("Draft acceptance share"), None),
    check(base + [series("llamacpp:prompt_tokens_cached_total", "0+0x6"),
                  series("llamacpp:prompt_tokens_total", "0+0x6")],
          expression("Approximate windowed reused-token share"), None),
]
pins = dict(line.split("=", 1) for line in (ROOT / "config/monitoring/pins.env").read_text().splitlines() if line and not line.startswith("#"))
with tempfile.TemporaryDirectory(prefix="gufo-promql-") as directory:
    path = Path(directory) / "tests.json"
    path.write_text(json.dumps({"evaluation_interval": "10s", "tests": tests}))
    subprocess.run(["podman", "run", "--rm", "--pull=never", "--network=none", "--read-only",
                    "--cap-drop=all", "--security-opt=no-new-privileges", "--entrypoint=/bin/promtool",
                    "-v", f"{path}:/tests.json:ro", pins["PROMETHEUS_IMAGE"], "test", "rules", "/tests.json"], check=True, timeout=30)
print("Gufo reset, readiness, historical-speed and idle-window policies passed.")
