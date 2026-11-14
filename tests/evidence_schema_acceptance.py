"""Executed explicitly in the hash-locked F01 schema qualification lane."""
import unittest
from pathlib import Path
import estate_evidence as e
import test_estate_evidence as cases

class SchemaAcceptanceTests(unittest.TestCase):
    snapshot = cases.PublicationTests.snapshot
    def test_public_schema_rejects_private_fields_and_bad_enum(self):
        report = e.public_report(self.snapshot())
        root = Path(__file__).resolve().parents[1]
        e.schema_check(report, root / 'schemas/estate-evidence-public.schema.json')
        for change in ({'repositories': ['owner/private']}, {'assurance': 'certified'}):
            candidate = dict(report, **change)
            with self.assertRaises(e.EvidenceError):
                e.schema_check(candidate, root / 'schemas/estate-evidence-public.schema.json')

    def test_private_schema_requires_provenance_and_all_observations(self):
        snapshot = self.snapshot()
        root = Path(__file__).resolve().parents[1]
        e.schema_check(snapshot, root / 'schemas/estate-evidence.schema.json')
        snapshot['reconciliation']['counts']['known_unavailable'] = 1
        snapshot['reconciliation']['unavailable'] = [{'repository': 'owner/reused',
            'repository_id': 99, 'state': 'unknown', 'reason': 'repository_identity_changed'}]
        e.schema_check(snapshot, root / 'schemas/estate-evidence.schema.json')
        del snapshot['repositories'][0]['observations']['protection']
        with self.assertRaises(e.EvidenceError):
            e.schema_check(snapshot, root / 'schemas/estate-evidence.schema.json')



class PipelineAcceptanceTests(unittest.TestCase):
    def test_cli_writes_valid_redacted_evidence_from_full_fake_api_sequence(self):
        import io
        import json
        import tempfile
        from contextlib import redirect_stdout
        from datetime import datetime
        from unittest.mock import patch
        repo = cases.repository(private=True)
        api = cases.FakeAPI([e.Reply(200, [repo]), e.Reply(200, [repo])] + cases.CollectorTests().replies())
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            registry = root / 'registry.json'
            registry.write_text(json.dumps({'repositories': [{'repository': 'owner/example', 'exceptions': []}]}))
            output = io.StringIO()
            with patch.object(e, 'API', return_value=api), patch.object(e, 'baselines', return_value=[]), \
                 patch.dict(e.os.environ, {'ESTATE_AUDIT_TOKEN': 'synthetic-only'}), \
                 patch.object(e, 'datetime') as clock, redirect_stdout(output):
                clock.now.return_value = cases.NOW
                clock.fromisoformat.side_effect = datetime.fromisoformat
                code = e.main(['--owner', 'owner', '--registry', str(registry), '--source-sha', cases.SHA,
                               '--private-output', str(root / 'private.json'), '--public-dir', str(root / 'public')])
            self.assertEqual(code, 0)
            report = json.loads(output.getvalue())
            self.assertEqual(report['counts']['observed_owned'], 1)
            self.assertEqual(report['counts']['private'], 1)
            self.assertNotIn('owner/example', output.getvalue())
            self.assertNotIn('synthetic-only', output.getvalue())
            self.assertTrue(report['inventory_complete_for_declared_scope'])
            self.assertEqual(report['controls']['enforcement']['pass'], 0)

    def test_historical_inputs_are_hashed_and_never_overwritten(self):
        import json
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            old = root / 'audits/latest/estate-conformance.json'
            old.parent.mkdir(parents=True)
            old.write_text(json.dumps({'generated_at': '2026-07-31T22:07:24Z', 'repository_count': 163}))
            privacy = root / 'conductor/tracks/privacy_secrets_rollout_20261110/metadata.json'
            privacy.parent.mkdir(parents=True)
            privacy.write_text(json.dumps({'inventory_counts': {'total': 303},
                                           'rollout_checkpoint': {'as_of': '2026-11-10T08:09:07Z'}}))
            before = (old.read_bytes(), privacy.read_bytes())
            result = e.baselines(root)
            self.assertEqual([item['count'] for item in result], [163, 303])
            self.assertFalse(any(item['compliance_trend_comparable'] for item in result))
            self.assertEqual(before, (old.read_bytes(), privacy.read_bytes()))


if __name__ == '__main__':
    unittest.main()
