"""Run the shared Gitleaks baseline without exposing matches or scanner logs.

Only the pinned tooling repository supplies scanner configuration. Repository
allowlists and inline suppression comments do not weaken this independent gate.
Reports exist only inside a private temporary directory and are removed on exit.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import tomllib
from collections import Counter
from pathlib import Path, PurePosixPath
from typing import Any

TIMEOUT_SECONDS = 600
MAX_REPORT_BYTES = 64 * 1024 * 1024
MAX_SUMMARY_FINDINGS = 100
REVISION = re.compile(r"(?:[0-9a-fA-F]{40}|[0-9a-fA-F]{64})\Z")
RULE_ID = re.compile(r"[a-zA-Z0-9_-]{1,120}\Z")
TRUSTED_CONFIG = Path(__file__).resolve().parents[1] / "privacy" / "gitleaks.toml"


class ScanError(Exception):
    """A fixed diagnostic code safe to include in public output."""


class SafeParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise ScanError("invalid_arguments")


def clean_environment() -> dict[str, str]:
    env = dict(os.environ)
    for key in tuple(env):
        if key.startswith("GIT_CONFIG_") or key in {
            "GITLEAKS_CONFIG",
            "GITLEAKS_CONFIG_TOML",
            "GIT_DIR",
            "GIT_WORK_TREE",
            "GIT_INDEX_FILE",
            "GIT_OBJECT_DIRECTORY",
            "GIT_ALTERNATE_OBJECT_DIRECTORIES",
            "GH_TOKEN",
            "GITHUB_TOKEN",
        }:
            env.pop(key, None)
    env.update(
        GIT_CONFIG_NOSYSTEM="1",
        GIT_CONFIG_GLOBAL=os.devnull,
        GIT_CONFIG_COUNT="2",
        GIT_CONFIG_KEY_0="core.hooksPath",
        GIT_CONFIG_VALUE_0=os.devnull,
        GIT_CONFIG_KEY_1="diff.external",
        GIT_CONFIG_VALUE_1="",
        GIT_TERMINAL_PROMPT="0",
        GIT_PAGER="cat",
        GIT_OPTIONAL_LOCKS="0",
    )
    return env


def git_output(root: Path, *args: str) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), *args],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            env=clean_environment(),
            check=False,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError) as error:
        raise ScanError("git_unavailable") from error
    if result.returncode != 0:
        raise ScanError("git_validation_failed")
    try:
        return result.stdout.decode("utf-8").removesuffix("\n").removesuffix("\r")
    except UnicodeError as error:
        raise ScanError("git_validation_failed") from error


def resolve_revision(root: Path, revision: str, *, allow_head: bool = False) -> str:
    if not REVISION.fullmatch(revision) and not (allow_head and revision == "HEAD"):
        raise ScanError("invalid_revision")
    resolved = git_output(
        root, "rev-parse", "--verify", "--end-of-options", revision + "^{commit}"
    )
    if not REVISION.fullmatch(resolved):
        raise ScanError("invalid_revision")
    return resolved


def safe_path(value: Any, root: Path) -> str:
    if not isinstance(value, str) or not value or len(value) > 1024:
        return "<invalid-path>"
    # Git paths use '/'. Reject traversal and Windows absolute paths as well.
    path = PurePosixPath(value)
    if path.is_absolute():
        try:
            path = PurePosixPath(Path(value).relative_to(root).as_posix())
        except ValueError:
            return "<outside-repository>"
    if (
        ".." in PurePosixPath(str(path).replace("\\", "/")).parts
        or re.match(r"^[a-zA-Z]:[\\/]", value)
        or value.startswith("\\")
    ):
        return "<outside-repository>"
    return str(path)


def summarise(findings: list[Any], root: Path) -> dict[str, Any]:
    safe: list[dict[str, Any]] = []
    counts: Counter[str] = Counter()
    for finding in findings:
        if not isinstance(finding, dict):
            raise ScanError("invalid_scanner_report")
        rule = finding.get("RuleID")
        if not isinstance(rule, str) or not RULE_ID.fullmatch(rule):
            rule = "<invalid-rule>"
        counts[rule] += 1
        if len(safe) < MAX_SUMMARY_FINDINGS:
            line = finding.get("StartLine")
            safe.append(
                {
                    "rule_id": rule,
                    "file": safe_path(finding.get("File"), root),
                    "line": line if type(line) is int and line > 0 else None,
                }
            )
    return {
        "scanner": "gitleaks",
        "status": "findings" if findings else "clean",
        "finding_count": len(findings),
        "counts_by_rule": dict(sorted(counts.items())),
        "findings": safe,
        "summary_truncated": len(findings) > MAX_SUMMARY_FINDINGS,
    }


def scan(
    root: Path,
    *,
    base: str | None = None,
    head: str = "HEAD",
    staged: bool = False,
    full_history: bool = False,
    binary: str = "gitleaks",
    config_path: Path = TRUSTED_CONFIG,
) -> tuple[int, dict[str, Any]]:
    if (staged and (base is not None or full_history)) or (
        base is not None and full_history
    ):
        raise ScanError("incompatible_scan_modes")
    try:
        root = root.resolve(strict=True)
        if not root.is_dir():
            raise ScanError("invalid_repository")
    except OSError as error:
        raise ScanError("invalid_repository") from error
    try:
        config = tomllib.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise ScanError("trusted_configuration_unavailable") from error
    extension = config.get("extend", {})
    if not isinstance(extension, dict) or extension.get("useDefault") is not True:
        raise ScanError("default_rules_required")
    if extension.get("disabledRules") or extension.get("path"):
        raise ScanError("default_rules_required")
    if git_output(root, "rev-parse", "--is-inside-work-tree") != "true":
        raise ScanError("invalid_repository")

    mode = (
        "staged"
        if staged
        else "full_history"
        if full_history or base is None
        else "commit_range"
    )
    if staged:
        # Explicitly select staged diff mode rather than the working copy.
        scan_args = ["--pre-commit", "--staged"]
    elif full_history or base is None:
        resolve_revision(root, head, allow_head=True)
        if git_output(root, "rev-parse", "--is-shallow-repository") == "true":
            raise ScanError("full_history_requires_complete_clone")
        scan_args = ["--log-opts=--all --full-history --no-ext-diff --no-textconv"]
    else:
        tip = resolve_revision(root, head, allow_head=True)
        start = resolve_revision(root, base)
        # A..B visits every submitted commit, including subsequently deleted leaks.
        scan_args = [
            f"--log-opts=--full-history --no-ext-diff --no-textconv {start}..{tip}"
        ]

    with tempfile.TemporaryDirectory(prefix="secrets-scan-") as directory:
        private_dir = Path(directory)
        # Gitleaks 8.30.1 unconditionally loads source/.gitleaksignore even when
        # --gitleaks-ignore-path is provided. A private Git view reuses the exact
        # object database and index without copying or modifying the repository.
        # Neither the target's ignore file nor its inline allows can hide leaks.
        git_dir = git_output(root, "rev-parse", "--absolute-git-dir")
        if "\n" in git_dir or "\r" in git_dir:
            raise ScanError("unsupported_git_directory")
        view = private_dir / "repository"
        view.mkdir(mode=0o700)
        (view / ".git").write_text(f"gitdir: {git_dir}\n", encoding="utf-8")
        if (
            Path(git_output(view, "rev-parse", "--absolute-git-dir")).resolve()
            != Path(git_dir).resolve()
        ):
            raise ScanError("git_view_validation_failed")
        report = private_dir / "report.json"
        ignore = private_dir / "empty-ignore"
        for path in (report, ignore):
            descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            os.close(descriptor)
        command = [
            binary,
            "git",
            *scan_args,
            "--config",
            str(config_path.resolve()),
            "--gitleaks-ignore-path",
            str(ignore),
            "--ignore-gitleaks-allow",
            "--redact=100",
            "--no-banner",
            "--no-color",
            "--log-level",
            "error",
            "--report-format",
            "json",
            "--report-path",
            str(report),
            "--timeout",
            str(TIMEOUT_SECONDS),
            str(view),
        ]
        try:
            result = subprocess.run(
                command,
                cwd=view,
                env=clean_environment(),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
                timeout=TIMEOUT_SECONDS + 30,
            )
        except (OSError, subprocess.SubprocessError) as error:
            raise ScanError("scanner_unavailable_or_timed_out") from error
        if result.returncode not in (0, 1):
            raise ScanError("scanner_failed")
        try:
            if report.stat().st_size > MAX_REPORT_BYTES:
                raise ScanError("scanner_report_too_large")
            findings = json.loads(report.read_text(encoding="utf-8"))
        except (OSError, ValueError) as error:
            raise ScanError("invalid_scanner_report") from error
        if not isinstance(findings, list):
            raise ScanError("invalid_scanner_report")
        if result.returncode == 1 and not findings:
            raise ScanError("scanner_failed_without_findings")
        summary = summarise(findings, root)
        summary["mode"] = mode
        return (1 if findings else 0), summary


def main(argv: list[str] | None = None) -> int:
    parser = SafeParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--base", help="Full base commit SHA; scans every commit in base..head"
    )
    parser.add_argument("--head", default="HEAD", help="HEAD or a full commit SHA")
    parser.add_argument(
        "--staged",
        action="store_true",
        help="Scan the staged index, including an initial commit",
    )
    parser.add_argument(
        "--full-history",
        action="store_true",
        help="Scan all locally reachable refs; requires a complete clone",
    )
    parser.add_argument(
        "--binary", default="gitleaks", help="Verified Gitleaks binary path"
    )
    try:
        args = parser.parse_args(argv)
        code, summary = scan(**vars(args))
    except ScanError as error:
        code, summary = (
            2,
            {"scanner": "gitleaks", "status": "error", "error": str(error)},
        )
    except (OSError, ValueError, subprocess.SubprocessError):
        code, summary = (
            2,
            {"scanner": "gitleaks", "status": "error", "error": "scan_io_failed"},
        )
    print(json.dumps(summary, ensure_ascii=True, sort_keys=True))
    return code


if __name__ == "__main__":
    sys.exit(main())
