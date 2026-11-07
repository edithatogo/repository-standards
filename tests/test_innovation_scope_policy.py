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

    def test_game_runtime_has_one_library_owner_and_keeps_application_separate(self):
        item = self.policy['capabilities'].get('game-runtime', {})
        self.assertEqual(item.get('kind'), 'library')
        self.assertEqual(item.get('repository'), 'edithatogo/paignia')
        self.assertEqual(item.get('incubator_repository'), 'edithatogo/new-drug-reimbursement-game')
        self.assertEqual(item.get('source_paths'), ['crates/paignia-core', 'crates/paignia-solve'])
        self.assertEqual(item.get('display_name'), 'Paignia')
        self.assertEqual(item.get('identity_status'), 'chosen-name-publication-checks-pending')
        self.assertTrue(item.get('standalone_repository_created', False))
        self.assertFalse(item.get('packages_published', True))
        self.assertFalse(item.get('static_solver_requires_simulator', True))
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

    def test_minimal_cores_do_not_require_optional_providers(self):
        for key in ('kairos', 'innovate', 'voiage', 'game-runtime'):
            self.assertEqual(self.policy['capabilities'][key]['providers'], [])
        pairs = {(x['consumer'], x['provider']): x for x in self.policy['planned_adapters']}
        for pair in (('innovate', 'kairos'), ('innovate', 'game-runtime'),
                     ('game-runtime', 'kairos'), ('game-runtime', 'uogto-semantics')):
            self.assertTrue(pairs.get(pair, {}).get('optional', False))

    def test_scoped_release_units_do_not_waive_claimed_gates(self):
        rules = self.policy.get('scientific_refinements', {}).get('release', {})
        self.assertEqual(rules.get('units'), ['native-core', 'data-bindings', 'optional-integrations'])
        self.assertFalse(rules.get('optional_integration_blocks_core', True))
        self.assertTrue(rules.get('all_claimed_capabilities_require_evidence', False))
        self.assertTrue(rules.get('unresolved_obligations_retained', False))

    def test_game_results_and_information_isolation_are_required(self):
        rules = self.policy.get('scientific_refinements', {}).get('games', {})
        self.assertTrue(rules.get('player_observation_isolation', False))
        self.assertTrue(rules.get('offline_game_access_is_not_live_policy_access', False))
        fields = set(rules.get('required_result_fields', []))
        self.assertTrue({'game_class', 'information_structure', 'solution_concept',
                         'algorithm_version', 'status', 'tolerance', 'residuals',
                         'selection_rule', 'completeness_claim'} <= fields)
        self.assertTrue(rules.get('equilibrium_and_behavioural_predictions_distinct', False))

    def test_information_estimands_and_randomness_are_not_conflated(self):
        rules = self.policy.get('scientific_refinements', {}).get('decision', {})
        self.assertEqual(set(rules.get('estimands', [])),
                         {'conventional-evpi-evsi', 'net-benefit-of-research',
                          'strategic-information-value', 'social-information-value'})
        self.assertFalse(rules.get('clip_strategic_values_to_zero', True))
        self.assertTrue(rules.get('conditional_expectation_before_decision_maximisation', False))
        self.assertTrue(rules.get('monte_carlo_error_reported', False))
        axes = set(self.policy.get('scientific_refinements', {}).get('uncertainty_axes', []))
        self.assertEqual(axes, {'parameter', 'structural', 'simulation', 'measurement', 'strategic', 'numerical'})

    def test_adversarial_scientific_and_feature_validation(self):
        rules = self.policy.get('scientific_refinements', {}).get('validation', {})
        for field in ('prior_only_inference_negative_control', 'data_dependent_sbc',
                      'metamorphic_invariants', 'hype_scale_identification',
                      'medicines_observation_shocks', 'effective_and_known_dates',
                      'resolved_cargo_feature_closures', 'lazy_polars_equivalence'):
            self.assertTrue(rules.get(field, False), field)
        self.assertEqual(rules.get('fit_assessment_dimensions'),
                         ['execution', 'convergence', 'identification', 'prediction', 'causal'])


if __name__ == '__main__':
    unittest.main()
