"""Behavioral tests for privacy scans; all identifiers are synthetic fixtures."""

from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import privacy_scan


def _synthetic(parts: tuple[str, ...]) -> str:
    """Build fictional test identifiers without storing complete matches."""
    return "".join(parts)


def _generated_recognizer_vectors() -> tuple[tuple[str, str, str], ...]:
    """Return entity, context and value for deterministic detector test inputs.

    This zero-input factory cannot ingest patient, customer or environment data.
    These values must be written in clear text in disposable Git repositories to
    exercise the real scanner. The bank-format vector uses a fictional TEST bank
    code and an all-zero account; its check digits are generated here. Keeping
    the provenance in this table also avoids representing a synthetic value as
    an application variable that retrieves a real identifier.
    """
    digits = [2, 1, 1, 1, 1, 1, 1, 1]
    checksum = sum(a * b for a, b in zip(digits, [1, 3, 7, 9, 1, 3, 7, 9])) % 10
    bank_format = "TEST" + "0" * 14
    rearranged = bank_format + "GB00"
    expanded = "".join(
        str(ord(char) - 55) if char.isalpha() else char for char in rearranged
    )
    check_digits = 98 - int(expanded) % 97
    return (
        (
            "AU_MEDICARE",
            "Medicare",
            "".join(str(x) for x in digits) + str(checksum) + "1",
        ),
        ("CREDIT_CARD", "Credit card number", "4" + "1" * 15),
        ("IBAN_CODE", "IBAN", f"GB{check_digits:02d}" + bank_format),
        # ACMA's reserved fictional mobile number, in international format.
        # https://www.acma.gov.au/phone-numbers-use-tv-shows-films-and-creative-works
        ("PHONE_NUMBER", "Phone", "+61 " + "491 " + "570 " + "006"),
    )


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


class GitBatchIOTests(GitFixture):
    def test_large_batch_input_and_output_do_not_deadlock(self) -> None:
        # A cat-file-like child may produce output before it has consumed all
        # input. Run in a bounded subprocess so a pipe deadlock cannot stall CI.
        child = (
            "import sys; "
            "sys.stdin.buffer.read(1); "
            "sys.stdout.buffer.write(b'x' * 262144); "
            "sys.stdout.buffer.flush(); "
            "sys.stdin.buffer.read()"
        )
        probe = (
            "import sys; from pathlib import Path; "
            "sys.path.insert(0, sys.argv[1]); import privacy_scan; "
            "child = sys.argv[3]; "
            "privacy_scan.git_command = lambda *args: [sys.executable, '-c', child]; "
            "result = privacy_scan.git(Path(sys.argv[2]), 'batch', "
            "input_data=b'y' * 262144); "
            "assert result == b'x' * 262144"
        )
        result = subprocess.run(
            [
                sys.executable,
                "-I",
                "-c",
                probe,
                str(Path(privacy_scan.__file__).parent),
                str(self.root),
                child,
            ],
            capture_output=True,
            timeout=10,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr.decode())


