"""Classifies each failure as flaky, environment problem, test-code error or product bug.

Deterministic rules first: every verdict comes with the evidence (the line in the
error) that led to it, so a person can check the reasoning. When no rule matches,
the verdict is "needs investigation" instead of a guess.
"""
import re
from dataclasses import dataclass

from netra.parser import Failure

FLAKY = "flaky"
ENVIRONMENT = "environment problem"
TEST_CODE = "test-code error"
PRODUCT_BUG = "product bug"
UNKNOWN = "needs investigation"

ENVIRONMENT_PATTERNS = [
    r"net::ERR_[A-Z_]+",                 # browser could not reach the server
    r"ECONNREFUSED|ECONNRESET|ETIMEDOUT",
    r"\b(502|503|504)\b",                # gateway / service unavailable
]
TEST_CODE_PATTERNS = [
    r"strict mode violation",                       # locator matches several elements
    r"(TypeError|ReferenceError|SyntaxError):",     # bug in the test code itself
]


@dataclass
class Verdict:
    category: str
    confidence: str   # high / medium / low
    evidence: str     # the exact part of the error that supports the verdict


def _find(patterns: list[str], text: str) -> str | None:
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(0)
    return None


def _line(text: str, starts_with: str) -> str | None:
    for line in text.splitlines():
        if line.strip().startswith(starts_with):
            return line.strip()
    return None


def classify(failure: Failure) -> Verdict:
    text = failure.error_text

    # 1. Flaky: Playwright reports "flaky" when a test failed and then passed on retry.
    if failure.status == "flaky":
        return Verdict(FLAKY, "high", f"failed, then passed on retry ({failure.attempts} attempts)")

    # 2. Environment: the browser could not reach the application at all.
    hit = _find(ENVIRONMENT_PATTERNS, text)
    if hit:
        return Verdict(ENVIRONMENT, "high", hit)

    # 3. Test-code error: the test itself is broken.
    hit = _find(TEST_CODE_PATTERNS, text)
    if hit:
        return Verdict(TEST_CODE, "high", hit)
    # An action timed out while waiting for an element that never appeared:
    # the page loaded, but the locator matches nothing - usually an outdated locator.
    if "TimeoutError" in text and "locator resolved to" not in text:
        waiting = _line(text, "- waiting for") or failure.error_message
        return Verdict(TEST_CODE, "medium", waiting)

    # 4. Product bug: the element exists, but shows the wrong value.
    expected, received = _line(text, "Expected:"), _line(text, "Received:")
    if expected and received and "locator resolved to" in text:
        return Verdict(PRODUCT_BUG, "medium", f"{expected} / {received}")

    # 5. No rule matched: say so instead of guessing.
    return Verdict(UNKNOWN, "low", failure.error_message)