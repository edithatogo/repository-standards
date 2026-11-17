"""Behavioral tests: secret withholding, fail-closed errors and commit coverage."""

from __future__ import annotations

import contextlib
import hashlib
import io
import json
import os
import shlex
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import secrets_scan as scanner


class RepositoryCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="test-secrets-")
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.root = self.directory / "repo"
        self.root.mkdir()
        self.config = self.directory / "trusted.toml"
        self.config.write_text("[extend]\nuseDefault = true\n", encoding="utf-8")
        self.git("init", "--quiet")
        self.git("config", "user.name", "Synthetic Test")
        self.git("config", "user.email", "fixture@example.invalid")
        self.git("config", "commit.gpgSign", "false")
        (self.root / "README.md").write_text(
            "Synthetic regression fixture.\n", encoding="utf-8"
        )
        self.git("add", "README.md")
        self.git("commit", "--quiet", "-m", "Initial fixture")
        self.base = self.git("rev-parse", "HEAD")

    def git(self, *args: str) -> str:
        result = subprocess.run(
            ["git", "-C", str(self.root), *args],
            capture_output=True,
            check=True,
            env={
                **os.environ,
                "GIT_CONFIG_GLOBAL": os.devnull,
                "GIT_CONFIG_NOSYSTEM": "1",
            },
        )
        return result.stdout.decode().strip()

    def fake_binary(self, report: object, code: int = 0, *, noisy: bool = False) -> str:
        path = self.directory / "fake-gitleaks"
        noise = (
            "print('PRIVATE_SCANNER_STDOUT')\n"
            "print('PRIVATE_SCANNER_STDERR', file=sys.stderr)\n"
            if noisy else ""
        )
        path.write_text(
            f"#!{sys.executable}\n"
            "import json, pathlib, sys\n"
            + noise
            + "target = pathlib.Path(sys.argv[sys.argv.index('--report-path') + 1])\n"
            f"target.write_text({json.dumps(json.dumps(report))})\n"
            f"sys.exit({code})\n",
            encoding="utf-8",
        )
        path.chmod(stat.S_IRWXU)
        return str(path)

    def scan(self, **kwargs: object) -> tuple[int, dict]:
        return scanner.scan(self.root, config_path=self.config, **kwargs)


class SecretOutputTests(RepositoryCase):
    def test_public_summary_drops_all_sensitive_metadata(self) -> None:
        finding = {
            "RuleID": "github-pat",
            "File": "folder/evil\n::error::injection.txt",
            "StartLine": 7,
            "Secret": "PRIVATE_SECRET",
            "Match": "PRIVATE_CONTEXT",
            "Author": "PRIVATE_AUTHOR",
            "Email": "PRIVATE_EMAIL",
            "Message": "PRIVATE_COMMIT_MESSAGE",
            "Fingerprint": "PRIVATE_FINGERPRINT",
        }
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code, summary = self.scan(binary=self.fake_binary([finding], 1))
        rendered = json.dumps(summary, ensure_ascii=True)
        self.assertEqual(code, 1)
        self.assertEqual(stdout.getvalue(), "")
        self.assertEqual(stderr.getvalue(), "")
        self.assertNotIn("PRIVATE_", rendered)
        self.assertNotIn("\n", rendered)
        self.assertEqual(summary["findings"][0]["line"], 7)
        self.assertEqual(set(summary["findings"][0]), {"rule_id", "file", "line"})

    def test_paths_cannot_disclose_external_absolute_paths(self) -> None:
        for path in (
            "/home/private/credentials.txt",
            "../../private.txt",
            "C:\\private\\secret.txt",
        ):
            self.assertEqual(scanner.safe_path(path, self.root), "<outside-repository>")
        self.assertEqual(
            scanner.safe_path(str(self.root / "file.txt"), self.root), "file.txt"
        )

    def test_invalid_rule_and_line_metadata_are_not_forwarded(self) -> None:
        summary = scanner.summarise(
            [
                {
                    "RuleID": "secret\n::error::",
                    "StartLine": "PRIVATE_LINE",
                    "File": None,
                }
            ],
            self.root,
        )
        self.assertEqual(
            summary["findings"],
            [{"rule_id": "<invalid-rule>", "file": "<invalid-path>", "line": None}],
        )

    def test_scanner_failure_never_becomes_clean(self) -> None:
        with self.assertRaisesRegex(scanner.ScanError, "scanner_failed"):
            self.scan(binary=self.fake_binary([], 2))
        with self.assertRaisesRegex(
            scanner.ScanError, "scanner_failed_without_findings"
        ):
            self.scan(binary=self.fake_binary([], 1))

    def test_scanner_diagnostics_never_become_clean_or_leak(self) -> None:
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            with self.assertRaisesRegex(scanner.ScanError, "scanner_diagnostic_failed"):
                self.scan(binary=self.fake_binary([], noisy=True))
        self.assertEqual(stdout.getvalue(), "")
        self.assertEqual(stderr.getvalue(), "")

    def test_missing_scanner_is_an_error(self) -> None:
        with self.assertRaisesRegex(scanner.ScanError, "scanner_unavailable"):
            self.scan(binary=str(self.directory / "does-not-exist"))

    def test_malformed_report_is_an_error(self) -> None:
        with self.assertRaisesRegex(scanner.ScanError, "invalid_scanner_report"):
            self.scan(binary=self.fake_binary({"Secret": "PRIVATE_SECRET"}))

    def test_report_findings_override_incorrect_zero_exit(self) -> None:
        code, summary = self.scan(
            binary=self.fake_binary([{"RuleID": "rule", "File": "a", "StartLine": 1}])
        )
        self.assertEqual(code, 1)
        self.assertEqual(summary["status"], "findings")

    def test_safe_cli_error_is_json_and_does_not_echo_arguments(self) -> None:
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            code = scanner.main(["--unknown-PRIVATE_ARGUMENT"])
        self.assertEqual(code, 2)
        self.assertEqual(json.loads(stdout.getvalue())["error"], "invalid_arguments")
        self.assertNotIn("PRIVATE_ARGUMENT", stdout.getvalue())

    def test_io_failure_does_not_expose_exception_details(self) -> None:
        stdout = io.StringIO()
        with (
            patch.object(scanner, "scan", side_effect=OSError("PRIVATE_IO_DETAILS")),
            contextlib.redirect_stdout(stdout),
        ):
            code = scanner.main([])
        self.assertEqual(code, 2)
        self.assertEqual(json.loads(stdout.getvalue())["error"], "scan_io_failed")
        self.assertNotIn("PRIVATE_IO_DETAILS", stdout.getvalue())

    def test_disabled_default_rules_fail_closed(self) -> None:
        self.config.write_text(
            '[extend]\nuseDefault = true\ndisabledRules = ["github-pat"]\n'
        )
        with self.assertRaisesRegex(scanner.ScanError, "default_rules_required"):
            self.scan(binary=self.fake_binary([]))

    def test_invalid_revision_cannot_inject_git_options(self) -> None:
        with self.assertRaisesRegex(scanner.ScanError, "invalid_revision"):
            self.scan(base="--all --output=/tmp/exfil", binary=self.fake_binary([]))

    def test_private_reports_are_removed_after_scan(self) -> None:
        captured: list[Path] = []
        original = subprocess.run

        def inspect(command, *args, **kwargs):
            if "--report-path" in command:
                report = Path(command[command.index("--report-path") + 1])
                captured.append(report)
                self.assertEqual(stat.S_IMODE(report.parent.stat().st_mode), 0o700)
                self.assertEqual(stat.S_IMODE(report.stat().st_mode), 0o600)
                self.assertIn("--ignore-gitleaks-allow", command)
                ignored = Path(command[command.index("--gitleaks-ignore-path") + 1])
                self.assertEqual(ignored.read_bytes(), b"")
            return original(command, *args, **kwargs)

        with patch.object(scanner.subprocess, "run", side_effect=inspect):
            self.scan(binary=self.fake_binary([]))
        self.assertEqual(len(captured), 1)
        self.assertFalse(captured[0].exists())


