"""Orchestration-only tests; simulated pytest hooks never qualify a real model."""
from __future__ import annotations

import importlib.util
import contextlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock


REPO = Path(__file__).resolve().parents[1]
HELPER = REPO / "security/offline-ai/scripts/qualify_model.py"
SPEC = importlib.util.spec_from_file_location("qualify_model", HELPER)
qualification = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(qualification)
EXPECTED = (
    "tests/test_local_dlp_integration.py::test_real_model_is_locally_available",
    "tests/test_local_dlp_integration.py::test_real_stack_redacts_email_canary_and_nested_tool_response",
    "tests/test_local_dlp_integration.py::test_real_detector_does_not_silently_return_raw_when_error",
)
CANARY = "SYNTHETIC_PRIVATE_MODEL_OUTPUT"


def complete(evidence, *, nodeids=EXPECTED, replace=None,
             first_phases=("setup", "call", "teardown"), final_counts=None, exitstatus=0):
    session = SimpleNamespace(items=[SimpleNamespace(nodeid=node) for node in nodeids],
                              testscollected=len(nodeids), testsfailed=0)
    evidence.pytest_sessionstart(session)
    evidence.pytest_collectreport(SimpleNamespace(outcome="passed"))
    evidence.pytest_collection_finish(session)
    for node in nodeids:
        for phase in first_phases if node == EXPECTED[0] else ("setup", "call", "teardown"):
            report = SimpleNamespace(nodeid=node, when=phase, outcome="passed")
            evidence.pytest_runtest_logreport(replace(report) if replace else report)
    if final_counts is not None:
        session.testscollected, session.testsfailed = final_counts
    evidence.pytest_sessionfinish(session, exitstatus)
    return evidence


class ModelEvidenceTests(unittest.TestCase):
    def test_requires_all_three_exact_tests_and_every_phase(self):
        evidence = complete(qualification.ModelTestEvidence())
        self.assertEqual(tuple(qualification.EXPECTED_NODEIDS), EXPECTED)
        self.assertTrue(evidence.passed(0))
        self.assertFalse(evidence.passed(1))

    def test_zero_exit_without_execution_is_not_qualification(self):
        self.assertFalse(qualification.ModelTestEvidence().passed(0))

    def test_missing_extra_duplicate_or_renamed_tests_fail(self):
        for nodeids in ((), EXPECTED[:2], (*EXPECTED, "unexpected.py::test_other"),
                        (*EXPECTED[:2], EXPECTED[0]),
                        (*EXPECTED[:2], EXPECTED[2] + "[parameter]")):
            with self.subTest(nodeids=nodeids):
                self.assertFalse(complete(qualification.ModelTestEvidence(), nodeids=nodeids).passed(0))

    def test_failed_or_skipped_setup_call_or_teardown_fails(self):
        for phase in ("setup", "call", "teardown"):
            for outcome in ("failed", "skipped"):
                def replace(report):
                    if report.nodeid == EXPECTED[0] and report.when == phase:
                        report.outcome = outcome
                    return report
                with self.subTest(phase=phase, outcome=outcome):
                    self.assertFalse(complete(qualification.ModelTestEvidence(), replace=replace).passed(0))

    def test_xpass_and_xfail_are_not_qualified_passes(self):
        def replace(report):
            report.wasxfail = "synthetic expected failure"
            return report
        self.assertFalse(complete(qualification.ModelTestEvidence(), replace=replace).passed(0))

    def test_missing_duplicate_out_of_order_or_unknown_phase_fails(self):
        for phases in (("setup", "call"), ("call", "setup", "teardown"),
                       ("setup", "call", "call", "teardown"),
                       ("setup", "call", "unknown")):
            evidence = complete(qualification.ModelTestEvidence(), first_phases=phases)
            with self.subTest(phases=phases):
                self.assertFalse(evidence.passed(0))

    def test_collection_failure_skip_deselection_or_extra_session_fails(self):
        for event in ("failed", "skipped", "deselected", "session"):
            evidence = complete(qualification.ModelTestEvidence())
            if event in ("failed", "skipped"):
                evidence.pytest_collectreport(SimpleNamespace(outcome=event))
            elif event == "deselected":
                evidence.pytest_deselected([SimpleNamespace(nodeid=EXPECTED[0])])
            else:
                evidence.pytest_sessionstart(SimpleNamespace())
            with self.subTest(event=event):
                self.assertFalse(evidence.passed(0))

    def test_session_error_or_changed_final_counts_fails(self):
        for count, failed, exitstatus in ((2, 0, 0), (3, 1, 0), (3, 0, 2)):
            evidence = complete(qualification.ModelTestEvidence(), final_counts=(count, failed),
                                exitstatus=exitstatus)
            with self.subTest(count=count, failed=failed, exitstatus=exitstatus):
                self.assertFalse(evidence.passed(0))


