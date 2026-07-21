from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = PROJECT_ROOT / "test-results"
JUNIT_PATH = RESULTS_DIR / "junit.xml"
COVERAGE_PATH = RESULTS_DIR / "coverage.xml"
SUMMARY_PATH = RESULTS_DIR / "summary.md"


def main() -> int:
    RESULTS_DIR.mkdir(exist_ok=True)
    command = [
        sys.executable,
        "-m",
        "pytest",
        "-q",
        f"--junitxml={JUNIT_PATH}",
        "--cov=app",
        "--cov-report=term-missing",
        f"--cov-report=xml:{COVERAGE_PATH}",
        *sys.argv[1:],
    ]
    completed = subprocess.run(command, cwd=PROJECT_ROOT, check=False)
    SUMMARY_PATH.write_text(_summary(completed.returncode), encoding="utf-8")
    print(f"Test summary: {SUMMARY_PATH}")
    return completed.returncode


def _summary(exit_code: int) -> str:
    counts: dict[str, int | str] = {
        "tests": "unknown",
        "failures": "unknown",
        "errors": "unknown",
        "skipped": "unknown",
    }
    duration = "unknown"
    if JUNIT_PATH.exists():
        root = ET.parse(JUNIT_PATH).getroot()
        suites = [root] if root.tag == "testsuite" else list(root.findall("testsuite"))
        if suites:
            counts = {
                key: sum(int(suite.attrib.get(key, "0")) for suite in suites)
                for key in counts
            }
            duration = f"{sum(float(suite.attrib.get('time', '0')) for suite in suites):.3f}s"
    status = "passed" if exit_code == 0 else "failed"
    generated_at = datetime.now(timezone.utc).isoformat()
    return (
        "# Test Results\n\n"
        f"- Status: **{status}**\n"
        f"- Generated: `{generated_at}`\n"
        f"- Python: `{sys.version.split()[0]}`\n"
        f"- Tests: `{counts['tests']}`\n"
        f"- Failures: `{counts['failures']}`\n"
        f"- Errors: `{counts['errors']}`\n"
        f"- Skipped: `{counts['skipped']}`\n"
        f"- Duration: `{duration}`\n"
        f"- Exit code: `{exit_code}`\n\n"
        "Detailed results are in `junit.xml`; coverage is in `coverage.xml`.\n"
    )


if __name__ == "__main__":
    raise SystemExit(main())
