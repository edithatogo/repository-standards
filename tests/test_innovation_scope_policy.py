"""Central policy assertions; these do not certify consumer implementations."""
from __future__ import annotations

import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class InnovationScopePolicyTests(unittest.TestCase):
    def setUp(self):
        self.policy = json.loads((ROOT / 'profiles/scientific-native.json').read_text())

    def test_innovate_scope_preserves_origin_and_extensions(self):
        scope = self.policy['capabilities']['innovate']['owns']
        for required in ('innovation', 'policy diffusion', 'competition', 'substitution', 'hype'):
            self.assertIn(required, scope)

    def test_innovate_native_and_dataframe_contract(self):
        contract = self.policy.get('runtime_contracts', {}).get('innovate', {})
        self.assertEqual(contract.get('scientific_engine'), 'rust-only')
        self.assertEqual(contract.get('tabular_engine'), 'polars')
        self.assertEqual(set(contract.get('unsupported_runtime_packages', [])), {'pandas', 'xarray'})
        self.assertFalse(contract.get('host_fallback', True))
        self.assertFalse(contract.get('runtime_accepted', True))

    def test_vop_is_a_poc_and_generic_methods_promote_to_voiage(self):
        item = self.policy['capabilities']['vop_poc_nz']
        self.assertEqual(item.get('lifecycle_role'), 'proof-of-concept')
        self.assertEqual(item.get('generic_decision_capability_owner'), 'voiage')
        self.assertIn('voiage', item['providers'])

    def test_game_runtime_is_one_incubated_library_not_an_application_dependency(self):
        item = self.policy['capabilities'].get('game-runtime', {})
        self.assertEqual(item.get('kind'), 'library')
        self.assertEqual(item.get('repository'), 'edithatogo/new-drug-reimbursement-game')
        self.assertEqual(item.get('source_paths'), ['crates/uogto-game-core', 'crates/uogto-game-solve'])
        self.assertEqual(item.get('status'), 'extraction-and-qualification-required')
        self.assertNotIn('new-drug-reimbursement-game', item.get('providers', []))

    def test_feedback_is_artifact_only_and_forward_adapter_is_optional(self):
        self.assertNotIn('voiage', self.policy['capabilities']['innovate']['providers'])
        matches = [x for x in self.policy.get('planned_adapters', [])
                   if x.get('consumer') == 'voiage' and x.get('provider') == 'innovate']
        self.assertEqual(len(matches), 1)
        self.assertTrue(matches[0].get('optional', False))
        self.assertEqual(self.policy.get('decision_feedback'), 'versioned-artifacts-through-application-orchestration')

    def test_frontier_policy_does_not_claim_alignment_already_passed(self):
        self.assertEqual(self.policy.get('status'), 'approved-policy-not-runtime-acceptance')
        self.assertEqual(self.policy.get('python'), '3.15.2')
        self.assertEqual(self.policy.get('candidate_checks'), ['security', 'build', 'numerical', 'consumer', 'resource'])
        self.assertFalse(self.policy.get('automatic_consumer_migration', True))


if __name__ == '__main__':
    unittest.main()
