"""Coverage and fail-closed controls for the tracked-source SAST wrapper."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import scan_opengrep as scanner  # noqa: E402
import scan_hosted_sast as hosted  # noqa: E402


class TrackedSourceScanTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        subprocess.run(["git", "init", "-q", str(self.root)], check=True, capture_output=True)
        (self.root / ".gitignore").write_text("*.py\n")
        (self.root / ".semgrepignore").write_text("*.py\n")
        (self.root / "private.py").write_text("print('fixture')\n")
        (self.root / "code.rs").write_text("fn main() {}\n")
        (self.root / "notes.txt").write_text("not a supported source\n")
        subprocess.run(["git", "-C", str(self.root), "add", "-f", "."], check=True, capture_output=True)
        self.rules = self.root / "rules.yaml"

    def run_with_report(self, *, findings=(), errors=(), missing=False, exit_code=0, parse_exit=0, skipped=None):
        calls = []
        real_run = subprocess.run

        def fake(command, **kwargs):
            if command[0] in {"git", sys.executable}:
                return real_run(command, **kwargs)
            if "--dump-ast" in command:
                return subprocess.CompletedProcess(command, parse_exit)
            calls.append(command)
            paths = command[command.index("--") + 1:]
            report = {"paths": {"scanned": paths[:-1] if missing else paths},
                      "results": list(findings), "errors": list(errors)}
            if skipped is not None:
                report["paths"]["skipped"] = skipped
            kwargs["stdout"].write(json.dumps(report).encode())
            return subprocess.CompletedProcess(command, exit_code)

        with mock.patch.object(scanner.subprocess, "run", side_effect=fake):
            outcome = scanner.scan(self.root, self.rules, executable="fake-scanner", offline_container=False)
        return outcome, calls

    def test_tracks_ignored_sources_and_bypasses_repository_ignore_rules(self):
        outcome, calls = self.run_with_report()
        self.assertEqual(outcome.status, 0)
        self.assertEqual((outcome.tracked, outcome.scanned), (2, 2))
        self.assertEqual(len(calls), 1)
        self.assertIn("--no-git-ignore", calls[0])
        self.assertIn("--semgrepignore-filename=/dev/null", calls[0])
        self.assertIn("--disable-nosem", calls[0])
        self.assertIn("--max-target-bytes=0", calls[0])
        self.assertIn(str(self.root / "private.py"), calls[0])
        self.assertNotIn(str(self.root / "notes.txt"), calls[0])

    def test_findings_parse_warnings_and_scanner_failures_remain_blocking(self):
        for arguments in ({"findings": [{"message": "private fixture"}]},
                          {"errors": [{"type": "PartialParsing", "level": "warn"}]},
                          {"exit_code": 3}, {"parse_exit": 3}):
            with self.subTest(arguments=arguments):
                outcome, _ = self.run_with_report(**arguments)
                self.assertEqual(outcome.status, 2)

    def test_missing_or_explicitly_skipped_source_is_rejected(self):
        for arguments in ({"missing": True}, {"skipped": [{"reason": "ignored"}]}):
            with self.subTest(arguments=arguments):
                with self.assertRaises(scanner.ScanError):
                    self.run_with_report(**arguments)

    def test_source_symlink_is_rejected(self):
        source = self.root / "private.py"
        source.unlink()
        source.symlink_to(self.root / "notes.txt")
        with self.assertRaises(scanner.ScanError):
            scanner.tracked_sources(self.root, offline_container=False)

    def test_unresolved_lfs_pointer_fails_closed(self):
        (self.root / "private.py").write_text(
            "version https://git-lfs.github.com/spec/v1\n" + "oid sha256:" + "a" * 64 + "\nsize 1\n"
        )
        with self.assertRaises(scanner.ScanError):
            self.run_with_report()

    def test_bare_dotfile_extensions_are_included(self):
        for suffix in scanner.SOURCE_SUFFIXES:
            (self.root / suffix).write_text("fixture\n")
        subprocess.run(["git", "-C", str(self.root), "add", "-f", "."], check=True, capture_output=True)
        paths, _ = scanner.tracked_sources(self.root, offline_container=False)
        self.assertTrue({str(self.root / suffix) for suffix in scanner.SOURCE_SUFFIXES}.issubset(paths))

    def test_materialized_submodule_cannot_be_silently_ignored(self):
        subprocess.run(["git", "-C", str(self.root), "update-index", "--add", "--cacheinfo",
                        "160000," + "1" * 40 + ",nested"], check=True, capture_output=True)
        sources, submodules = scanner.tracked_sources(self.root, offline_container=False)
        self.assertEqual((len(sources), submodules), (2, 1))
        (self.root / "nested").mkdir()
        (self.root / "nested/source.py").write_text("print('fixture')\n")
        with self.assertRaises(scanner.ScanError):
            scanner.tracked_sources(self.root, offline_container=False)

    def test_batches_preserve_the_complete_inventory(self):
        paths = ["/" + "a" * 2000 + str(index) for index in range(100)]
        groups = list(scanner.batches(paths))
        self.assertGreater(len(groups), 1)
        self.assertEqual([path for group in groups for path in group], paths)

    def test_hosted_engines_receive_disjoint_complete_index_partitions(self):
        rust = str(self.root / "code.rs")
        python = str(self.root / "private.py")
        binary = Path("/hosted-sast/semgrep-core")
        rustfmt = Path("/rust-toolchain/bin/rustfmt")
        environment = {"LD_LIBRARY_PATH": "/hosted-sast/libs"}
        clean = scanner.ScanOutcome(1, 1, 0, 0, 0, 0, 0)
        with mock.patch.object(scanner, "scan_paths", return_value=clean) as non_rust, \
                mock.patch.object(hosted.semgrep, "verify_rust_fixtures") as fixtures, \
                mock.patch.object(hosted.semgrep, "verify_syntax") as syntax, \
                mock.patch.object(hosted.semgrep, "scan", return_value=[]) as scan:
            self.assertEqual(hosted.scan(self.root, binary, rustfmt, environment), 0)
            non_rust.assert_called_once_with(self.root, scanner.RULES, [python], 0)
            fixtures.assert_called_once_with(binary, environment)
            syntax.assert_called_once_with(rustfmt, self.root, [rust], {})
            scan.assert_called_once_with(binary, self.root, [rust], environment)
            scan.return_value = [{}]
            self.assertEqual(hosted.scan(self.root, binary, rustfmt, environment), 2)
            scan.return_value = []
            non_rust.return_value = scanner.ScanOutcome(1, 0, 0, 0, 0, 0, 0)
            self.assertEqual(hosted.scan(self.root, binary, rustfmt, environment), 2)


if __name__ == "__main__":
    unittest.main()
