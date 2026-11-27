import hashlib
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

import attested_evidence as evidence


RAW = b'{"fixture":"synthetic"}'
CONTEXT = dict(expected_digest=hashlib.sha256(RAW).hexdigest(),
               producer_repository='owner/example', producer_revision='a' * 40,
               workflow='collect.yml')


class AttestationTests(unittest.TestCase):
    def verify(self, raw=RAW, **changes):
        return evidence.authenticate_bytes(raw, **dict(CONTEXT, **changes))

    def test_native_verifier_receives_exact_bytes_and_trusted_constraints(self):
        def native(args, **kwargs):
            self.assertEqual(args[:3], ['gh', 'attestation', 'verify'])
            self.assertEqual(Path(args[3]).read_bytes(), RAW)
            expected = {'--repo': 'owner/example', '--source-digest': 'a' * 40,
                        '--signer-digest': 'a' * 40, '--source-ref': 'refs/heads/main',
                        '--signer-workflow': 'owner/example/.github/workflows/collect.yml',
                        '--hostname': 'github.com', '--predicate-type': 'https://slsa.dev/provenance/v1',
                        '--cert-oidc-issuer': 'https://token.actions.githubusercontent.com'}
            for flag, value in expected.items():
                self.assertEqual(args[args.index(flag) + 1], value)
            self.assertIn('--deny-self-hosted-runners', args)
            self.assertNotIn('--bundle', args)
            self.assertNotIn('--custom-trusted-root', args)
            self.assertEqual(kwargs['timeout'], 120)
            self.assertNotEqual(kwargs.get('shell'), True)
            self.assertEqual(kwargs['env']['GH_PROMPT_DISABLED'], '1')
            return subprocess.CompletedProcess(args, 0)
        with patch.object(evidence.subprocess, 'run', side_effect=native):
            result = self.verify()
        self.assertTrue(result['producer_attestation_verified'])
        self.assertFalse(result['snapshot_verified'])
        self.assertFalse(result['write_authorized'])
        self.assertEqual(result['artifact_sha256'], CONTEXT['expected_digest'])

    def test_substituted_bytes_never_reach_native_verification(self):
        with patch.object(evidence.subprocess, 'run') as run:
            with self.assertRaisesRegex(evidence.AttestationError, 'digest_mismatch'):
                self.verify(b'{"fixture":"different"}')
            run.assert_not_called()

    def test_untrusted_policy_arguments_rejected(self):
        with patch.object(evidence.subprocess, 'run') as run:
            for change in ({'producer_repository': '--owner/example'},
                           {'producer_revision': 'a' * 7}, {'workflow': '../collect.yml'},
                           {'workflow': 'https://example.org/collect.yml'},
                           {'expected_digest': 'invalid'}):
                with self.subTest(change=change), self.assertRaises(evidence.AttestationError):
                    self.verify(**change)
            run.assert_not_called()

    def test_nonzero_missing_binary_and_timeout_are_not_verified(self):
        for failure in (subprocess.CompletedProcess([], 1), FileNotFoundError('private-path'),
                        subprocess.TimeoutExpired(['gh'], 120)):
            kwargs = {'side_effect': failure} if isinstance(failure, Exception) else {'return_value': failure}
            with self.subTest(failure=type(failure)), patch.object(evidence.subprocess, 'run', **kwargs):
                with self.assertRaisesRegex(evidence.AttestationError, 'attestation_unverified'):
                    self.verify()

    def test_empty_and_oversized_inputs_are_rejected(self):
        with patch.object(evidence.subprocess, 'run') as run:
            for raw in (b'', b'x' * (evidence.MAX_BYTES + 1)):
                with self.assertRaisesRegex(evidence.AttestationError, 'artifact_size'):
                    self.verify(raw)
            run.assert_not_called()


class ReceiptBindingTests(unittest.TestCase):
    def inspect(self, **changes):
        import json
        from datetime import UTC, datetime
        data = dict(schema_version=1, repository='owner/target', revision='b' * 40,
                    generated_at='2026-11-27T09:30:00Z', result='pass',
                    checks=[dict(name='tests', result='pass')])
        data.update(changes)
        raw = json.dumps(data).encode()
        return evidence.inspect_attested_receipt(
            raw, expected_digest=hashlib.sha256(raw).hexdigest(),
            producer_repository='owner/example', producer_revision='a' * 40, workflow='collect.yml',
            repository='owner/target', revision='b' * 40, required_checks=['tests'],
            not_before=datetime(2026, 11, 27, 9, tzinfo=UTC),
            now=datetime(2026, 11, 27, 10, tzinfo=UTC))

    def test_same_byte_receipt_binding_does_not_establish_check_truth(self):
        with patch.object(evidence.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0)):
            result = self.inspect()
        self.assertTrue(result['producer_attestation_verified'])
        self.assertFalse(result['provenance_verified'])
        self.assertFalse(result['write_authorized'])
        self.assertEqual(result['result'], 'pass')

    def test_claimed_green_and_wrong_target_cannot_override_semantic_checks(self):
        from verify_receipt import ReceiptError
        with patch.object(evidence.subprocess, 'run') as run:
            for change in ({'revision': 'c' * 40}, {'checks': [dict(name='tests', result='fail')]},
                           {'generated_at': '2026-11-27T08:00:00Z'}, {'checks': [dict(name='other', result='pass')]}):
                with self.subTest(change=change), self.assertRaises(ReceiptError):
                    self.inspect(**change)
            run.assert_not_called()
