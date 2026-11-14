"""Bounded cache qualification; repository findings remain independent."""
from __future__ import annotations

import copy
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

import simulate_policy_impact as impact


class CountingSupply(dict):
    def __init__(self, values):
        super().__init__(values)
        self.reads = 0

    def __getitem__(self, key):
        self.reads += 1
        return super().__getitem__(key)


class PolicyImpactCacheTests(unittest.TestCase):
    def run_simulation(self, audit, profiles):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            audit_path = root / "audit.json"
            profiles_path = root / "profiles.json"
            output = root / "out" / "impact.json"
            audit_text = json.dumps(audit)
            profiles_text = json.dumps(profiles)
            audit_path.write_text(audit_text, encoding="utf-8")
            profiles_path.write_text(profiles_text, encoding="utf-8")
            argv = ["impact", "--audit", str(audit_path), "--profiles", str(profiles_path),
                    "--output", str(output)]
            with patch("sys.argv", argv), redirect_stdout(io.StringIO()):
                self.assertEqual(impact.main(), 0)
            self.assertEqual(audit_path.read_text(encoding="utf-8"), audit_text)
            self.assertEqual(profiles_path.read_text(encoding="utf-8"), profiles_text)
            return json.JSONDecoder().decode(output.read_text(encoding="utf-8"))

    def test_repeated_profiles_resolve_once_but_keep_per_repository_findings(self):
        supply = CountingSupply({"baseline": ["signature", "sbom"]})
        profiles = {"profiles": {"python": {}, "rust": {}}, "supply_chain_profiles": supply}
        audit = {"repositories": [
            {"repository": "owner/a", "profile": "python", "controls": {"sbom": True}},
            {"repository": "owner/b", "profile": "python", "controls": {"signature": True}},
            {"repository": "owner/c", "profile": "rust", "controls": {"sbom": True, "signature": True}},
            {"repository": "owner/d", "profile": "rust", "controls": {}},
        ]}
        with patch.object(impact.json, "loads", side_effect=[audit, profiles]):
            result = self.run_simulation(audit, profiles)
        self.assertEqual(result["impacts"], [
            {"repository": "owner/a", "new_failures": ["signature"]},
            {"repository": "owner/b", "new_failures": ["sbom"]},
            {"repository": "owner/d", "new_failures": ["sbom", "signature"]},
        ])
        self.assertEqual(result["repository_count"], 4)
        self.assertEqual(result["affected_repository_count"], 3)
        self.assertEqual(supply.reads, 2)

    def test_inherited_override_is_preserved_without_mutating_profiles(self):
        profiles = {"profiles": {
            "base": {"supply_chain": "baseline"},
            "middle": {"extends": "base"},
            "leaf": {"extends": "middle", "supply_chain": "published"},
        }, "supply_chain_profiles": {"baseline": ["base"], "published": ["z", "a", "z"]}}
        before = copy.deepcopy(profiles)
        audit = {"repositories": [
            {"repository": "owner/a", "profile": "leaf", "controls": {}},
            {"repository": "owner/b", "profile": "leaf", "controls": {"a": True}},
        ]}
        with patch.object(impact.json, "loads", side_effect=[audit, profiles]):
            result = self.run_simulation(audit, profiles)
        self.assertEqual(profiles, before)
        self.assertEqual(result["impacts"], [
            {"repository": "owner/a", "new_failures": ["a", "z"]},
            {"repository": "owner/b", "new_failures": ["z"]},
        ])

    def test_cache_does_not_survive_a_second_invocation(self):
        audit = {"repositories": [{"repository": "owner/a", "profile": "python", "controls": {}}]}
        for control in ("old", "new"):
            with self.subTest(control=control):
                profiles = {"profiles": {"python": {}}, "supply_chain_profiles": {"baseline": [control]}}
                result = self.run_simulation(audit, profiles)
                self.assertEqual(result["impacts"][0]["new_failures"], [control])

    def test_empty_snapshot_retains_dry_run_schema(self):
        result = self.run_simulation({"repositories": []}, {"profiles": {}, "supply_chain_profiles": {}})
        self.assertEqual(result, {"schema_version": 1, "mode": "dry_run", "repository_count": 0,
                                  "affected_repository_count": 0, "impacts": []})

    def test_empty_requirement_set_does_not_leak_between_profiles(self):
        profiles = {"profiles": {"none": {"supply_chain": "none"}, "python": {}},
                    "supply_chain_profiles": {"none": [], "baseline": ["sbom"]}}
        audit = {"repositories": [
            {"repository": "owner/a", "profile": "none", "controls": {}},
            {"repository": "owner/b", "profile": "python", "controls": {"sbom": False}},
            {"repository": "owner/c", "profile": "none", "controls": {}},
        ]}
        self.assertEqual(self.run_simulation(audit, profiles)["impacts"],
                         [{"repository": "owner/b", "new_failures": ["sbom"]}])


if __name__ == "__main__":
    unittest.main()
