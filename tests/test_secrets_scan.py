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


GITLEAKS_BINARY = os.environ.get("GITLEAKS_BINARY") or shutil.which("gitleaks")


@unittest.skipUnless(
    GITLEAKS_BINARY, "Verified Gitleaks binary not available; set GITLEAKS_BINARY"
)
class GitleaksIntegrationTests(RepositoryCase):
    @staticmethod
    def synthetic_secret() -> str:
        # Construct a synthetic pattern only in temporary fixtures, never a credential.
        return "ghp_" + hashlib.sha256(b"synthetic-regression-canary").hexdigest()[:36]

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
