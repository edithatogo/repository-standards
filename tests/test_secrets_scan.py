"""Behavioral tests: secret withholding, fail-closed errors and commit coverage."""

from __future__ import annotations

import contextlib
import hashlib
import io
import json
import os
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

    def fake_binary(self, report: object, code: int = 0) -> str:
        path = self.directory / "fake-gitleaks"
        path.write_text(
            "#!/usr/bin/env python3\n"
            "import json, pathlib, sys\n"
            "print('PRIVATE_SCANNER_STDOUT')\n"
            "print('PRIVATE_SCANNER_STDERR', file=sys.stderr)\n"
            "target = pathlib.Path(sys.argv[sys.argv.index('--report-path') + 1])\n"
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
        with (
            patch.object(scanner, "OFFLINE_CONSUMER_MOUNT", root),
            patch.dict(os.environ, {"GIT_TEST_ASSUME_DIFFERENT_OWNER": "true"}),
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

    def test_real_cli_exact_admission_and_extra_secret_resistance(self) -> None:
        self.verify_exact_admission(
            hashlib.sha1(b"public-object-regression-fixture").hexdigest()
        )

    def test_real_cli_exact_sha256_admission_and_extra_secret_resistance(self) -> None:
        self.verify_exact_admission(
            hashlib.sha256(b"public-object-regression-fixture").hexdigest()
        )

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
