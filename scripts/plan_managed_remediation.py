#!/usr/bin/env python3
"""Create a bounded, reviewable remediation plan; never writes target repos."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


LOW_RISK = {
    "agents",
    "managed:AGENTS.md",
    "managed:CONTRIBUTING.md",
    "managed:SECURITY.md",
    "managed:renovate.json",
    "managed:.github/workflows/scorecard.yml",
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--audit", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=25)
    args = parser.parse_args()
    audit = json.loads(args.audit.read_text(encoding="utf-8-sig"))
    operations = []
    for row in audit["repositories"]:
        controls = sorted(LOW_RISK.intersection(row["violations"]))
        if controls:
            operations.append(
                {
                    "repository": row["repository"],
                    "delivery": "managed_pull_request",
                    "controls": controls,
                    "automerge_eligible": True,
                    "preconditions": [
                        "no target-file content is overwritten",
                        "stable required checks are known and pass",
                        "GitHub App installation covers the repository",
                    ],
                }
            )
    payload = {
        "schema_version": 1,
        "mode": "plan_only",
        "total_candidates": len(operations),
        "bounded_operations": operations[: args.limit],
        "deferred_candidates": max(0, len(operations) - args.limit),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in payload.items() if k != "bounded_operations"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
