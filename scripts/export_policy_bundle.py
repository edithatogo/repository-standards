#!/usr/bin/env python3
"""Export an independently evaluable OPA/Rego policy data bundle."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


REGO = '''package repository_standards

default allow := false

deny contains message if {
  input.sole_developer != true
  message := "repository must retain the sole-developer posture"
}

deny contains message if {
  input.mandatory_human_approvals != 0
  message := "mandatory human approvals must be zero"
}

deny contains message if {
  some exception in input.exceptions
  not exception.review_after
  message := sprintf("exception for %s has no review_after", [exception.control])
}

allow if count(deny) == 0
'''


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profiles", type=Path, required=True)
    parser.add_argument("--registry", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    profiles = json.loads(args.profiles.read_text(encoding="utf-8-sig"))
    registry = json.loads(args.registry.read_text(encoding="utf-8-sig"))
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "repository_standards.rego").write_text(REGO, encoding="utf-8")
    (args.output_dir / "data.json").write_text(
        json.dumps({"profiles": profiles, "registry": registry}, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"repositories": len(registry["repositories"]), "format": "opa-bundle"}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
