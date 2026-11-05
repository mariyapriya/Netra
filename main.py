"""Netra: read a Playwright JSON report, classify every failure, print a summary and write an HTML report."""
import sys
from netra.parser import load_report, collect_failures
from netra.classifier import classify
from netra.report import write_html

report_path = sys.argv[1] if len(sys.argv) > 1 else "../ajTests/reports/results.json"
report = load_report(report_path)
classified = [(f, classify(f)) for f in collect_failures(report)]

stats = report.get("stats", {})
print(f"Passed: {stats.get('expected', 0)}  Failed: {stats.get('unexpected', 0)}  Flaky: {stats.get('flaky', 0)}")
for f, verdict in classified:
    print(f"- {verdict.category.upper()} ({verdict.confidence}) | {f.project} | {f.title}")
    print(f"    {f.error_message}  ({f.error_location})")
    print(f"    evidence: {verdict.evidence}")

html_path = write_html(report, classified, "reports/netra-report.html")
print(f"\nHTML report: {html_path.resolve()}")
