#!/usr/bin/env python3
"""Require real execution of the three offline model tests, with no skipped phases.

Run inside the restricted scanner container. This invokes real pytest and the
existing integration tests; it never supplies replacement models or detectors.
Only fixed outcome labels escape the worker process, including on native-library
output, collection failure, plugin errors, or an incomplete test session.
"""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
TEST_FILE = ROOT / "tests/test_local_dlp_integration.py"
EXPECTED_NODEIDS = (
    "tests/test_local_dlp_integration.py::test_real_model_is_locally_available",
    "tests/test_local_dlp_integration.py::test_real_stack_redacts_email_canary_and_nested_tool_response",
    "tests/test_local_dlp_integration.py::test_real_detector_does_not_silently_return_raw_when_error",
)
PHASES = ["setup", "call", "teardown"]
WORKER_TIMEOUT_SECONDS = 540


class ModelTestEvidence:
    """Collect pytest's actual reports; a zero exit alone is insufficient."""

    def __init__(self):
        self.valid = True
        self.session_starts = 0
        self.collection_finishes = 0
        self.session_finishes = 0
        self.collected = []
        self.reports = {node: [] for node in EXPECTED_NODEIDS}

    def pytest_sessionstart(self, session):
        self.session_starts += 1

    def pytest_collectreport(self, report):
        if report.outcome != "passed":
            self.valid = False

    def pytest_collection_finish(self, session):
        self.collection_finishes += 1
        self.collected = [item.nodeid for item in session.items]

    def pytest_deselected(self, items):
        if items:
            self.valid = False

    def pytest_runtest_logreport(self, report):
        if (report.nodeid not in self.reports or report.when not in PHASES
                or report.outcome != "passed" or hasattr(report, "wasxfail")):
            self.valid = False
            return
        self.reports[report.nodeid].append(report.when)

    def pytest_sessionfinish(self, session, exitstatus):
        self.session_finishes += 1
        if (exitstatus != 0 or session.testscollected != len(EXPECTED_NODEIDS)
                or session.testsfailed != 0):
            self.valid = False

    def passed(self, exit_code):
        return (exit_code == 0 and self.valid
                and self.session_starts == self.collection_finishes == self.session_finishes == 1
                and len(self.collected) == len(EXPECTED_NODEIDS)
                and set(self.collected) == set(EXPECTED_NODEIDS)
                and all(phases == PHASES for phases in self.reports.values()))


def worker():
    # The parent also redirects these descriptors. Keep direct internal-worker
    # invocation quiet, including output emitted below Python's stream objects.
    with open(os.devnull, "wb") as sink:
        os.dup2(sink.fileno(), 1)
        os.dup2(sink.fileno(), 2)
    try:
        import pytest

        evidence = ModelTestEvidence()
        # An empty explicit config prevents repository/user pytest configuration
        # from altering imports, selection, fixtures or test outcomes.
        with tempfile.TemporaryDirectory(prefix="offline-model-pytest-") as directory:
            config = Path(directory) / "pytest.ini"
            config.write_text("[pytest]\n", encoding="utf-8")
            exit_code = pytest.main([
                "-q", "-c", str(config), "-o", "addopts=", "--rootdir", str(ROOT),
                "--noconftest", "-p", "no:cacheprovider", str(TEST_FILE),
            ], plugins=[evidence])
        return 0 if evidence.passed(exit_code) else 2
    except BaseException:
        # pytest/system exits and interrupts cannot substitute for full evidence.
        return 2


def main(argv=None):
    arguments = sys.argv[1:] if argv is None else argv
    if arguments == ["--worker"]:
        return worker()
    if arguments:
        print("Offline model qualification failed", file=sys.stderr)
        return 2
    environment = {key: value for key, value in os.environ.items()
                   if not key.startswith("PYTEST_")}
    environment.update({
        "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1", "PYTHONNOUSERSITE": "1",
        "PYTHONPATH": str(ROOT), "PYTHONOPTIMIZE": "0", "PYTHONDONTWRITEBYTECODE": "1",
    })
    try:
        result = subprocess.run(
            [sys.executable, "-B", str(Path(__file__).resolve()), "--worker"],
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            cwd=ROOT, env=environment, check=False, timeout=WORKER_TIMEOUT_SECONDS,
        )
        passed = result.returncode == 0
    except (OSError, subprocess.SubprocessError):
        passed = False
    if not passed:
        print("Offline model qualification failed", file=sys.stderr)
        return 2
    print("Offline model qualification passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
