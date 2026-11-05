"""Netra: run the parser on a Playwright JSON report and print the failures."""
import sys
from netra.parser import load_report, collect_failures

report_path = sys.argv[1] if len(sys.argv) > 1 else "../ajTests/reports/results.json"
report = load_report(report_path)
failures = collect_failures(report)

stats = report.get("stats", {})
print(f"Passed: {stats.get('expected', 0)}  Failed: {stats.get('unexpected', 0)}  Flaky: {stats.get('flaky', 0)}")
for f in failures:
    print(f"- [{f.status}] {f.project} | {f.file} | {f.title}")
    print(f"    {f.error_message}  ({f.error_location})")