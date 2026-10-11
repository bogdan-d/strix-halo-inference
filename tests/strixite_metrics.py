#!/usr/bin/env python3
"""Check Strixite dashboard policy with real promtool and synthetic sequences."""
import json
from pathlib import Path
import subprocess
import tempfile

import dashboard_panels

ROOT = Path(__file__).resolve().parents[1]


def expression(title: str, index: int = 0) -> str:
    return dashboard_panels.expression("strixite", title, index)


def series(name: str, values: str, job: str = "strixite") -> dict[str, str]:
    instance = "127.0.0.1:5300" if job == "strixite" else "127.0.0.1:9115"
    return {"series": name + f'{{job="{job}",instance="{instance}"}}', "values": values}


def check(inputs: list[dict[str, str]], query: str, expected: float | None, job: str = "strixite") -> dict:
    instance = "127.0.0.1:5300" if job == "strixite" else "127.0.0.1:9115"
    samples = [] if expected is None else [{"labels": f'{{job="{job}",instance="{instance}"}}', "value": expected}]
    return {"interval": "10s", "input_series": inputs,
            "promql_expr_test": [{"expr": f"sum without (__name__) ({query})", "eval_time": "1m", "exp_samples": samples}]}


up = series("up", "1+0x6")
speed = series("strix_last_decode_tokens_per_second", "50+0x6")
tests = [
    check([up, series("strix_generated_tokens_total", "0 100 200 300 400 0 100")],
          "(" + expression("Completion-accounted wall-time throughput", 1) + ") > bool 0", 1),
    check([series("up", "0+0x6", "strixite-ready"), series("probe_success", "1+0x6", "strixite-ready")],
          expression("Model readiness"), None, "strixite-ready"),
    check([series("up", "1+0x6", "strixite-ready"), series("probe_success", "0+0x6", "strixite-ready")],
          expression("Model readiness"), 0, "strixite-ready"),
    # Native diagnostics remain visible when readiness fails, but never after scrape failure.
    check([up, series("probe_success", "0+0x6", "strixite-ready"), series("strix_busy", "1+0x6")],
          expression("Execution slot"), 1),
    check([series("up", "0+0x6"), speed], expression("Last qualifying request speed", 1), None),
    check([up, speed, series("strix_busy", "0+0x6")], expression("Last qualifying request speed", 1), 50),
    check([up, series("strix_last_decode_tokens_per_second", "0+0x6")], expression("Last qualifying request speed", 1), None),
    check([up, series("strix_mtp_accepted_tokens_total", "0+0x6"), series("strix_mtp_drafted_tokens_total", "0+0x6")],
          expression("Draft acceptance share"), None),
    check([up, series("strix_prompt_tokens_cached_total", "0+0x6"), series("strix_prompt_tokens_total", "0+0x6")],
          expression("Reused prompt share"), None),
    check([up, series("strix_prompt_tokens_cached_total", "0+5x6"), series("strix_prompt_tokens_total", "0+10x6")],
          expression("Reused prompt share"), 0.5),
    check([up, series("strix_mtp_accepted_tokens_total", "0 50 100 150 200 0 50"),
           series("strix_mtp_drafted_tokens_total", "0 100 200 300 400 0 100")],
          expression("Draft acceptance share"), 0.5),
]
pins = dict(line.split("=", 1) for line in (ROOT / "config/monitoring/pins.env").read_text().splitlines()
            if line and not line.startswith("#"))
with tempfile.TemporaryDirectory(prefix="strixite-promql-") as directory:
    path = Path(directory) / "tests.json"
    path.write_text(json.dumps({"evaluation_interval": "10s", "tests": tests}))
    subprocess.run(["podman", "run", "--rm", "--pull=never", "--network=none", "--read-only",
                    "--cap-drop=all", "--security-opt=no-new-privileges", "--entrypoint=/bin/promtool",
                    "-v", f"{path}:/tests.json:ro", pins["PROMETHEUS_IMAGE"], "test", "rules", "/tests.json"], check=True, timeout=30)
print("Strixite reset, readiness, historical-speed and no-work ratio policies passed.")