class ReviewedPrivacyFindingTests(GitFixture):
    def setUp(self) -> None:
        super().setUp()
        self.values = ("FIRST-SYNTHETIC-MATCH", "SECOND-SYNTHETIC-MATCH")
        self.text = " ".join(self.values) + "\n"
        self.path = "data/synthetic.txt"
        self.put(self.path, self.text)
        self.commit()
        self.blob = self.git("rev-parse", "HEAD:" + self.path)
        self.registry = self.root / "trusted-review.json"

        class Recognizer:
            supported_entities = ["PHONE_NUMBER"]

            def analyze(inner_self, *, text, entities, nlp_artifacts):
                return [
                    SimpleNamespace(
                        entity_type="PHONE_NUMBER",
                        start=text.index(value),
                        end=text.index(value) + len(value),
                        score=1,
                    )
                    for value in self.values
                    if value in text
                ]

        self.recognizer = Recognizer()
        self.write_registry(self.blob)
        self.patcher = patch.object(
            privacy_scan, "TRUSTED_PRIVACY_REVIEWS", self.registry, create=True
        )
        self.patcher.start()
        self.addCleanup(self.patcher.stop)

    def entry(self, blob: str) -> dict:
        start = self.text.index(self.values[0])
        return {
            "blob": blob,
            "path": self.path,
            "entity": "PHONE_NUMBER",
            "line": 1,
            "start": start,
            "end": start + len(self.values[0]),
            "value_sha256": hashlib.sha256(self.values[0].encode()).hexdigest(),
            "profile": "repository",
            "reason": "Synthetic match in a temporary behavioral test fixture.",
            "evidence_urls": ["https://github.com/example/project/commit/" + self.blob],
        }

    def write_registry(self, blob: str) -> None:
        self.registry.write_text(
            json.dumps({"schema_version": 1, "findings": [self.entry(blob)]})
        )

    def test_registry_accepts_128_kib_and_rejects_one_extra_byte(self) -> None:
        # Bound the trusted registry even when valid JSON has trailing whitespace.
        raw = self.registry.read_bytes()
        at_limit = raw + b" " * (128 * 1024 - len(raw))
        self.registry.write_bytes(at_limit)
        self.assertEqual(len(privacy_scan.load_privacy_reviews()), 1)
        self.registry.write_bytes(at_limit + b" ")
        with self.assertRaisesRegex(privacy_scan.ScanError, "invalid_privacy_reviews"):
            privacy_scan.load_privacy_reviews()

    def test_reviewed_span_does_not_hide_another_match_on_the_same_line(self) -> None:
        report = privacy_scan.scan_repository(self.root, recognizers=[self.recognizer])
        self.assertEqual(report["reviewed_nonidentifier_count"], 1)
        self.assertEqual(report["blocking_findings"], 1)
        for value in self.values:
            self.assertNotIn(value, json.dumps(report))

    def test_review_does_not_apply_to_changed_blob_sensitive_or_staged_scope(self) -> None:
        report = privacy_scan.scan_repository(
            self.root, profile="sensitive", recognizers=[self.recognizer]
        )
        self.assertEqual(report["blocking_findings"], 2)
        self.put(self.path, self.text + "extra\n")
        report = privacy_scan.scan_repository(
            self.root, staged=True, recognizers=[self.recognizer]
        )
        self.assertEqual(report["blocking_findings"], 2)
        staged_blob = self.git("rev-parse", ":" + self.path)
        self.write_registry(staged_blob)
        report = privacy_scan.scan_repository(
            self.root, staged=True, recognizers=[self.recognizer]
        )
        self.assertEqual(report["blocking_findings"], 2)
        self.commit()
        self.write_registry(self.blob)
        report = privacy_scan.scan_repository(self.root, recognizers=[self.recognizer])
        self.assertEqual(report["blocking_findings"], 2)

    def test_every_identity_mismatch_remains_blocking(self) -> None:
        entry = self.entry(self.blob)
        for field, value in (
            ("blob", "1" * 40),
            ("path", "data/other.txt"),
            ("entity", "AU_TFN"),
            ("line", 2),
            ("start", 1),
            ("end", entry["end"] + 1),
            ("value_sha256", "2" * 64),
        ):
            with self.subTest(field=field):
                self.registry.write_text(
                    json.dumps({"schema_version": 1, "findings": [{**entry, field: value}]})
                )
                report = privacy_scan.scan_repository(
                    self.root, recognizers=[self.recognizer]
                )
                self.assertEqual(report["blocking_findings"], 2)

    def test_consumer_registry_and_environment_cannot_add_reviews(self) -> None:
        target = self.root / "privacy" / "reviewed-privacy-findings.json"
        target.parent.mkdir()
        target.write_bytes(self.registry.read_bytes())
        self.registry.write_text(json.dumps({"schema_version": 1, "findings": []}))
        with patch.dict(os.environ, {"PRIVACY_REVIEWED_FINDINGS": str(target)}):
            report = privacy_scan.scan_repository(
                self.root, recognizers=[self.recognizer]
            )
        self.assertEqual(report["blocking_findings"], 2)

    def test_malformed_and_duplicate_reviews_fail_closed(self) -> None:
        entry = self.entry(self.blob)
        for value in (
            {"schema_version": 1, "findings": [entry, entry]},
            {"schema_version": 1, "findings": [{**entry, "start": True}]},
            {"schema_version": 1, "findings": [{**entry, "path": "../input"}]},
            {"schema_version": 1, "findings": [{**entry, "value_sha256": "*"}]},
            {"schema_version": 1, "findings": [{**entry, "profile": "sensitive"}]},
        ):
            with self.subTest(value=value):
                self.registry.write_text(json.dumps(value))
                with self.assertRaises(privacy_scan.ScanError):
                    privacy_scan.scan_repository(self.root, recognizers=[self.recognizer])