class ReviewedFindingTests(RepositoryCase):
    def setUp(self) -> None:
        super().setUp()
        self.value = "PUBLIC-OBJECT"
        self.finding = {
            "RuleID": "generic-api-key",
            "File": "inventory.json",
            "StartLine": 3,
            "Commit": self.base,
            "Secret": self.value,
            "Match": "PRIVATE_CONTEXT",
        }
        self.admission = {
            "commit": self.base,
            "path": "inventory.json",
            "rule_id": "generic-api-key",
            "line": 3,
            "value_sha256": hashlib.sha256(self.value.encode()).hexdigest(),
            "reason": "Reviewed public-object regression fixture, only in a temporary test repository.",
            "evidence_urls": ["https://github.com/example/project/commit/" + self.base],
        }
        self.registry = self.directory / "reviewed-findings.json"
        self.write_registry()
        patcher = patch.object(
            scanner, "TRUSTED_REVIEWED_FINDINGS", self.registry, create=True
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def write_registry(self, entries: list | None = None) -> None:
        self.registry.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "findings": [self.admission] if entries is None else entries,
                }
            ),
            encoding="utf-8",
        )

    def test_exact_reviewed_finding_is_explicit_and_value_free(self) -> None:
        code, summary = self.scan(binary=self.fake_binary([self.finding], 1))
        self.assertEqual(code, 0)
        self.assertEqual(summary["status"], "reviewed_nonsecret")
        self.assertEqual(summary["finding_count"], 0)
        self.assertEqual(summary["detected_finding_count"], 1)
        self.assertEqual(summary["reviewed_nonsecret_count"], 1)
        self.assertEqual(summary["findings"], [])
        self.assertNotIn(self.value, json.dumps(summary))
        self.assertNotIn("PRIVATE_CONTEXT", json.dumps(summary))

    def test_every_identity_mismatch_still_blocks(self) -> None:
        for field, replacement in (
            ("Commit", "1" * 40),
            ("File", "other.json"),
            ("File", "./inventory.json"),
            ("File", "nested/../inventory.json"),
            ("File", str(self.root / "inventory.json")),
            ("RuleID", "github-pat"),
            ("StartLine", 4),
            ("StartLine", True),
            ("Secret", "DIFFERENT"),
            ("Secret", ""),
            ("Secret", None),
            ("Secret", 123),
            ("Commit", None),
            ("Commit", ""),
            ("Commit", 123),
        ):
            with self.subTest(field=field, replacement=replacement):
                finding = {**self.finding, field: replacement}
                code, summary = self.scan(binary=self.fake_binary([finding], 1))
                self.assertEqual((code, summary["finding_count"]), (1, 1))
                self.assertEqual(summary["reviewed_nonsecret_count"], 0)
        for field in ("Secret", "Commit"):
            with self.subTest(missing=field):
                finding = {
                    key: value for key, value in self.finding.items() if key != field
                }
                code, summary = self.scan(binary=self.fake_binary([finding], 1))
                self.assertEqual((code, summary["reviewed_nonsecret_count"]), (1, 0))

    def test_staged_findings_never_use_a_commit_admission(self) -> None:
        code, summary = self.scan(
            staged=True, binary=self.fake_binary([self.finding], 1)
        )
        self.assertEqual((code, summary["reviewed_nonsecret_count"]), (1, 0))

    def test_mixed_reviewed_and_unmatched_findings_still_block(self) -> None:
        other = {**self.finding, "Secret": "UNREVIEWED"}
        code, summary = self.scan(binary=self.fake_binary([self.finding, other], 1))
        self.assertEqual((code, summary["status"]), (1, "findings"))
        self.assertEqual(summary["finding_count"], 1)
        self.assertEqual(summary["reviewed_nonsecret_count"], 1)
        self.assertEqual(summary["detected_finding_count"], 2)
        self.assertNotIn("UNREVIEWED", json.dumps(summary))

    def test_distinct_values_at_one_coordinate_are_reviewed_individually(self) -> None:
        second_value = "SECOND-PUBLIC-OBJECT"
        second_entry = {
            **self.admission,
            "value_sha256": hashlib.sha256(second_value.encode()).hexdigest(),
        }
        self.write_registry([self.admission, second_entry])
        second_finding = {**self.finding, "Secret": second_value}
        extra_finding = {**self.finding, "Secret": "UNREVIEWED-THIRD-VALUE"}
        code, summary = self.scan(
            binary=self.fake_binary([self.finding, second_finding, extra_finding], 1)
        )
        self.assertEqual(code, 1)
        self.assertEqual(summary["reviewed_nonsecret_count"], 2)
        self.assertEqual(summary["finding_count"], 1)
        self.assertNotIn(second_value, json.dumps(summary))
        self.assertNotIn("UNREVIEWED-THIRD-VALUE", json.dumps(summary))

        code, summary = self.scan(binary=self.fake_binary([self.finding, second_finding], 1))
        self.assertEqual((code, summary["status"]), (0, "reviewed_nonsecret"))
        self.assertEqual(summary["reviewed_nonsecret_count"], 2)

    def test_scanner_failure_is_not_admitted(self) -> None:
        with self.assertRaisesRegex(scanner.ScanError, "scanner_failed"):
            self.scan(binary=self.fake_binary([self.finding], 2))

    def test_target_registry_and_environment_cannot_supply_admissions(self) -> None:
        target = self.root / "privacy" / "reviewed-findings.json"
        target.parent.mkdir()
        target.write_bytes(self.registry.read_bytes())
        self.write_registry([])
        with patch.dict(os.environ, {"PRIVACY_REVIEWED_FINDINGS": str(target)}):
            code, summary = self.scan(binary=self.fake_binary([self.finding], 1))
        self.assertEqual((code, summary["reviewed_nonsecret_count"]), (1, 0))

    def test_registry_is_revalidated_for_every_scan(self) -> None:
        self.scan(binary=self.fake_binary([self.finding], 1))
        self.registry.write_text("not JSON", encoding="utf-8")
        with self.assertRaisesRegex(scanner.ScanError, "invalid_reviewed_findings"):
            self.scan(binary=self.fake_binary([]))

    def test_oversized_registry_fails_closed(self) -> None:
        self.registry.write_bytes(b" " * (scanner.MAX_REVIEW_REGISTRY_BYTES + 1))
        with self.assertRaisesRegex(scanner.ScanError, "invalid_reviewed_findings"):
            self.scan(binary=self.fake_binary([]))

    def test_malformed_or_ambiguous_registry_fails_closed(self) -> None:
        cases = [
            {},
            [],
            {"schema_version": True, "findings": []},
            {"schema_version": 2, "findings": []},
            {"schema_version": 1, "findings": [], "extra": True},
            {"schema_version": 1, "findings": {}},
            {"schema_version": 1, "findings": [self.admission, self.admission]},
        ]
        for field, value in (
            ("commit", "HEAD"),
            ("commit", "0" * 40),
            ("path", "../inventory.json"),
            ("path", "./inventory.json"),
            ("path", "/inventory.json"),
            ("path", "folder\\inventory.json"),
            ("path", "inventory\n.json"),
            ("rule_id", "*"),
            ("line", True),
            ("line", 0),
            ("value_sha256", "*"),
            ("reason", ""),
            ("evidence_urls", []),
        ):
            cases.append(
                {"schema_version": 1, "findings": [{**self.admission, field: value}]}
            )
        for value in cases:
            with self.subTest(registry=value):
                self.registry.write_text(json.dumps(value), encoding="utf-8")
                with self.assertRaisesRegex(
                    scanner.ScanError, "invalid_reviewed_findings"
                ):
                    self.scan(binary=self.fake_binary([]))
        # Reject duplicate object keys at both top level and finding level.
        for value in (
            '{"schema_version":1,"schema_version":1,"findings":[]}',
            '{"schema_version":1,"findings":['
            + json.dumps(self.admission).replace(
                '{"commit":', '{"commit":"1","commit":', 1
            )
            + "]}",
        ):
            self.registry.write_text(value, encoding="utf-8")
            with self.assertRaisesRegex(scanner.ScanError, "invalid_reviewed_findings"):
                self.scan(binary=self.fake_binary([]))

    def test_registry_failure_cli_is_redacted_exit_two(self) -> None:
        self.registry.write_text("PRIVATE_REGISTRY_DATA", encoding="utf-8")
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            code = scanner.main(
                ["--root", str(self.root), "--binary", self.fake_binary([])]
            )
        self.assertEqual(code, 2)
        self.assertEqual(
            json.loads(stdout.getvalue())["error"], "invalid_reviewed_findings"
        )
        self.assertNotIn("PRIVATE_REGISTRY_DATA", stdout.getvalue())

    def test_non_posix_report_does_not_apply_admissions(self) -> None:
        with patch.object(scanner, "PRIVATE_MATCH_PROCESSING", False, create=True):
            code, summary = self.scan(binary=self.fake_binary([self.finding], 1))
        self.assertEqual((code, summary["reviewed_nonsecret_count"]), (1, 0))

    def test_private_report_permissions_are_verified_after_scanner_write(self) -> None:
        original = subprocess.run
        reports: list[Path] = []

        def inspect(command, *args, **kwargs):
            result = original(command, *args, **kwargs)
            if "--report-path" in command:
                report = Path(command[command.index("--report-path") + 1])
                reports.append(report)
                self.assertEqual(kwargs["umask"], 0o077)
                self.assertIn("--redact=0", command)
                self.assertEqual(stat.S_IMODE(report.stat().st_mode), 0o600)
                self.assertEqual(stat.S_IMODE(report.parent.stat().st_mode), 0o700)
                self.assertIn(self.value, report.read_text())
            return result

        with patch.object(scanner.subprocess, "run", side_effect=inspect):
            self.scan(binary=self.fake_binary([self.finding], 1))
        self.assertEqual(len(reports), 1)
        self.assertFalse(reports[0].exists())

    def test_report_permissions_cannot_be_broadened(self) -> None:
        original = subprocess.run

        def broaden(command, *args, **kwargs):
            result = original(command, *args, **kwargs)
            if "--report-path" in command:
                Path(command[command.index("--report-path") + 1]).chmod(0o644)
            return result

        with (
            patch.object(scanner.subprocess, "run", side_effect=broaden),
            self.assertRaisesRegex(scanner.ScanError, "unsafe_private_report"),
        ):
            self.scan(binary=self.fake_binary([self.finding], 1))

    def test_error_paths_remove_raw_reports_and_keep_public_errors_safe(self) -> None:
        for failure in (
            "scanner",
            "timeout",
            "malformed",
            "permissions",
            "hardlink",
            "symlink",
        ):
            with self.subTest(failure=failure):
                original = subprocess.run
                captured: list[Path] = []

                def fail(
                    command,
                    *args,
                    _original=original,
                    _captured=captured,
                    _failure=failure,
                    **kwargs,
                ):
                    result = _original(command, *args, **kwargs)
                    if "--report-path" in command:
                        report = Path(command[command.index("--report-path") + 1])
                        _captured.append(report)
                        if _failure == "timeout":
                            raise subprocess.TimeoutExpired(
                                command,
                                1,
                                output="PRIVATE_STDOUT",
                                stderr="PRIVATE_STDERR",
                            )
                        if _failure == "malformed":
                            report.write_text("PRIVATE_MALFORMED_JSON")
                        if _failure == "permissions":
                            report.chmod(0o644)
                        if _failure == "hardlink":
                            os.link(report, report.parent / "linked-report")
                        if _failure == "symlink":
                            moved = report.with_name("moved-report")
                            report.rename(moved)
                            report.symlink_to(moved)
                    return result

                output, errors = io.StringIO(), io.StringIO()
                with (
                    patch.object(scanner.subprocess, "run", side_effect=fail),
                    contextlib.redirect_stdout(output),
                    contextlib.redirect_stderr(errors),
                ):
                    code = scanner.main(
                        [
                            "--root",
                            str(self.root),
                            "--binary",
                            self.fake_binary(
                                [self.finding], 2 if failure == "scanner" else 1
                            ),
                        ]
                    )
                self.assertEqual(code, 2)
                self.assertEqual(json.loads(output.getvalue())["status"], "error")
                self.assertNotIn("PRIVATE_", output.getvalue() + errors.getvalue())
                self.assertNotIn(self.value, output.getvalue() + errors.getvalue())
                self.assertEqual(len(captured), 1)
                self.assertFalse(captured[0].exists())
                self.assertFalse(captured[0].parent.exists())


