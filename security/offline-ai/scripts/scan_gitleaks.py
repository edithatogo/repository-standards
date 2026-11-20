"""Run pinned Gitleaks rules against the isolated checkout and its history."""

from __future__ import annotations

import os
import sys
from importlib import import_module
from pathlib import Path

# The policy mount is trusted and read-only. Do not import from the consumer.
POLICY = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(POLICY / "scripts"))
secrets_scan = import_module("secrets_scan")

ROOT = Path("/work")
CONFIG = POLICY / "security" / "offline-ai" / ".gitleaks.toml"


def main() -> int:
    """Scan complete history and verify the commit range when supplied."""
    event = os.environ.get("EVENT_NAME", "")
    base = os.environ.get("BASE_SHA", "")
    try:
        status, _summary = secrets_scan.scan(
            ROOT, full_history=True, config_path=CONFIG, offline_container=True
        )
        if status or event not in {"pull_request", "push"}:
            return status
        if event == "push" and base == "0" * 40:
            return 0
        if not base:
            return 2
        status, _summary = secrets_scan.scan(
            ROOT, base=base, config_path=CONFIG, offline_container=True
        )
        return status
    except secrets_scan.ScanError:
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
