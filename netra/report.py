"""Writes the classified failures as a single, self-contained HTML page (no external files or services)."""
from datetime import datetime
from html import escape
from pathlib import Path

from netra.classifier import Verdict, FLAKY, ENVIRONMENT, TEST_CODE, PRODUCT_BUG, UNKNOWN
from netra.parser import Failure

# Most important first: a product bug needs attention before anything else.
ORDER = [PRODUCT_BUG, TEST_CODE, ENVIRONMENT, FLAKY, UNKNOWN]
COLOURS = {
    PRODUCT_BUG: "#c62828", TEST_CODE: "#ef6c00", ENVIRONMENT: "#6a1b9a",
    FLAKY: "#f9a825", UNKNOWN: "#546e7a",
}
ADVICE = {
    PRODUCT_BUG: "Check the application change. Raise a bug with the evidence below.",
    TEST_CODE: "Fix the test: the locator or test logic no longer matches the application.",
    ENVIRONMENT: "Check the test environment (server, network) before looking at the tests.",
    FLAKY: "Find the root cause (timing, shared data). Quarantine with an owner if it repeats.",
    UNKNOWN: "No rule matched. Investigate manually and consider adding a new rule.",
}

STYLE = """
body { font-family: -apple-system, 'Segoe UI', Arial, sans-serif; margin: 32px auto; max-width: 980px; padding: 0 20px; color: #1a1a1a; background: #fafafa; }
h1 { margin: 0; font-size: 26px; } .sub { color: #666; margin: 4px 0 24px; }
.cards { display: flex; flex-wrap: wrap; gap: 12px; margin-bottom: 28px; }
.card { background: #fff; border-radius: 10px; padding: 14px 18px; min-width: 120px; box-shadow: 0 1px 3px rgba(0,0,0,.08); }
.card .n { font-size: 26px; font-weight: 700; } .card .l { font-size: 13px; color: #555; }
.failure { background: #fff; border-radius: 10px; padding: 16px 20px; margin-bottom: 14px; box-shadow: 0 1px 3px rgba(0,0,0,.08); }
.badge { display: inline-block; color: #fff; font-size: 12px; font-weight: 700; padding: 3px 10px; border-radius: 12px; text-transform: uppercase; }
.conf { font-size: 12px; color: #555; margin-left: 8px; }
.title { font-weight: 600; margin: 10px 0 4px; } .meta { font-size: 13px; color: #666; }
.evidence { background: #f3f5f9; border-radius: 6px; padding: 8px 12px; margin: 10px 0; font-family: Menlo, monospace; font-size: 13px; }
.advice { font-size: 13px; } details { margin-top: 8px; font-size: 13px; } pre { white-space: pre-wrap; font-size: 12px; background: #f6f6f6; padding: 10px; border-radius: 6px; }
img { max-width: 100%; border-radius: 6px; margin-top: 8px; border: 1px solid #ddd; }
.ok { background: #e8f5e9; border-radius: 10px; padding: 16px 20px; }
"""


def _card(number: int, label: str, colour: str = "#1a1a1a") -> str:
    return f'<div class="card"><div class="n" style="color:{colour}">{number}</div><div class="l">{escape(label)}</div></div>'


def _failure_html(failure: Failure, verdict: Verdict) -> str:
    colour = COLOURS[verdict.category]
    screenshots = [p for p in failure.attachments if p.endswith(".png")]
    traces = [p for p in failure.attachments if p.endswith(".zip")]
    extras = ""
    if screenshots:
        extras += f'<details><summary>Screenshot</summary><img src="{Path(screenshots[0]).as_uri()}" alt="screenshot"></details>'
    if traces:
        extras += f'<details><summary>Trace</summary><pre>npx playwright show-trace "{escape(traces[0])}"</pre></details>'
    return f"""
<div class="failure">
  <span class="badge" style="background:{colour}">{escape(verdict.category)}</span><span class="conf">confidence: {escape(verdict.confidence)}</span>
  <div class="title">{escape(failure.title)}</div>
  <div class="meta">{escape(failure.project)} &middot; {escape(failure.error_location)} &middot; {failure.attempts} attempt(s)</div>
  <div class="evidence">{escape(verdict.evidence)}</div>
  <div class="advice"><strong>Next step:</strong> {escape(ADVICE[verdict.category])}</div>
  <details><summary>Full error</summary><pre>{escape(failure.error_text)}</pre></details>
  {extras}
</div>"""


def write_html(report: dict, classified: list[tuple[Failure, Verdict]], output: str) -> Path:
    """Build the HTML page and save it. Returns the path of the file."""
    stats = report.get("stats", {})
    counts = {c: sum(1 for _, v in classified if v.category == c) for c in ORDER}
    cards = _card(stats.get("expected", 0), "passed", "#2e7d32") + "".join(
        _card(counts[c], c, COLOURS[c]) for c in ORDER if counts[c]
    )
    ordered = sorted(classified, key=lambda pair: ORDER.index(pair[1].category))
    body = "".join(_failure_html(f, v) for f, v in ordered) or '<div class="ok">All tests passed. Nothing to analyse.</div>'
    started = stats.get("startTime", "")[:16].replace("T", " ")
    page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Netra report</title><style>{STYLE}</style></head>
<body><h1>Netra report</h1>
<p class="sub">Test run started {escape(started)} UTC &middot; report created {datetime.now():%Y-%m-%d %H:%M}</p>
<div class="cards">{cards}</div>{body}</body></html>"""
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(page, encoding="utf-8")
    return path
