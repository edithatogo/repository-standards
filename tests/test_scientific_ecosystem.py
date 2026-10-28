from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

import scientific_ecosystem as science

ROOT = Path(__file__).resolve().parents[1]


class ScientificPolicyTests(unittest.TestCase):
    def setUp(self):
        self.policy = json.loads((ROOT / 'profiles/scientific-native.json').read_text())

    def test_checked_in_policy(self):
        self.assertEqual(science.validate_policy(self.policy), [])

    def test_rejects_cycle(self):
        self.policy['capabilities']['kairos']['providers'] = ['innovate']
        self.assertIn('dependency cycle', ' '.join(science.validate_policy(self.policy)))

    def test_rejects_unknown_provider(self):
        self.policy['capabilities']['kairos']['providers'] = ['missing']
        self.assertIn('unknown provider', ' '.join(science.validate_policy(self.policy)))

    def test_rejects_core_depending_on_application(self):
        self.policy['capabilities']['kairos']['providers'] = ['tobac']
        self.assertIn('application', ' '.join(science.validate_policy(self.policy)))

    def test_candidate_promotion_requires_every_gate(self):
        record = {'candidate': 'nightly-2026-10-29', 'source_revision': 'a' * 40,
                  'status': 'qualified', 'checks': {k: 'pass' for k in science.CANDIDATE_CHECKS}}
        self.assertEqual(science.validate_candidate(record), [])
        for gate in science.CANDIDATE_CHECKS:
            invalid = copy.deepcopy(record)
            invalid['checks'][gate] = 'skip'
            self.assertTrue(science.validate_candidate(invalid), gate)

    def test_older_dependency_requires_actionable_exception(self):
        record = {'candidate': 'latest', 'source_revision': 'a' * 40,
                  'status': 'blocked', 'checks': {}}
        self.assertTrue(science.validate_candidate(record))
        record['exception'] = {'blocker': 'fixture incompatibility', 'capability': 'replay',
                               'owner': 'kairos', 'revisit': 'upstream fix or 2026-11-05'}
        self.assertEqual(science.validate_candidate(record), [])

    def receipt(self):
        return {'repository': 'edithatogo/kairos', 'revision': 'a' * 40,
                'stage': 'runtime-build', 'command': ['cargo', 'test', '--locked'],
                'source_hashes': {'Cargo.lock': 'b' * 64}, 'toolchains': {'rust': '1.99.1'},
                'runner': 'linux-x86_64', 'cache_state': 'cold', 'concurrency': 2,
                'started_at': '2026-10-29T00:00:00Z', 'finished_at': '2026-10-29T00:01:00Z',
                'result': 'pass', 'exit_code': 0, 'stop_reason': 'completed',
                'measurement': {'memory_method': 'descendant-rss', 'interval_seconds': 2,
                                'peak_rss_bytes': 1024, 'disk_growth_bytes': 2048,
                                'limitations': ['sampled peaks may miss short spikes']}}

    def test_passing_resource_receipt(self):
        self.assertEqual(science.validate_receipt(self.receipt()), [])

    def test_no_pass_on_stop_or_nonzero_exit(self):
        for key, value in [('exit_code', 1), ('stop_reason', 'oom'), ('stop_reason', 'timeout')]:
            record = self.receipt()
            record[key] = value
            self.assertTrue(science.validate_receipt(record))

    def test_bootstrap_needs_requirement_and_stage0_disclosure(self):
        record = self.receipt()
        record['stage'] = 'compiler-bootstrap'
        self.assertTrue(science.validate_receipt(record))
        record.update(packaging_requirement='voiage/spack-dated-nightly',
                      bootstrap_binary='authenticated stage0 digest',
                      source_built_components=['rustc', 'llvm'])
        self.assertEqual(science.validate_receipt(record), [])

    def test_incomplete_or_nonfinite_measurements_rejected(self):
        for value in [-1, float('nan'), float('inf'), True]:
            record = self.receipt()
            record['measurement']['peak_rss_bytes'] = value
            self.assertTrue(science.validate_receipt(record))
        record = self.receipt()
        del record['source_hashes']
        self.assertTrue(science.validate_receipt(record))

    def test_process_group_not_accepted_as_descendant_proof(self):
        record = self.receipt()
        record['measurement']['memory_method'] = 'process-group-rss'
        self.assertTrue(science.validate_receipt(record))

    def test_missing_proof_is_not_zero(self):
        record = self.receipt()
        del record['measurement']['disk_growth_bytes']
        self.assertTrue(science.validate_receipt(record))

    def test_invalid_evidence_types_rejected(self):
        for key, value in [('toolchains', {'rust': None}), ('command', [''])]:
            record = self.receipt()
            record[key] = value
            self.assertTrue(science.validate_receipt(record))
        record = self.receipt()
        record['measurement']['limitations'] = [None]
        self.assertTrue(science.validate_receipt(record))
        record.update(stage='compiler-bootstrap', packaging_requirement=True,
                      bootstrap_binary=1, source_built_components={'rustc': True})
        self.assertTrue(science.validate_receipt(record))

    def test_planned_edges_enforce_same_ownership(self):
        for consumer, provider in [('kairos', 'tobac'), ('kairos', 'innovate'), ('kairos', 'missing')]:
            policy = copy.deepcopy(self.policy)
            policy['planned_adapters'].append(dict(consumer=consumer, provider=provider))
            self.assertTrue(science.validate_policy(policy))

    def test_missing_kind_is_structured_failure(self):
        del self.policy['capabilities']['innovate']['kind']
        self.assertIn('unknown kind', ' '.join(science.validate_policy(self.policy)))
