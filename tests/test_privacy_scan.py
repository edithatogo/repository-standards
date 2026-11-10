"""Behavioral tests for privacy scans; all identifiers are synthetic fixtures."""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import privacy_scan


def _synthetic(parts: tuple[str, ...]) -> str:
    """Build fictional test identifiers without storing complete matches."""
    return "".join(parts)


HAS_PRESIDIO = importlib.util.find_spec("presidio_analyzer") is not None


class GitFixture(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.git("init", "-q")
        self.git("config", "user.name", "Synthetic Fixture")
        self.git("config", "user.email", "fixture@example.invalid")
        self.git(
            "-c",
            "core.hooksPath=/dev/null",
            "commit",
            "--allow-empty",
            "-qm",
            "initial",
        )

    def git(self, *args: str) -> str:
        result = subprocess.run(
            ["git", "-C", str(self.root), *args],
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip()

    def put(self, path: str, text: str | bytes) -> None:
        file = self.root / path
        file.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(text, bytes):
            file.write_bytes(text)
        else:
            file.write_text(text, encoding="utf-8")
        self.git("add", "--", path)

    def commit(self) -> str:
        self.git("-c", "core.hooksPath=/dev/null", "commit", "-qm", "synthetic input")
        return self.git("rev-parse", "HEAD")

    def run_cli(self, *args: str) -> tuple[int, dict, str]:
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = privacy_scan.main(["--root", str(self.root), *args])
        raw = output.getvalue()
        return code, json.loads(raw), raw


@unittest.skipUnless(HAS_PRESIDIO, "install the isolated Presidio tooling requirements")
class PresidioIntegrationTests(GitFixture):
    def test_contextual_australian_identifier_blocks_without_plaintext(self) -> None:
        value = _synthetic(("123", "456", "782"))
        self.put("notes.txt", "tax file number: " + value + "\n")
        self.commit()
        code, report, output = self.run_cli()
        self.assertEqual(code, 1)
        self.assertGreater(report["blocking_findings"], 0)
        self.assertIn("AU_TFN", output)
        self.assertNotIn(value, output)
        self.assertNotIn("tax file number:", output)

    def test_remaining_supported_entities_use_real_recognizers(self) -> None:
        digits = [2, 1, 1, 1, 1, 1, 1, 1]
        checksum = sum(a * b for a, b in zip(digits, [1, 3, 7, 9, 1, 3, 7, 9])) % 10
        medicare = "".join(str(x) for x in digits) + str(checksum) + "1"
        card = "4" + "1" * 15
        iban = _synthetic(("GB82", "WEST", "1234", "5698", "7654", "32"))
        phone = "+61 " + "412 " + "345 " + "678"
        text = (
            "Medicare: "
            + medicare
            + "\nCredit card number: "
            + card
            + "\nIBAN: "
            + iban
            + "\nPhone: "
            + phone
        )
        self.put("records/synthetic.txt", text)
        self.commit()
        code, report, output = self.run_cli()
        self.assertEqual(code, 1)
        entities = {f["entity"] for f in report["findings"]}
        self.assertTrue(
            {"AU_MEDICARE", "CREDIT_CARD", "IBAN_CODE", "PHONE_NUMBER"}.issubset(
                entities
            )
        )
        for value in (medicare, card, iban, phone):
            self.assertNotIn(value, output)

    def test_invalid_australian_checksum_is_not_accepted(self) -> None:
        value = _synthetic(("123", "456", "781"))
        self.put("notes.txt", "TFN: " + value + "\n")
        self.commit()
        code, report, _ = self.run_cli()
        self.assertEqual(code, 0)
        self.assertNotIn("AU_TFN", {f["entity"] for f in report["findings"]})

    def test_public_bibliographic_contact_is_advisory(self) -> None:
        address = "citation.author" + "@" + "example.org"
        self.put("CITATION.cff", "email: " + address + "\n")
        self.commit()
        code, report, output = self.run_cli()
        self.assertEqual(code, 0)
        self.assertEqual(report["blocking_findings"], 0)
        self.assertGreater(report["advisory_findings"], 0)
        self.assertNotIn(address, output)

    def test_email_in_data_path_blocks(self) -> None:
        self.put("datasets/input.csv", "email\n" + "test.person" + "@example.org\n")
        self.commit()
        code, report, _ = self.run_cli()
        self.assertEqual(code, 1)
        self.assertGreater(report["blocking_findings"], 0)

    def test_sensitive_profile_blocks_contact_outside_data_paths(self) -> None:
        self.put("notes.txt", "test.person" + "@example.org\n")
        self.commit()
        code, _, _ = self.run_cli("--profile", "sensitive")
        self.assertEqual(code, 1)

    def test_unformatted_contextless_numeric_match_is_advisory(self) -> None:
        value = _synthetic(("123", "456", "782"))
        self.put("results.csv", "value\n" + value + "\n")
        self.commit()
        code, report, _ = self.run_cli()
        self.assertEqual(code, 0)
        self.assertGreater(report["advisory_findings"], 0)

    def test_committed_blob_not_modified_worktree_is_scanned(self) -> None:
        value = _synthetic(("123", "456", "782"))
        self.put("notes.txt", "TFN: " + value + "\n")
        self.commit()
        (self.root / "notes.txt").write_text("nothing here\n")
        code, _, _ = self.run_cli()
        self.assertEqual(code, 1)

    def test_staged_blob_not_modified_worktree_is_scanned(self) -> None:
        value = _synthetic(("123", "456", "782"))
        self.put("notes.txt", "TFN: " + value + "\n")
        (self.root / "notes.txt").write_text("nothing here\n")
        code, report, _ = self.run_cli("--staged")
        self.assertEqual(code, 1)
        self.assertEqual(report["scope"], "staged")

    def test_staged_scope_ignores_unchanged_index_blobs(self) -> None:
        self.put("datasets/old.csv", "address\n" + "old.person" + "@example.org\n")
        self.commit()
        self.put("new.txt", "no matching identifiers\n")
        code, report, _ = self.run_cli("--staged")
        self.assertEqual(code, 0)
        self.assertEqual(report["files_selected"], 1)

    def test_no_network_call_during_email_detection(self) -> None:
        from unittest.mock import patch

        self.put("CITATION.cff", "email: " + "test.person" + "@example.org\n")
        self.commit()
        with patch(
            "socket.socket.connect", side_effect=AssertionError("network forbidden")
        ):
            code, report, _ = self.run_cli()
        self.assertEqual(code, 0)
        self.assertGreater(report["advisory_findings"], 0)

    def test_diff_scope_ignores_unchanged_files(self) -> None:
        self.put("datasets/old.csv", "address\n" + "old.person" + "@example.org\n")
        base = self.commit()
        self.put("new.txt", "no matching identifiers\n")
        self.commit()
        code, report, _ = self.run_cli("--base", base)
        self.assertEqual(code, 0)
        self.assertEqual(report["files_selected"], 1)
        self.assertEqual(report["files_scanned"], 1)

    def test_chunk_boundary_keeps_identifier_detection(self) -> None:
        value = _synthetic(("123", "456", "782"))
        padding = "x " * (privacy_scan.CHUNK_SIZE // 2 - 4)
        self.put("notes.txt", padding + " TFN: " + value + "\n")
        self.commit()
        code, report, _ = self.run_cli()
        self.assertEqual(code, 1)
        matches = [f for f in report["findings"] if f["entity"] == "AU_TFN"]
        self.assertEqual(sum(f["count"] for f in matches), 1)

    def test_newline_filename_is_json_escaped(self) -> None:
        name = "records/line\n::error::injection.txt"
        self.put(name, "address: " + "test.person" + "@example.org\n")
        self.commit()
        code, report, raw = self.run_cli()
        self.assertEqual(code, 1)
        self.assertEqual(report["findings"][0]["path"], name)
        self.assertNotIn("\n::error::", raw)

    def test_symlink_never_reads_external_target(self) -> None:
        outside = self.root.parent / (self.root.name + "-outside.txt")
        outside.write_text("TFN: " + _synthetic(("123", "456", "782")))
        self.addCleanup(outside.unlink)
        os.symlink(outside, self.root / "reference.txt")
        self.git("add", "reference.txt")
        self.commit()
        code, report, _ = self.run_cli()
        self.assertEqual(code, 0)
        self.assertEqual(report["files_scanned"], 0)
        self.assertFalse(report["coverage_complete"])
        self.assertEqual(report["skipped"][0]["reason"], "symlink")

    def test_submodule_is_reported_without_traversal(self) -> None:
        oid = self.git("rev-parse", "HEAD")
        self.git("update-index", "--add", "--cacheinfo", "160000," + oid + ",nested")
        self.commit()
        code, report, _ = self.run_cli()
        self.assertEqual(code, 0)
        self.assertEqual(report["files_scanned"], 0)
        self.assertFalse(report["coverage_complete"])
        self.assertEqual(report["skipped"][0]["reason"], "submodule")

    def test_isolated_cli_ignores_target_python_import_shadowing(self) -> None:
        (self.root / "presidio_analyzer.py").write_text(
            "raise RuntimeError('ROOT_IMPORT_EXECUTED')\n"
        )
        self.put("README.md", "plain project text\n")
        self.commit()
        env = dict(os.environ, PYTHONPATH=str(self.root))
        result = subprocess.run(
            [
                sys.executable,
                "-I",
                str(Path(privacy_scan.__file__)),
                "--root",
                str(self.root),
            ],
            cwd=self.root,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0)
        self.assertNotIn("ROOT_IMPORT_EXECUTED", result.stdout + result.stderr)
        self.assertEqual(json.loads(result.stdout)["files_scanned"], 1)

    def test_binary_lfs_and_oversized_files_are_visible_skips(self) -> None:
        self.put("input.bin", b"abc\0def")
        self.put("large.txt", b"a" * (privacy_scan.MAX_FILE_BYTES + 1))
        self.put(
            "data.lfs",
            "version https://git-lfs.github.com/spec/v1\noid sha256:"
            + "0" * 64
            + "\nsize 100\n",
        )
        self.commit()
        code, report, _ = self.run_cli()
        self.assertEqual(code, 0)
        self.assertFalse(report["coverage_complete"])
        self.assertEqual(
            {x["reason"] for x in report["skipped"]},
            {"binary", "oversized", "lfs_pointer"},
        )

    def test_skip_report_is_bounded_without_losing_coverage_counts(self) -> None:
        count = privacy_scan.MAX_REPORTED_SKIPS + 2
        for i in range(count):
            (self.root / f"input-{i}.bin").write_bytes(b"abc\0def")
        self.git("add", "--", ".")
        self.commit()
        code, report, _ = self.run_cli()
        self.assertEqual(code, 0)
        self.assertEqual(report["status"], "incomplete")
        self.assertFalse(report["coverage_complete"])
        self.assertEqual(len(report["skipped"]), privacy_scan.MAX_REPORTED_SKIPS)
        self.assertEqual(report["skipped_count"], count)
        self.assertEqual(report["skipped_counts_by_reason"], {"binary": count})
        self.assertEqual(report["skipped_omitted"], 2)

    def test_failure_does_not_print_git_error_or_supplied_argument(self) -> None:
        supplied = "invalid-" + "confidential-argument"
        code, report, output = self.run_cli("--base", supplied)
        self.assertEqual(code, 2)
        self.assertEqual(report["status"], "error")
        self.assertNotIn(supplied, output)

    def test_valid_but_missing_commit_fails_closed(self) -> None:
        code, report, _ = self.run_cli("--base", "a" * 40)
        self.assertEqual(code, 2)
        self.assertEqual(report["status"], "error")

    def test_scan_error_is_sanitized(self) -> None:
        from unittest.mock import patch

        with patch.object(
            privacy_scan, "scan_repository", side_effect=RuntimeError("sensitive-value")
        ):
            code, report, output = self.run_cli()
        self.assertEqual(code, 2)
        self.assertEqual(report["status"], "error")
        self.assertNotIn("sensitive-value", output)

    def test_argument_parser_does_not_echo_invalid_values(self) -> None:
        code, report, output = self.run_cli("--profile", "sensitive-value")
        self.assertEqual(code, 2)
        self.assertEqual(report["status"], "error")
        self.assertNotIn("sensitive-value", output)

    def test_recognizer_warning_fails_closed_without_echo(self) -> None:
        import logging

        class IncompleteRecognizer:
            supported_entities = ("AU_TFN",)

            def analyze(self, **kwargs):
                logging.getLogger("presidio-analyzer").warning("sensitive-value")
                return []

        output = io.StringIO()
        with (
            contextlib.redirect_stderr(output),
            self.assertRaises(privacy_scan.ScanError),
        ):
            privacy_scan.analyze_text(
                "text", "file.txt", [IncompleteRecognizer()], "repository"
            )
        self.assertNotIn("sensitive-value", output.getvalue())


if __name__ == "__main__":
    unittest.main()
