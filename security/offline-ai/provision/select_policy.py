"""Select an immutable policy allowing only its self-reference to differ."""
from __future__ import annotations

from pathlib import Path
import re
import subprocess
import sys


WORKFLOW = ".github/workflows/reusable-ai-sec-pipeline.yml"
PIN = re.compile(rb"^          ref: ([0-9a-f]{40})$", re.MULTILINE)
FAILURE = "Runtime policy source verification failed"


class PolicySourceError(RuntimeError):
    """A fixed failure without source contents or caller arguments."""


def _git(root, *arguments):
    try:
        return subprocess.run(
            ["git", "--no-replace-objects", "-C", str(root), *arguments],
            check=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            timeout=30,
        ).stdout
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        raise PolicySourceError(FAILURE) from None


def _without_pin(contents):
    matches = list(PIN.finditer(contents))
    if len(matches) != 1:
        raise PolicySourceError(FAILURE)
    match = matches[0]
    start, end = match.span(1)
    # Normalize only the SHA bytes, preserving whitespace, comments, line
    # endings and every other byte of both committed workflow versions.
    normalized = contents[:start] + b"<POLICY-SHA>" + contents[end:]
    return match.group(1).decode("ascii"), normalized


def select_policy(root):
    """Return the source SHA only when the committed source identities match."""
    if _git(root, "status", "--porcelain", "--untracked-files=all"):
        raise PolicySourceError(FAILURE)
    pin, head_workflow = _without_pin(_git(root, "show", "HEAD:" + WORKFLOW))
    _git(root, "merge-base", "--is-ancestor", pin, "HEAD")
    changed = set(_git(root, "diff", "--name-only", "-z", pin, "HEAD", "--").split(b"\0"))
    if changed - {b"", WORKFLOW.encode("ascii")}:
        raise PolicySourceError(FAILURE)
    _, source_workflow = _without_pin(_git(root, "show", pin + ":" + WORKFLOW))
    if source_workflow != head_workflow:
        raise PolicySourceError(FAILURE)
    return pin


def main(argv=None):
    try:
        arguments = sys.argv[1:] if argv is None else argv
        if len(arguments) != 3:
            raise PolicySourceError(FAILURE)
        root, temporary, output = map(Path, arguments)
        root = root.resolve(strict=True)
        temporary = temporary.resolve(strict=True)
        pin = select_policy(root)
        policy = temporary / "offline-qualified-policy"
        _git(root, "worktree", "add", "--detach", str(policy), pin)
        with output.open("a", encoding="utf-8") as stream:
            stream.write(f"path={policy}\nsha={pin}\n")
    except (PolicySourceError, OSError):
        print(FAILURE, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
