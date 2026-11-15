#!/usr/bin/env python3
"""Run both repository scanners and select a safe, explicit Git revision range."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path


def commit_sha(value: object) -> str:
    if not isinstance(value, str) or not re.fullmatch(
        r"[0-9a-fA-F]{40}|[0-9a-fA-F]{64}", value
    ):
        raise ValueError("invalid commit identifier")
    return value


def select_range(event: dict, event_name: str, mode: str) -> tuple[str | None, str]:
    """Full audits are explicit. Incremental events never silently lose their base."""
    if mode == "full" or event_name in {"schedule", "workflow_dispatch"}:
        return None, "HEAD"
    if event_name == "pull_request":
        return commit_sha(event["pull_request"]["base"]["sha"]), "HEAD"
    if event_name == "push":
        before = commit_sha(event["before"])
        return (None if set(before) == {"0"} else before), "HEAD"
    if event_name == "merge_group":
        return commit_sha(event["merge_group"]["base_sha"]), "HEAD"
    if not event_name:
        return None, "HEAD"
    raise ValueError("unsupported event")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--binary", default="gitleaks")
    parser.add_argument("--mode", choices=("auto", "full"), default="auto")
    parser.add_argument(
        "--profile", choices=("repository", "sensitive"), default="repository"
    )
    parser.add_argument("--base")
    parser.add_argument("--head", default="HEAD")
    parser.add_argument("--staged", action="store_true")
    args = parser.parse_args()
    try:
        if args.base:
            base, head = commit_sha(args.base), args.head
        elif args.staged:
            base, head = None, "HEAD"
        else:
            event_path = os.environ.get("GITHUB_EVENT_PATH")
            event = json.loads(Path(event_path).read_text()) if event_path else {}
            base, head = select_range(
                event, os.environ.get("GITHUB_EVENT_NAME", ""), args.mode
            )
            head = args.head
        if args.staged and args.head != "HEAD":
            raise ValueError("staged scanning does not accept a head override")
        if head != "HEAD":
            commit_sha(head)
        root = args.root.resolve(strict=True)
        common = ["--root", str(root), "--head", head]
        if base:
            common += ["--base", base]
        if args.staged:
            common += ["--staged"]
        scripts = Path(__file__).resolve().parent
        commands = [
            [
                sys.executable,
                "-I",
                str(scripts / "secrets_scan.py"),
                *common,
                "--binary",
                args.binary,
            ],
            [
                sys.executable,
                "-I",
                str(scripts / "privacy_scan.py"),
                *common,
                "--profile",
                args.profile,
            ],
        ]
        if not base and not args.staged:
            commands[0].append("--full-history")
        statuses: list[int] = []
        for command in commands:
            # Only the trusted wrappers may write safe output; never relay scanner stderr.
            result = subprocess.run(
                command, cwd=root, stderr=subprocess.DEVNULL, check=False, timeout=900
            )
            statuses.append(result.returncode)
        if any(code not in (0, 1) for code in statuses):
            return 2
        return 1 if 1 in statuses else 0
    except Exception:  # noqa: BLE001 - never print third-party exception data at the public CLI boundary
        print(json.dumps({"tool": "privacy-guard", "status": "scan_error"}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
