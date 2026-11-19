"""Contracts for the proposed reusable SAST workflow; do not infer runtime qualification."""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class OpenGrepStandardContractTests(unittest.TestCase):
    def test_fixed_asset_and_fail_closed_workflow(self):
        policy = json.loads((ROOT / "profiles/opengrep-sast-pilot.json").read_text())
        workflow = (ROOT / ".github/workflows/reusable-opengrep-sast.yml").read_text()
        self.assertEqual(policy["stage"], "pilot")
        self.assertIn(policy["scanner"]["asset_sha256"], workflow)
        for expected in ("workflow_call:", "persist-credentials: false",
                         "contents: read", "--strict --error", "--config p/python",
                         'test "$detected" -eq 1', "SCANNER_EXIT", "report.json"):
            self.assertIn(expected, workflow)
        self.assertNotIn("continue-on-error: true", workflow)
        self.assertNotIn("upload-artifact", workflow)
        self.assertNotIn("security-events: write", workflow)

    def test_incomplete_scan_receipts_cannot_pass(self):
        workflow = (ROOT / ".github/workflows/reusable-opengrep-sast.yml").read_text()
        for expected in ("not isinstance(results, list)", "not isinstance(errors, list)",
                         "not isinstance(scanned, list) or not scanned",
                         'if errors or int(os.environ["SCANNER_EXIT"]) != 0:'):
            self.assertIn(expected, workflow)

    def test_no_unsupported_language_promotion(self):
        policy = json.loads((ROOT / "profiles/opengrep-sast-pilot.json").read_text())
        self.assertEqual(policy["supported_profiles"], ["python"])
        self.assertFalse(policy["rule_source"]["immutable"])
        self.assertFalse(policy["rule_source"]["semgrep_parity_verified"])
        self.assertIn("rust", policy["not_yet_qualified"])


if __name__ == "__main__":
    unittest.main()