GITLEAKS_BINARY = os.environ.get("GITLEAKS_BINARY") or shutil.which("gitleaks")


@unittest.skipUnless(
    GITLEAKS_BINARY, "Verified Gitleaks binary not available; set GITLEAKS_BINARY"
)
class GitleaksIntegrationTests(RepositoryCase):
    @staticmethod
    def synthetic_secret() -> str:
        # Construct a synthetic pattern only in temporary fixtures, never a credential.
        return "ghp_" + hashlib.sha256(b"synthetic-regression-canary").hexdigest()[:36]

    def test_offline_mount_scans_history_across_owner_boundary(self) -> None:
        root = self.root.resolve()
        clean_environment = scanner.clean_environment
        with (
            patch.object(scanner, "OFFLINE_CONSUMER_MOUNT", root),
            patch.object(
                scanner,
                "clean_environment",
                side_effect=lambda **kwargs: {
                    **clean_environment(**kwargs),
                    "GIT_TEST_ASSUME_DIFFERENT_OWNER": "true",
                },
            ),
        ):
            with self.assertRaisesRegex(scanner.ScanError, "git_validation_failed"):
                scanner.scan(root, full_history=True, binary=GITLEAKS_BINARY)
            code, summary = scanner.scan(
                root,
                full_history=True,
                binary=GITLEAKS_BINARY,
                offline_container=True,
            )
        self.assertEqual(code, 0)
        self.assertEqual(summary["status"], "clean")

    def test_inherited_graft_cannot_hide_deleted_history(self) -> None:
        value = self.synthetic_secret()
        source = self.root / "historical-secret.txt"
        source.write_text(value + "\n")
        self.git("add", "historical-secret.txt")
        self.git("commit", "--quiet", "-m", "Synthetic historical finding")
        self.git("rm", "--quiet", "historical-secret.txt")
        self.git("commit", "--quiet", "-m", "Remove synthetic finding")
        graft = self.directory / "untrusted-graft"
        graft.write_text(self.git("rev-parse", "HEAD") + "\n")

        with patch.dict(os.environ, {"GIT_GRAFT_FILE": str(graft)}):
            for options in ({"full_history": True}, {"base": self.base}):
                with self.subTest(options=options):
                    code, summary = self.scan(binary=GITLEAKS_BINARY, **options)
                    self.assertEqual(code, 1)
                    self.assertIn(
                        "historical-secret.txt", {item["file"] for item in summary["findings"]}
                    )
                    self.assertNotIn(value, json.dumps(summary))

    def test_repository_graft_cannot_hide_deleted_history(self) -> None:
        value = self.synthetic_secret()
        source = self.root / "historical-secret.txt"
        source.write_text(value + "\n")
        self.git("add", "historical-secret.txt")
        self.git("commit", "--quiet", "-m", "Synthetic historical finding")
        self.git("rm", "--quiet", "historical-secret.txt")
        self.git("commit", "--quiet", "-m", "Remove synthetic finding")
        (self.root / ".git" / "info" / "grafts").write_text(
            self.git("rev-parse", "HEAD") + "\n"
        )

        for options in ({"full_history": True}, {"base": self.base}):
            with self.subTest(options=options):
                code, summary = self.scan(binary=GITLEAKS_BINARY, **options)
                self.assertEqual(code, 1)
                self.assertIn(
                    "historical-secret.txt", {item["file"] for item in summary["findings"]}
                )
                self.assertNotIn(value, json.dumps(summary))

    def test_replacement_refs_cannot_hide_deleted_history(self) -> None:
        value = self.synthetic_secret()
        source = self.root / "historical-secret.txt"
        source.write_text(value + "\n")
        self.git("add", "historical-secret.txt")
        self.git("commit", "--quiet", "-m", "Synthetic historical finding")
        self.git("rm", "--quiet", "historical-secret.txt")
        self.git("commit", "--quiet", "-m", "Remove synthetic finding")
        self.git("replace", "--graft", self.git("rev-parse", "HEAD"))

        for options in ({"full_history": True}, {"base": self.base}):
            with self.subTest(options=options):
                code, summary = self.scan(binary=GITLEAKS_BINARY, **options)
                self.assertEqual(code, 1)
                self.assertIn(
                    "historical-secret.txt", {item["file"] for item in summary["findings"]}
                )
                self.assertNotIn(value, json.dumps(summary))

    def test_inherited_shallow_file_cannot_hide_deleted_history(self) -> None:
        value = self.synthetic_secret()
        source = self.root / "historical-secret.txt"
        source.write_text(value + "\n")
        self.git("add", "historical-secret.txt")
        self.git("commit", "--quiet", "-m", "Synthetic historical finding")
        self.git("rm", "--quiet", "historical-secret.txt")
        self.git("commit", "--quiet", "-m", "Remove synthetic finding")
        shallow = self.directory / "untrusted-shallow"
        shallow.write_text(self.git("rev-parse", "HEAD") + "\n")

        with patch.dict(os.environ, {"GIT_SHALLOW_FILE": str(shallow)}):
            for options in ({"full_history": True}, {"base": self.base}):
                with self.subTest(options=options):
                    code, summary = self.scan(binary=GITLEAKS_BINARY, **options)
                    self.assertEqual(code, 1)
                    self.assertIn(
                        "historical-secret.txt", {item["file"] for item in summary["findings"]}
                    )
                    self.assertNotIn(value, json.dumps(summary))

    def test_range_scan_rejects_an_actual_shallow_boundary(self) -> None:
        (self.root / "later.txt").write_text("synthetic change\n")
        self.git("add", "later.txt")
        self.git("commit", "--quiet", "-m", "Synthetic later commit")
        (self.root / ".git" / "shallow").write_text(self.git("rev-parse", "HEAD") + "\n")
        with self.assertRaisesRegex(scanner.ScanError, "range_requires_complete_clone"):
            self.scan(base=self.base, binary=GITLEAKS_BINARY)

    def test_binary_git_attributes_cannot_hide_text_history(self) -> None:
        value = self.synthetic_secret()
        (self.root / ".gitattributes").write_text("*.txt -diff\n")
        self.git("add", ".gitattributes")
        self.git("commit", "--quiet", "-m", "Synthetic binary attribute")
        source = self.root / "historical-secret.txt"
        source.write_text(value + "\n")
        self.git("add", "historical-secret.txt")
        self.git("commit", "--quiet", "-m", "Synthetic historical finding")
        self.git("rm", "--quiet", "historical-secret.txt")
        self.git("commit", "--quiet", "-m", "Remove synthetic finding")

        for options in ({"full_history": True}, {"base": self.base}):
            with self.subTest(options=options):
                code, summary = self.scan(binary=GITLEAKS_BINARY, **options)
                self.assertEqual(code, 1)
                self.assertIn(
                    "historical-secret.txt", {item["file"] for item in summary["findings"]}
                )
                self.assertNotIn(value, json.dumps(summary))

    def test_info_attributes_cannot_hide_text_history(self) -> None:
        value = self.synthetic_secret()
        source = self.root / "historical-secret.txt"
        source.write_text(value + "\n")
        self.git("add", "historical-secret.txt")
        self.git("commit", "--quiet", "-m", "Synthetic historical finding")
        self.git("rm", "--quiet", "historical-secret.txt")
        self.git("commit", "--quiet", "-m", "Remove synthetic finding")
        (self.root / ".git" / "info" / "attributes").write_text("*.txt -diff\n")

        for options in ({"full_history": True}, {"base": self.base}):
            with self.subTest(options=options):
                code, summary = self.scan(binary=GITLEAKS_BINARY, **options)
                self.assertEqual(code, 1)
                self.assertIn(
                    "historical-secret.txt", {item["file"] for item in summary["findings"]}
                )
                self.assertNotIn(value, json.dumps(summary))

    def test_info_attributes_cannot_hide_staged_text(self) -> None:
        value = self.synthetic_secret()
        (self.root / "staged-secret.txt").write_text(value + "\n")
        self.git("add", "staged-secret.txt")
        (self.root / ".git" / "info" / "attributes").write_text("*.txt -diff\n")
        with self.assertRaisesRegex(scanner.ScanError, "staged_binary_diff_unscannable"):
            self.scan(staged=True, binary=GITLEAKS_BINARY)

    def test_staged_binary_diff_fails_closed(self) -> None:
        (self.root / "binary.bin").write_bytes(b"\x00synthetic-binary\n")
        self.git("add", "binary.bin")
        with self.assertRaisesRegex(scanner.ScanError, "staged_binary_diff_unscannable"):
            self.scan(staged=True, binary=GITLEAKS_BINARY)

    def test_staged_custom_textconv_is_not_executed_or_trusted(self) -> None:
        (self.root / ".gitattributes").write_text("*.txt diff=fixture\n")
        (self.root / "staged-secret.txt").write_text(self.synthetic_secret() + "\n")
        self.git("add", ".gitattributes", "staged-secret.txt")
        marker = self.directory / "textconv-executed"
        converter = self.directory / "textconv.sh"
        converter.write_text(
            "#!/bin/sh\nprintf invoked > " + shlex.quote(str(marker))
            + "\nprintf 'redacted fixture\\n'\n"
        )
        converter.chmod(0o700)
        self.git("config", "diff.fixture.textconv", str(converter))
        self.git("diff", "--staged")
        self.assertTrue(marker.exists(), "Fixture must demonstrate textconv executes")
        marker.unlink()
        with self.assertRaisesRegex(scanner.ScanError, "staged_custom_diff_unscannable"):
            self.scan(staged=True, binary=GITLEAKS_BINARY)
        self.assertFalse(marker.exists())

    def test_partial_clone_with_missing_blobs_fails_closed(self) -> None:
        (self.root / "later.txt").write_text(self.synthetic_secret() + "\n")
        self.git("add", "later.txt")
        self.git("commit", "--quiet", "-m", "Synthetic historical finding")
        self.git("config", "uploadpack.allowFilter", "true")
        partial = self.directory / "partial"
        subprocess.run(
            ["git", "clone", "--quiet", "--filter=blob:none", "--no-checkout",
             self.root.as_uri(), str(partial)],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        subprocess.run(
            ["git", "-C", str(partial), "remote", "set-url", "origin",
             (self.directory / "unavailable-origin").as_uri()],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        def missing_objects() -> bytes:
            return subprocess.run(
                ["git", "-C", str(partial), "rev-list", "--objects", "--all",
                 "--missing=print"],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                env={**os.environ, "GIT_NO_LAZY_FETCH": "1"},
            ).stdout

        self.assertTrue(any(line.startswith(b"?") for line in missing_objects().splitlines()))
        for options in ({"full_history": True}, {"base": self.base}):
            with self.subTest(options=options):
                with self.assertRaisesRegex(scanner.ScanError, "git_history_preflight_failed"):
                    scanner.scan(partial, config_path=self.config, binary=GITLEAKS_BINARY, **options)
        self.assertTrue(any(line.startswith(b"?") for line in missing_objects().splitlines()))

    def test_staged_scan_does_not_execute_repository_fsmonitor(self) -> None:
        (self.root / "staged.txt").write_text("synthetic text\n")
        self.git("add", "staged.txt")
        marker = self.directory / "fsmonitor-executed"
        helper = self.directory / "fsmonitor.sh"
        helper.write_text("#!/bin/sh\nprintf invoked > " + shlex.quote(str(marker)) + "\n")
        helper.chmod(0o700)
        self.git("config", "core.fsmonitor", str(helper))
        self.git("diff", "--staged")
        self.assertTrue(marker.exists(), "Fixture must demonstrate the Git hook executes")
        marker.unlink()

        code, summary = self.scan(staged=True, binary=GITLEAKS_BINARY)
        self.assertEqual((code, summary["status"]), (0, "clean"))
        self.assertFalse(marker.exists())

    def test_full_history_scans_root_even_when_local_config_hides_it(self) -> None:
        value = self.synthetic_secret()
        (self.root / "README.md").write_text(value + "\n")
        self.git("add", "README.md")
        self.git("commit", "--quiet", "--amend", "--no-edit")
        self.git("config", "log.showRoot", "false")
        self.assertNotIn(value, self.git("log", "-p", "--all"))
        code, summary = self.scan(full_history=True, binary=GITLEAKS_BINARY)
        self.assertEqual(code, 1)
        self.assertIn("README.md", {item["file"] for item in summary["findings"]})
        self.assertNotIn(value, json.dumps(summary))

    def test_local_pretty_format_cannot_hide_history_findings(self) -> None:
        value = self.synthetic_secret()
        (self.root / "historical-secret.txt").write_text(value + "\n")
        self.git("add", "historical-secret.txt")
        self.git("commit", "--quiet", "-m", "Synthetic historical finding")
        self.git("config", "format.pretty", "oneline")
        self.assertFalse(self.git("log", "-1").startswith("commit "))
        code, summary = self.scan(base=self.base, binary=GITLEAKS_BINARY)
        self.assertEqual(code, 1)
        self.assertIn("historical-secret.txt", {item["file"] for item in summary["findings"]})
        self.assertNotIn(value, json.dumps(summary))

    def test_history_scan_does_not_execute_repository_signature_verifier(self) -> None:
        value = self.synthetic_secret()
        (self.root / "signed-secret.txt").write_text(value + "\n")
        self.git("add", "signed-secret.txt")
        signer = self.directory / "synthetic-signer.sh"
        signer.write_text(
            "#!/bin/sh\ncat >/dev/null\n"
            "printf '[GNUPG:] SIG_CREATED D 1 10 00 0 ABCDEF\\n' >&2\n"
            "printf '%s\\n' '-----BEGIN PGP SIGNATURE-----' 'fixture' '-----END PGP SIGNATURE-----'\n"
        )
        signer.chmod(0o700)
        self.git("-c", "gpg.program=" + str(signer), "-c", "commit.gpgsign=true", "commit", "--quiet", "-m", "Synthetic signed commit")
        marker = self.directory / "verifier-executed"
        verifier = self.directory / "synthetic-verifier.sh"
        verifier.write_text("#!/bin/sh\nprintf invoked > " + shlex.quote(str(marker)) + "\nexit 1\n")
        verifier.chmod(0o700)
        self.git("config", "log.showSignature", "true")
        self.git("config", "gpg.program", str(verifier))
        self.git("log", "-1", "--format=%H")
        self.assertTrue(marker.exists(), "Fixture must demonstrate signature verification executes")
        marker.unlink()

        for options in ({"full_history": True}, {"base": self.base}):
            with self.subTest(options=options):
                code, summary = self.scan(binary=GITLEAKS_BINARY, **options)
                self.assertEqual(code, 1)
                self.assertIn("signed-secret.txt", {item["file"] for item in summary["findings"]})
                self.assertFalse(marker.exists())
                self.assertNotIn(value, json.dumps(summary))

    def test_real_cli_exact_admission_and_extra_secret_resistance(self) -> None:
        self.verify_exact_admission(
            hashlib.sha1(b"public-object-regression-fixture").hexdigest()
        )

    def test_real_cli_exact_sha256_admission_and_extra_secret_resistance(self) -> None:
        self.verify_exact_admission(
            hashlib.sha256(b"public-object-regression-fixture").hexdigest()
        )

    def test_merge_only_and_removed_side_branch_secrets_are_both_scanned(self) -> None:
        original_branch = self.git("branch", "--show-current")
        side_value = "ghp_" + hashlib.sha256(b"fictional-side-canary").hexdigest()[:36]
        merge_value = "ghp_" + hashlib.sha256(b"fictional-merge-canary").hexdigest()[:36]
        self.git("checkout", "--quiet", "-b", "side")
        (self.root / "side.txt").write_text(side_value + "\n")
        self.git("add", "side.txt")
        self.git("commit", "--quiet", "-m", "Synthetic side commit")
        self.git("checkout", "--quiet", original_branch)
        (self.root / "main.txt").write_text("main branch\n")
        self.git("add", "main.txt")
        self.git("commit", "--quiet", "-m", "Synthetic main commit")
        self.git("merge", "--quiet", "--no-ff", "--no-commit", "side")
        self.git("rm", "--force", "--quiet", "side.txt")
        (self.root / "merge-only.txt").write_text(merge_value + "\n")
        self.git("add", "merge-only.txt")
        self.git("commit", "--quiet", "-m", "Synthetic merge resolution")

        for options in ({"full_history": True}, {"base": self.base}):
            with self.subTest(options=options):
                code, summary = self.scan(binary=GITLEAKS_BINARY, **options)
                self.assertEqual(code, 1)
                paths = {finding["file"] for finding in summary["findings"]}
                self.assertIn("side.txt", paths)
                self.assertIn("merge-only.txt", paths)
                self.assertNotIn(side_value, json.dumps(summary))
                self.assertNotIn(merge_value, json.dumps(summary))
                clean_environment = scanner.clean_environment
                with (
                    patch.object(scanner, "OFFLINE_CONSUMER_MOUNT", self.root.resolve()),
                    patch.object(
                        scanner,
                        "clean_environment",
                        side_effect=lambda **kwargs: {
                            **clean_environment(**kwargs),
                            "GIT_TEST_ASSUME_DIFFERENT_OWNER": "true",
                        },
                    ),
                ):
                    offline_code, offline_summary = self.scan(
                        binary=GITLEAKS_BINARY, offline_container=True, **options
                    )
                self.assertEqual(offline_code, 1)
                offline_paths = {finding["file"] for finding in offline_summary["findings"]}
                self.assertIn("side.txt", offline_paths)
                self.assertIn("merge-only.txt", offline_paths)
                self.assertNotIn(side_value, json.dumps(offline_summary))
                self.assertNotIn(merge_value, json.dumps(offline_summary))

    def test_real_cli_distinct_values_on_one_line_remain_individually_blocking(
        self,
    ) -> None:
        values = [
            hashlib.sha256(label).hexdigest()
            for label in (b"public-first", b"public-second", b"unreviewed-third")
        ]
        source = self.root / "checksums.json"
        source.write_text(
            json.dumps(
                {
                    "allocator-api2-0.2.21.tar.gz": values[0],
                    "winapi-0.3.9.tar.gz": values[1],
                    "api_key": values[2],
                }
            )
            + "\n"
        )
        self.git("add", "checksums.json")
        self.git("commit", "--quiet", "-m", "Synthetic same-line findings")
        commit = self.git("rev-parse", "HEAD")
        entries = [
            {
                "commit": commit,
                "path": "checksums.json",
                "rule_id": "generic-api-key",
                "line": 1,
                "value_sha256": hashlib.sha256(value.encode()).hexdigest(),
                "reason": "Reviewed synthetic public digest in a temporary regression fixture.",
                "evidence_urls": ["https://github.com/example/project/commit/" + commit],
            }
            for value in values[:2]
        ]
        registry = self.directory / "reviewed.json"
        registry.write_text(json.dumps({"schema_version": 1, "findings": entries}))
        with patch.object(scanner, "TRUSTED_REVIEWED_FINDINGS", registry):
            code, summary = self.scan(base=self.base, binary=GITLEAKS_BINARY)
        self.assertEqual(code, 1)
        self.assertEqual(summary["reviewed_nonsecret_count"], 2)
        self.assertEqual(summary["finding_count"], 1)
        for value in values:
            self.assertNotIn(value, json.dumps(summary))

    def test_same_reviewed_value_in_two_contexts_remains_blocking(self) -> None:
        value = hashlib.sha256(b"synthetic-public-digest").hexdigest()
        source = self.root / "checksums.json"
        source.write_text(json.dumps({"allocator-api2.tar.gz": value, "api_key": value}) + "\n")
        self.git("add", "checksums.json")
        self.git("commit", "--quiet", "-m", "Synthetic duplicate contexts")
        commit = self.git("rev-parse", "HEAD")
        entry = {
            "commit": commit,
            "path": "checksums.json",
            "rule_id": "generic-api-key",
            "line": 1,
            "value_sha256": hashlib.sha256(value.encode()).hexdigest(),
            "reason": "Synthetic public digest reviewed in one temporary fixture context.",
            "evidence_urls": ["https://github.com/example/project/commit/" + commit],
        }
        registry = self.directory / "reviewed.json"
        registry.write_text(json.dumps({"schema_version": 1, "findings": [entry]}))
        with patch.object(scanner, "TRUSTED_REVIEWED_FINDINGS", registry):
            code, summary = self.scan(base=self.base, binary=GITLEAKS_BINARY)
        self.assertEqual(code, 1)
        self.assertEqual(summary["finding_count"], 2)
        self.assertEqual(summary["reviewed_nonsecret_count"], 0)
        self.assertNotIn(value, json.dumps(summary))

    def verify_exact_admission(self, value: str) -> None:
        source = self.root / "inventory.json"
        source.write_text(
            json.dumps({"privacy-" + "secrets.yml": value}, indent=2) + "\n"
        )
        self.git("add", "inventory.json")
        self.git("commit", "--quiet", "-m", "Public object fixture")
        commit = self.git("rev-parse", "HEAD")
        entry = {
            "commit": commit,
            "path": "inventory.json",
            "rule_id": "generic-api-key",
            "line": 2,
            "value_sha256": hashlib.sha256(value.encode()).hexdigest(),
            "reason": "Reviewed synthetic public object for a temporary behavioral test.",
            "evidence_urls": ["https://github.com/example/project/commit/" + commit],
        }
        tooling = self.directory / "pinned-tooling"
        (tooling / "scripts").mkdir(parents=True)
        (tooling / "privacy").mkdir()
        shutil.copyfile(scanner.__file__, tooling / "scripts" / "secrets_scan.py")
        shutil.copyfile(self.config, tooling / "privacy" / "gitleaks.toml")
        registry = tooling / "privacy" / "reviewed-findings.json"
        registry.write_text(json.dumps({"schema_version": 1, "findings": [entry]}))
        command = [
            sys.executable,
            "-I",
            str(tooling / "scripts" / "secrets_scan.py"),
            "--root",
            str(self.root),
            "--binary",
            str(GITLEAKS_BINARY),
            "--base",
            self.base,
        ]
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        summary = json.loads(result.stdout)
        self.assertEqual(
            (result.returncode, summary["status"]), (0, "reviewed_nonsecret")
        )
        self.assertEqual(summary["reviewed_nonsecret_count"], 1)
        self.assertNotIn(value, result.stdout + result.stderr)

        # A repository cannot replace the trusted registry, nor hide another finding.
        target_registry = self.root / "privacy" / "reviewed-findings.json"
        target_registry.parent.mkdir()
        target_registry.write_bytes(registry.read_bytes())
        registry.write_text(json.dumps({"schema_version": 1, "findings": []}))
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        self.assertEqual(
            (result.returncode, json.loads(result.stdout)["reviewed_nonsecret_count"]),
            (1, 0),
        )
        registry.write_bytes(target_registry.read_bytes())

        (self.root / "extra.txt").write_text(
            self.synthetic_secret() + " # gitleaks:allow\n"
        )
        self.git("add", "extra.txt")
        self.git("commit", "--quiet", "-m", "Unreviewed synthetic credential fixture")
        (self.root / ".gitleaksignore").write_text(
            self.git("rev-parse", "HEAD") + ":extra.txt:github-pat:1\n"
        )
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        summary = json.loads(result.stdout)
        self.assertEqual((result.returncode, summary["status"]), (1, "findings"))
        self.assertEqual(summary["reviewed_nonsecret_count"], 1)
        self.assertGreater(summary["finding_count"], 0)
        self.assertEqual(
            summary["detected_finding_count"],
            summary["reviewed_nonsecret_count"] + summary["finding_count"],
        )
        self.assertNotIn(value, result.stdout + result.stderr)
        self.assertNotIn(self.synthetic_secret(), result.stdout + result.stderr)

    def test_algorithm_qualified_hash_preserves_nearby_credential_detection(
        self,
    ) -> None:
        value = hashlib.sha256(b"public-workflow-format-fixture").hexdigest()
        source = self.root / "capsule.json"
        fields = {"privacy-" + "secrets.yml": "sha256:" + value}
        source.write_text(json.dumps(fields, indent=2) + "\n")
        self.git("add", "capsule.json")
        self.git("commit", "--quiet", "-m", "Qualified public digest fixture")
        code, summary = self.scan(base=self.base, binary=GITLEAKS_BINARY)
        self.assertEqual((code, summary["finding_count"]), (0, 0))

        credential = hashlib.sha256(b"synthetic-nearby-credential-canary").hexdigest()
        fields["api_" + "key"] = credential
        source.write_text(json.dumps(fields, indent=2) + "\n")
        self.git("add", "capsule.json")
        self.git("commit", "--quiet", "-m", "Nearby credential fixture")
        code, summary = self.scan(base=self.base, binary=GITLEAKS_BINARY)
        self.assertEqual(code, 1)
        self.assertGreater(summary["counts_by_rule"].get("generic-api-key", 0), 0)
        self.assertNotIn(credential, json.dumps(summary))
        self.assertNotIn(value, json.dumps(summary))

    def test_real_report_is_private_after_gitleaks_replaces_it(self) -> None:
        (self.root / "leak.txt").write_text(self.synthetic_secret() + "\n")
        self.git("add", "leak.txt")
        self.git("commit", "--quiet", "-m", "Private report fixture")
        original = subprocess.run
        reports: list[Path] = []

        def inspect(command, *args, **kwargs):
            result = original(command, *args, **kwargs)
            if "--report-path" in command:
                report = Path(command[command.index("--report-path") + 1])
                reports.append(report)
                self.assertEqual(stat.S_IMODE(report.stat().st_mode), 0o600)
                self.assertEqual(stat.S_IMODE(report.parent.stat().st_mode), 0o700)
                self.assertIn(self.synthetic_secret(), report.read_text())
            return result

        with patch.object(scanner.subprocess, "run", side_effect=inspect):
            code, _ = self.scan(base=self.base, binary=GITLEAKS_BINARY)
        self.assertEqual(code, 1)
        self.assertEqual(len(reports), 1)
        self.assertFalse(reports[0].exists())

    def test_all_submitted_commits_are_scanned_even_after_deletion(self) -> None:
        path = self.root / "temporary.txt"
        path.write_text(self.synthetic_secret() + "\n", encoding="utf-8")
        self.git("add", "temporary.txt")
        self.git("commit", "--quiet", "-m", "Synthetic leak fixture")
        self.git("rm", "temporary.txt")
        self.git("commit", "--quiet", "-m", "Remove fixture")
        code, summary = self.scan(base=self.base, binary=GITLEAKS_BINARY)
        self.assertEqual(code, 1)
        self.assertGreater(summary["finding_count"], 0)
        self.assertNotIn(self.synthetic_secret(), json.dumps(summary))

    def test_staged_mode_scans_index_not_clean_worktree(self) -> None:
        path = self.root / "staged.txt"
        path.write_text(self.synthetic_secret() + "\n", encoding="utf-8")
        self.git("add", "staged.txt")
        path.write_text("Working copy is clean; index is not.\n", encoding="utf-8")
        code, summary = self.scan(staged=True, binary=GITLEAKS_BINARY)
        self.assertEqual(code, 1)
        self.assertEqual(summary["mode"], "staged")

    def test_inline_allow_and_repo_config_cannot_disable_baseline(self) -> None:
        (self.root / ".gitleaks.toml").write_text(
            "[extend]\nuseDefault = false\n", encoding="utf-8"
        )
        (self.root / "inline.txt").write_text(
            self.synthetic_secret() + " # gitleaks:allow\n", encoding="utf-8"
        )
        self.git("add", ".gitleaks.toml", "inline.txt")
        self.git("commit", "--quiet", "-m", "Synthetic override fixture")
        (self.root / ".gitleaksignore").write_text(
            self.git("rev-parse", "HEAD") + ":inline.txt:github-pat:1\n",
            encoding="utf-8",
        )
        code, summary = self.scan(base=self.base, binary=GITLEAKS_BINARY)
        self.assertEqual(code, 1)
        self.assertGreater(summary["finding_count"], 0)

    def test_initial_staged_commit_is_scanned_without_head(self) -> None:
        initial = self.directory / "initial"
        initial.mkdir()
        subprocess.run(["git", "-C", str(initial), "init", "--quiet"], check=True)
        (initial / "initial.txt").write_text(
            self.synthetic_secret() + "\n", encoding="utf-8"
        )
        subprocess.run(["git", "-C", str(initial), "add", "initial.txt"], check=True)
        code, summary = scanner.scan(
            initial, staged=True, config_path=self.config, binary=GITLEAKS_BINARY
        )
        self.assertEqual((code, summary["status"]), (1, "findings"))

    def test_full_history_finds_other_branch_and_clean_range_passes(self) -> None:
        code, summary = self.scan(base=self.base, binary=GITLEAKS_BINARY)
        self.assertEqual((code, summary["status"]), (0, "clean"))
        self.git("checkout", "--quiet", "-b", "synthetic-other")
        (self.root / "branch.txt").write_text(
            self.synthetic_secret() + "\n", encoding="utf-8"
        )
        self.git("add", "branch.txt")
        self.git("commit", "--quiet", "-m", "Other branch synthetic fixture")
        self.git("checkout", "--quiet", "--detach", self.base)
        code, summary = self.scan(full_history=True, binary=GITLEAKS_BINARY)
        self.assertEqual(code, 1)
        self.assertEqual(summary["mode"], "full_history")

    def test_shallow_full_history_is_explicitly_rejected(self) -> None:
        clone = self.directory / "shallow"
        subprocess.run(
            ["git", "clone", "--quiet", "--depth", "1", self.root.as_uri(), str(clone)],
            check=True,
        )
        with self.assertRaisesRegex(
            scanner.ScanError, "full_history_requires_complete_clone"
        ):
            scanner.scan(
                clone,
                full_history=True,
                config_path=self.config,
                binary=GITLEAKS_BINARY,
            )


if __name__ == "__main__":
    unittest.main()
