"""Run actual Opengrep CLI against fail-open and fail-closed synthetic fixtures.

This MUST run within the isolated image. It deliberately does not use mock SAST.
"""
from __future__ import annotations
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures" / "taint"
RULES = ROOT / ".opengrep" / "rules.yaml"

def verify() -> None:
    result = subprocess.run(
        ["opengrep", "scan", "--json", "--config", str(RULES), str(FIXTURES)],
        capture_output=True, text=True, timeout=120, check=False,
    )
    if result.returncode != 0:
        raise RuntimeError("Opengrep fixture invocation or parsing failed")
    try:
        payload = json.loads(result.stdout)
        if payload.get("errors"):
            raise ValueError("Rules were rejected")
        hits = payload["results"]
        observed = {Path(item["path"]).name for item in hits}
    except (ValueError, TypeError, KeyError) as exc:
        raise RuntimeError("Opengrep fixture report invalid") from None
    required = {"python_bad.py", "typescript_bad.ts", "rust_bad.rs"}
    clean = {"python_good.py", "typescript_good.ts", "rust_good.rs"}
    if not required.issubset(observed) or (observed & clean):
        raise RuntimeError("Opengrep rule regression: unexpected coverage on synthetic fixtures")

if __name__ == "__main__":
    try:
        verify()
    except (RuntimeError, subprocess.TimeoutExpired) as exc:
        print("SAST fixture qualification failed", file=sys.stderr)
        raise SystemExit(2)
