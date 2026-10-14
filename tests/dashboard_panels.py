"""Read the dashboard's panel definitions and compose queries the way the page does."""
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
_page = (ROOT / "config/monitoring/dashboard.html").read_text()
_match = re.search(r'<script type="application/json" id="panels">(.*?)</script>', _page, re.DOTALL)
assert _match, "dashboard.html has no panel definitions"
CONFIG = json.loads(_match.group(1))
SECTIONS = {section["job"]: section for section in [CONFIG["host"], CONFIG["npu"], *CONFIG["engines"]]}


def compose(section: dict, panel: dict, series: dict, expr: str, window: str) -> str:
    name = series.get("gate", panel.get("gate", "live"))
    gate = "" if name == "none" else section["gates"][name]
    body = expr.replace("$__rate_interval", window)
    return f"({body}) {gate}" if gate else body


def expression(job: str, title: str, index: int = 0) -> str:
    section = SECTIONS[job]
    panels = [panel for group in ("status", "tiles", "charts", "extras") for panel in section[group] if panel["title"] == title]
    assert len(panels) == 1, (job, title, len(panels))
    series = panels[0]["series"][index]
    return compose(section, panels[0], series, series["expr"], "1m")
