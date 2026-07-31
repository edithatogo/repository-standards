#!/usr/bin/env python3
"""Simulate profile-policy changes against a conformance snapshot without writes."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--audit", type=Path, required=True)
    parser.add_argument("--profiles", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    audit = json.loads(args.audit.read_text(encoding="utf-8-sig"))
    profiles = json.loads(args.profiles.read_text(encoding="utf-8-sig"))
    supply = profiles["supply_chain_profiles"]
    impacts = []
    for row in audit["repositories"]:
        profile = dict(profiles["profiles"][row["profile"]])
        while "extends" in profile:
            parent_name = profile.pop("extends")
            profile = {**profiles["profiles"][parent_name], **profile}
        required = set(supply[profile.get("supply_chain", "baseline")])
        missing = sorted(control for control in required if not row["controls"].get(control))
        if missing:
            impacts.append({"repository": row["repository"], "new_failures": missing})
    payload = {
        "schema_version": 1,
        "mode": "dry_run",
        "repository_count": len(audit["repositories"]),
        "affected_repository_count": len(impacts),
        "impacts": impacts,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: payload[k] for k in payload if k != "impacts"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