@unittest.skipUnless(HAS_PRESIDIO, "install the isolated Presidio tooling requirements")
class PresidioIntegrationTests(GitFixture):
    def test_real_credit_card_review_keeps_a_neighboring_match_blocking(self) -> None:
        # Public payment-test vectors are generated only in a temporary Git fixture.
        values = ("4" + "1" * 15, "5" * 12 + "4" * 4)
        text = "credit card number: " + values[0] + " credit card number: " + values[1] + "\n"
        path = "data/synthetic-cards.txt"
        self.put(path, text)
        self.commit()
        blob = self.git("rev-parse", "HEAD:" + path)
        recognizer = next(
            item for item in privacy_scan.build_recognizers()
            if "CREDIT_CARD" in item.supported_entities
        )
        matches = [
            item for item in recognizer.analyze(
                text=text, entities=recognizer.supported_entities, nlp_artifacts=None
            )
            if item.score > 0
        ]
        self.assertEqual(len(matches), 2)
        match = matches[0]
        entry = {
            "blob": blob,
            "path": path,
            "entity": "CREDIT_CARD",
            "line": 1,
            "start": match.start,
            "end": match.end,
            "value_sha256": hashlib.sha256(text[match.start:match.end].encode()).hexdigest(),
            "profile": "repository",
            "reason": "Public synthetic payment-test value in a temporary regression fixture.",
            "evidence_urls": ["https://github.com/example/project/commit/" + blob],
        }
        registry = self.root / "trusted-review.json"
        registry.write_text(json.dumps({"schema_version": 1, "findings": [entry]}))
        with patch.object(privacy_scan, "TRUSTED_PRIVACY_REVIEWS", registry):
            report = privacy_scan.scan_repository(self.root, recognizers=[recognizer])
            sensitive = privacy_scan.scan_repository(
                self.root, profile="sensitive", recognizers=[recognizer]
            )
        self.assertEqual(report["reviewed_nonidentifier_count"], 1)
        self.assertEqual(report["blocking_findings"], 1)
        self.assertEqual(sensitive["blocking_findings"], 2)
        for value in values:
            self.assertNotIn(value, json.dumps(report))

    def test_real_phone_review_keeps_an_unreviewed_phone_blocking(self) -> None:
        values = ("+61 " + "491 " + "570 " + "006", "+61 " + "491 " + "570 " + "007")
        text = "\n".join(values) + "\n"
        path = "data/fictional-phones.txt"
        self.put(path, text)
        self.commit()
        blob = self.git("rev-parse", "HEAD:" + path)
        recognizer = next(
            item for item in privacy_scan.build_recognizers()
            if "PHONE_NUMBER" in item.supported_entities
        )
        matches = [
            item for item in recognizer.analyze(
                text=text, entities=recognizer.supported_entities, nlp_artifacts=None
            )
            if item.score > 0
        ]
        self.assertEqual(len(matches), 2)
        match = matches[0]
        reviewed_value = text[match.start:match.end]
        entry = {
            "blob": blob,
            "path": path,
            "entity": "PHONE_NUMBER",
            "line": 1,
            "start": match.start,
            "end": match.end,
            "value_sha256": hashlib.sha256(reviewed_value.encode()).hexdigest(),
            "profile": "repository",
            "reason": "Fictional reserved phone number in a temporary regression fixture.",
            "evidence_urls": ["https://github.com/example/project/commit/" + blob],
        }
        registry = self.root / "trusted-review.json"
        registry.write_text(json.dumps({"schema_version": 1, "findings": [entry]}))
        with patch.object(privacy_scan, "TRUSTED_PRIVACY_REVIEWS", registry):
            report = privacy_scan.scan_repository(self.root, recognizers=[recognizer])
        self.assertEqual(report["reviewed_nonidentifier_count"], 1)
        self.assertEqual(report["blocking_findings"], 1)
        for value in values:
            self.assertNotIn(value, json.dumps(report))

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
        vectors = _generated_recognizer_vectors()
        text = "\n".join(context + ": " + sample for _, context, sample in vectors)
        self.put("records/synthetic.txt", text)
        self.commit()
        code, report, output = self.run_cli()
        self.assertEqual(code, 1)
        entities = {f["entity"] for f in report["findings"]}
        self.assertTrue({entity for entity, _, _ in vectors}.issubset(entities))
        for _, _, sample in vectors:
            self.assertNotIn(sample, output)

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
