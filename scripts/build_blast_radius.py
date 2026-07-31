#!/usr/bin/env python3
"""Build a profile-to-repository dependency graph for rollout ordering."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--registry", type=Path, required=True)
    parser.add_argument("--canaries", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    registry = json.loads(args.registry.read_text(encoding="utf-8-sig"))
    canaries = json.loads(args.canaries.read_text(encoding="utf-8-sig"))
    canary_by_profile = {row["profile"]: row["repository"] for row in canaries["canaries"]}
    profiles: dict[str, list[str]] = {}
    for row in registry["repositories"]:
        profiles.setdefault(row["profile"], []).append(row["repository"])
    graph = {
        profile: {
            "canary": canary_by_profile.get(profile),
            "blast_radius": len(repositories),
            "repositories": sorted(repositories),
            "rollout_gate": "canary_success" if profile in canary_by_profile else "manual_profile_canary_required",
        }
        for profile, repositories in sorted(profiles.items())
    }
    payload = {"schema_version": 1, "profiles": graph}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
