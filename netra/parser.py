"""Reads a Playwright JSON report and extracts the failure details (failure metadata)."""
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

ANSI = re.compile(r"\x1b\[[0-9;]*m")  # terminal colour codes inside Playwright error messages


def clean(text: str) -> str:
    """Remove colour codes so the text is readable and easy to analyse."""
    return ANSI.sub("", text or "").strip()


@dataclass
class Failure:
    """One failed (or flaky) test, with everything needed to understand it."""
    file: str              # spec file, e.g. cart.spec.ts
    title: str             # full test name: describe > test
    project: str           # browser project, e.g. chromium
    status: str            # "unexpected" (failed) or "flaky" (failed, then passed on retry)
    attempts: int          # how many times it ran (1 = no retry)
    error_message: str     # first line of the error
    error_location: str    # file:line where it failed
    error_text: str        # full cleaned error message (used by the classifier)
    duration_ms: float     # duration of the last attempt
    attachments: list = field(default_factory=list)  # screenshot / trace / video paths


def load_report(path: str) -> dict:
    """Load the Playwright JSON report from disk."""
    return json.loads(Path(path).read_text(encoding="utf-8"))


def collect_failures(report: dict) -> list[Failure]:
    """Walk through all suites and return every failed or flaky test."""
    failures: list[Failure] = []
    for suite in report.get("suites", []):
        _walk(suite, parents=[], failures=failures)
    return failures


def _walk(suite: dict, parents: list[str], failures: list[Failure]) -> None:
    """Visit one suite: check its specs, then visit its inner suites (recursion)."""
    path = parents + ([suite["title"]] if suite.get("title") else [])
    for spec in suite.get("specs", []):
        for test in spec.get("tests", []):
            if test["status"] in ("unexpected", "flaky"):
                failures.append(_to_failure(spec, test, path))
    for inner in suite.get("suites", []):
        _walk(inner, path, failures)


def _to_failure(spec: dict, test: dict, path: list[str]) -> Failure:
    """Turn one Playwright test entry into a Failure."""
    results = test["results"]
    failed = next((r for r in results if r["status"] != "passed"), results[-1])
    error = failed["errors"][0] if failed.get("errors") else {}
    location = error.get("location", {})
    return Failure(
        file=spec["file"],
        title=" > ".join(path[1:] + [spec["title"]]),   # path[0] is the file name
        project=test["projectName"],
        status=test["status"],
        attempts=len(results),
        error_message=(clean(error.get("message")).splitlines() or [""])[0],
        error_location=f'{Path(location.get("file", "?")).name}:{location.get("line", "?")}',
        error_text=clean(error.get("message")),
        duration_ms=results[-1]["duration"],
        attachments=[a["path"] for a in failed.get("attachments", []) if a.get("path")],
    )