"""Credential boundary regression checks for the F01 hosted collector."""
from __future__ import annotations

import unittest
from pathlib import Path


class EstateWorkflowTests(unittest.TestCase):
    def test_live_collector_never_mints_implicitly_installation_wide_app_token(self):
        workflow = (Path(__file__).resolve().parents[1] / '.github/workflows/estate-conformance.yml').read_text()
        self.assertNotIn('actions/create-github-app-token@', workflow)
        self.assertNotIn('ESTATE_AUTOMATION_APP_PRIVATE_KEY', workflow)
        self.assertNotIn('zizmor: ignore', workflow)
        self.assertIn('ESTATE_AUDIT_TOKEN: ${{ secrets.ESTATE_AUDIT_TOKEN }}', workflow)

    def test_live_collector_keeps_main_only_and_no_default_token_fallback(self):
        workflow = (Path(__file__).resolve().parents[1] / '.github/workflows/estate-conformance.yml').read_text()
        collection = workflow.split('  reconcile-estate:', 1)[1].split('  publish-aggregate:', 1)[0]
        self.assertIn("if: github.event_name != 'pull_request' && github.ref == 'refs/heads/main'", collection)
        self.assertNotIn('${{ github.token }}', collection)
        self.assertNotIn('issues: write', collection)
        self.assertNotIn('||', collection)
        self.assertIn('if: always()', collection)
        self.assertIn('f01-private/estate-evidence.json', collection)


if __name__ == '__main__':
    unittest.main()