class WorkerFailureTests(unittest.TestCase):
    def test_worker_timeout_start_failure_and_nonzero_exit_never_leak_output(self):
        cases = (
            subprocess.TimeoutExpired(CANARY, 1, output=CANARY, stderr=CANARY),
            OSError(CANARY),
            SimpleNamespace(returncode=19),
        )
        for result in cases:
            stdout, stderr = io.StringIO(), io.StringIO()
            options = {"side_effect": result} if isinstance(result, Exception) else {"return_value": result}
            with self.subTest(result=type(result).__name__), \
                    mock.patch.object(qualification.subprocess, "run", **options), \
                    contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                code = qualification.main([])
            self.assertEqual(code, 2)
            self.assertEqual(stdout.getvalue(), "")
            self.assertEqual(stderr.getvalue(), "Offline model qualification failed\n")


class ModelWrapperTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        scripts = self.root / "scripts"
        scripts.mkdir()
        self.helper = scripts / "qualify_model.py"
        shutil.copyfile(HELPER, self.helper)
        self.record = self.root / "simulated-pytest.json"
        tests = self.root / "tests"
        tests.mkdir()
        (tests / "test_local_dlp_integration.py").write_text("# Not executed by simulated pytest.\n")
        # This subprocess fixture exercises dispatch and output suppression only.
        (scripts / "pytest.py").write_text(r'''
import json, os, sys
from pathlib import Path
from types import SimpleNamespace

def main(args, plugins):
    print("SYNTHETIC_PRIVATE_MODEL_OUTPUT")
    print("SYNTHETIC_PRIVATE_MODEL_OUTPUT", file=sys.stderr)
    os.write(1, b"SYNTHETIC_PRIVATE_MODEL_OUTPUT\n")
    os.write(2, b"SYNTHETIC_PRIVATE_MODEL_OUTPUT\n")
    Path(os.environ["SIMULATION_RECEIPT"]).write_text(json.dumps({
        "args": args,
        "autoload": os.environ.get("PYTEST_DISABLE_PLUGIN_AUTOLOAD"),
        "addopts": os.environ.get("PYTEST_ADDOPTS"),
        "plugins": os.environ.get("PYTEST_PLUGINS"),
    }))
    mode = os.environ.get("SIMULATION_MODE", "complete")
    if mode == "exception":
        raise RuntimeError("SYNTHETIC_PRIVATE_MODEL_OUTPUT")
    if mode == "no-tests":
        return 0
    evidence = plugins[0]
    nodes = [
        "tests/test_local_dlp_integration.py::test_real_model_is_locally_available",
        "tests/test_local_dlp_integration.py::test_real_stack_redacts_email_canary_and_nested_tool_response",
        "tests/test_local_dlp_integration.py::test_real_detector_does_not_silently_return_raw_when_error",
    ]
    session = SimpleNamespace(items=[SimpleNamespace(nodeid=node) for node in nodes],
                              testscollected=3, testsfailed=0)
    evidence.pytest_sessionstart(session)
    evidence.pytest_collectreport(SimpleNamespace(outcome="passed"))
    evidence.pytest_collection_finish(session)
    for node in nodes:
        for phase in ("setup", "call", "teardown"):
            evidence.pytest_runtest_logreport(SimpleNamespace(nodeid=node, when=phase,
                outcome="skipped" if mode == "skipped" and phase == "call" else "passed"))
    evidence.pytest_sessionfinish(session, 0)
    return 0
''', encoding="utf-8")

    def invoke(self, mode="complete", *args):
        environment = dict(os.environ, SIMULATION_RECEIPT=str(self.record),
                           SIMULATION_MODE=mode, PYTEST_ADDOPTS="--collect-only -k nothing",
                           PYTEST_PLUGINS="synthetic_untrusted_plugin", PYTEST_DISABLE_PLUGIN_AUTOLOAD="0")
        return subprocess.run([sys.executable, str(self.helper), *args], env=environment,
                              capture_output=True, text=True, timeout=15)

    def test_complete_simulation_reports_only_fixed_success_and_ignores_extra_options(self):
        result = self.invoke()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "Offline model qualification passed\n")
        self.assertEqual(result.stderr, "")
        self.assertNotIn(CANARY, result.stdout + result.stderr)
        record = json.loads(self.record.read_text())
        self.assertEqual(record["autoload"], "1")
        self.assertIsNone(record["addopts"])
        self.assertIsNone(record["plugins"])
        self.assertIn("--noconftest", record["args"])
        self.assertIn("addopts=", record["args"])
        self.assertEqual(record["args"][-1], str(self.root / "tests/test_local_dlp_integration.py"))

    def test_unexecuted_skipped_or_exception_sessions_report_only_fixed_failure(self):
        for mode in ("no-tests", "skipped", "exception"):
            with self.subTest(mode=mode):
                result = self.invoke(mode)
                self.assertEqual(result.returncode, 2)
                self.assertEqual(result.stdout, "")
                self.assertEqual(result.stderr, "Offline model qualification failed\n")
                self.assertNotIn(CANARY, result.stdout + result.stderr)

    def test_extra_cli_options_cannot_change_the_test_selection(self):
        result = self.invoke("complete", "--collect-only")
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stderr, "Offline model qualification failed\n")
        self.assertFalse(self.record.exists())


if __name__ == "__main__":
    unittest.main()
