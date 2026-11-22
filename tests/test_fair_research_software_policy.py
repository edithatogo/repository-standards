"""Offline tests for the opt-in FAIR research software profile."""

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class FAIRProfileTests(unittest.TestCase):
    def test_disabled_by_default_and_advisory(self):
        policy = json.loads((ROOT / "profiles/fair-research-software.json").read_text())
        self.assertTrue(policy["selection"]["missing_is_disabled"])
        self.assertFalse(policy["selection"]["automatic_rollout"])
        self.assertEqual(policy["mode"], "advisory")
        self.assertFalse(policy["governance"]["score_is_not_release_gate"])
        self.assertTrue(policy["controls"]["howfairis"]["hosted_run_required_for_acceptance"])

    def test_repository_entry_schema_does_not_require_fair(self):
        schema = json.loads((ROOT / "schemas/repository-entry.schema.json").read_text())
        self.assertNotIn("fair_software", schema["required"])
        field = schema["properties"]["fair_software"]
        self.assertEqual(field["properties"]["enabled"]["type"], "boolean")
        self.assertEqual(field["required"], ["enabled"])

    def test_external_action_pinned_to_commit(self):
        policy = json.loads((ROOT / "profiles/fair-research-software.json").read_text())
        sha = policy["controls"]["howfairis"]["pinned_action_commit"]
        self.assertEqual(len(sha), 40)
        self.assertTrue(all(c in "0123456789abcdef" for c in sha))


if __name__ == "__main__":
    unittest.main()
