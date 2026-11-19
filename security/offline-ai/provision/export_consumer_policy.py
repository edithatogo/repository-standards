"""Export a clean, immutable policy snapshot for the offline consumer container."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import types

ROOT = Path(__file__).resolve().parents[3]
QUALIFIER = ROOT / "security/offline-ai/docker/qualify_image.py"
SHA = re.compile(r"[0-9a-f]{40}\Z")


class ExportError(RuntimeError):
    """A fixed public error without repository contents or local paths."""


def git_environment() -> dict[str, str]:
    env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    env.update(
        GIT_CONFIG_NOSYSTEM="1",
        GIT_CONFIG_GLOBAL=os.devnull,
        GIT_CONFIG_COUNT="2",
        GIT_CONFIG_KEY_0="core.hooksPath",
        GIT_CONFIG_VALUE_0=os.devnull,
        GIT_CONFIG_KEY_1="core.fsmonitor",
        GIT_CONFIG_VALUE_1="false",
        GIT_NO_REPLACE_OBJECTS="1",
        GIT_NO_LAZY_FETCH="1",
        GIT_TERMINAL_PROMPT="0",
        GIT_OPTIONAL_LOCKS="0",
    )
    return env


def git(*arguments: str) -> bytes:
    try:
        result = subprocess.run(
            ["git", "--no-replace-objects", "-C", str(ROOT), *arguments],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            env=git_environment(),
            check=False,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError) as error:
        raise ExportError("policy_source_unavailable") from error
    if result.returncode:
        raise ExportError("policy_source_unavailable")
    return result.stdout


def export(commit: str, destination: Path) -> None:
    if not SHA.fullmatch(commit) or not destination.is_absolute():
        raise ExportError("invalid_snapshot_request")
    try:
        parent = destination.parent.resolve(strict=True)
        output = parent / destination.name
        if (
            parent.is_relative_to(ROOT)
            or output.exists()
            or output.is_symlink()
            or destination.name in {"", ".", ".."}
        ):
            raise ExportError("invalid_snapshot_request")
        if git("rev-parse", "HEAD").strip() != commit.encode("ascii"):
            raise ExportError("policy_source_mismatch")
        if git("status", "--porcelain", "--untracked-files=all"):
            raise ExportError("policy_source_dirty")
        # Execute the exact committed helper, never an ignored checkout pyc.
        source = git("show", commit + ":security/offline-ai/docker/qualify_image.py")
        qualifier = types.ModuleType("offline_qualifier")
        qualifier.__file__ = str(QUALIFIER)
        exec(compile(source, str(QUALIFIER), "exec"), qualifier.__dict__)
        # The image qualifier already archives committed bytes and rejects links.
        with qualifier.policy_snapshot(commit, env=git_environment()) as snapshot:
            if (snapshot / ".git").exists() or (snapshot / ".git").is_symlink():
                raise ExportError("policy_snapshot_invalid")
            shutil.copytree(snapshot, output)
        if git("rev-parse", "HEAD").strip() != commit.encode("ascii") or git(
            "status", "--porcelain", "--untracked-files=all"
        ):
            raise ExportError("policy_source_changed")
    except ExportError:
        raise
    except (OSError, RuntimeError, shutil.Error, SyntaxError, ImportError, ValueError) as error:
        raise ExportError("policy_snapshot_failed") from error


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--destination", required=True, type=Path)
    args = parser.parse_args()
    try:
        export(args.commit, args.destination)
    except ExportError as error:
        print("Consumer policy snapshot failed: " + str(error), file=sys.stderr)
        return 2
    print("Consumer policy snapshot ready")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
