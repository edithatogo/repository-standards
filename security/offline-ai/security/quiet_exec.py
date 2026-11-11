"""Run security controls without leaking prompts, findings or source into CI logs."""
from __future__ import annotations
import subprocess
import sys

_ALLOWED = frozenset({
    "gitleaks-history", "gitleaks-diff", "opengrep", "pytest",
    "promptfoo-mock", "promptfoo-agent", "asset-preflight",
    "network-preflight", "sast-fixtures", "gitleaks-fixtures",
})

def run(label: str, command: list[str]) -> int:
    if label not in _ALLOWED or not command:
        print("Security control could not be started", file=sys.stderr)
        return 2
    try:
        result = subprocess.run(command, stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL, stdin=None,
                                timeout=1800, check=False)
        if result.returncode == 0:
            return 0
    except (OSError, subprocess.TimeoutExpired):
        pass
    print(f"Security control failed: {label}", file=sys.stderr)
    return 2

if __name__ == "__main__":
    if len(sys.argv) < 3:
        raise SystemExit(2)
    raise SystemExit(run(sys.argv[1], sys.argv[2:]))
