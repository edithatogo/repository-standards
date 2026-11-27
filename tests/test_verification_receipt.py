import hashlib
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import UTC, datetime
from pathlib import Path

import verify_receipt as verifier


NOW = datetime(2026, 11, 27, 10, tzinfo=UTC)
CUTOFF = datetime(2026, 11, 27, 9, tzinfo=UTC)
REVISION = 'a' * 40
REPOSITORY = 'owner/example'


def receipt(**changes):
    return {'schema_version': 1, 'repository': REPOSITORY, 'revision': REVISION,
            'generated_at': '2026-11-27T09:30:00Z', 'result': 'pass',
            'checks': [{'name': 'tests', 'result': 'pass'},
                       {'name': 'security', 'result': 'pass'}], **changes}


class ReceiptTests(unittest.TestCase):
    def inspect(self, candidate=None, *, raw=None, **options):
        if raw is None:
            raw = json.dumps(receipt() if candidate is None else candidate).encode()
        arguments = {'expected_digest': hashlib.sha256(raw).hexdigest(),
                     'repository': REPOSITORY, 'revision': REVISION,
                     'required_checks': ['tests', 'security'],
                     'not_before': CUTOFF, 'now': NOW, **options}
        return verifier.inspect_receipt(raw, **arguments)

    def test_matching_complete_receipt_is_only_consistent_not_merge_authority(self):
        result = self.inspect()
        self.assertEqual(result['result'], 'pass')
        self.assertFalse(result['write_authorized'])
        self.assertFalse(result['provenance_verified'])

    def test_byte_substitution_cannot_use_original_digest(self):
        digest = hashlib.sha256(json.dumps(receipt()).encode()).hexdigest()
        with self.assertRaisesRegex(verifier.ReceiptError, 'digest_mismatch'):
            self.inspect(receipt(seed=42), expected_digest=digest)

    def test_wrong_repository_or_revision_is_rejected(self):
        for changes in ({'repository': 'owner/other'}, {'revision': 'b' * 40},
                        {'revision': 'a' * 7}):
            with self.subTest(changes=changes), self.assertRaises(verifier.ReceiptError):
                self.inspect(receipt(**changes))
        with self.assertRaises(verifier.ReceiptError):
            self.inspect(revision='a' * 7)

    def test_stale_future_and_naive_timestamps_fail(self):
        for value in ('2026-11-27T08:59:59Z', '2026-11-27T10:00:01Z',
                      '2026-11-27T09:30:00', 'invalid'):
            with self.subTest(value=value), self.assertRaises(verifier.ReceiptError):
                self.inspect(receipt(generated_at=value))
        self.assertEqual(self.inspect(receipt(generated_at='2026-11-27T19:00:00+10:00'))['result'], 'pass')

    def test_missing_duplicate_and_ambiguous_check_names_fail(self):
        for checks in ([{'name': 'tests', 'result': 'pass'}],
                       receipt()['checks'] * 2,
                       receipt()['checks'] + [{'name': 'security ', 'result': 'pass'}],
                       receipt()['checks'] + [{'name': '\nsecurity', 'result': 'pass'}]):
            with self.subTest(checks=checks), self.assertRaises(verifier.ReceiptError):
                self.inspect(receipt(checks=checks))
        for required in ([], ['tests', 'tests'], ['tests', '']):
            with self.subTest(required=required), self.assertRaises(verifier.ReceiptError):
                self.inspect(required_checks=required)

    def test_failure_or_skip_cannot_be_reported_as_pass(self):
        for status, expected in (('fail', 'fail'), ('skip', 'partial')):
            checks = [{'name': 'tests', 'result': 'pass'}, {'name': 'security', 'result': status}]
            with self.subTest(status=status):
                with self.assertRaisesRegex(verifier.ReceiptError, 'aggregate_mismatch'):
                    self.inspect(receipt(checks=checks))
                self.assertEqual(self.inspect(receipt(checks=checks, result=expected))['result'], expected)
        with self.assertRaisesRegex(verifier.ReceiptError, 'aggregate_mismatch'):
            self.inspect(receipt(result='partial'))

    def test_optional_skip_is_not_an_overall_pass(self):
        checks = receipt()['checks'] + [{'name': 'optional', 'result': 'skip'}]
        with self.assertRaisesRegex(verifier.ReceiptError, 'aggregate_mismatch'):
            self.inspect(receipt(checks=checks))
        self.assertEqual(self.inspect(receipt(checks=checks, result='partial'))['result'], 'partial')

    def test_schema_and_strict_json_reject_malformed_receipts(self):
        for raw in (b'{"result":"pass","result":"fail"}', b'[]', b'\xff', b'{',
                    json.dumps(receipt(schema_version=True)).encode(),
                    json.dumps(receipt(quality_metrics={'line_coverage_percent': float('nan')})).encode(),
                    json.dumps(receipt(checks=[{'name': 'tests', 'result': 'success'}])).encode(),
                    json.dumps(receipt(quality_metrics={'line_coverage_percent': 101})).encode(),
                    json.dumps(receipt(checks=receipt()['checks'] + [{'name': 'x', 'result': 'pass', 'duration_seconds': 0}])).replace('"duration_seconds": 0', '"duration_seconds": 1e999').encode()):
            with self.subTest(raw=raw), self.assertRaises(verifier.ReceiptError):
                self.inspect(raw=raw)

    def test_size_bound_is_enforced(self):
        with self.assertRaisesRegex(verifier.ReceiptError, 'receipt_size'):
            self.inspect(raw=b' ' * (verifier.MAX_BYTES + 1))

    def test_cli_exit_and_output_do_not_echo_untrusted_content(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'receipt.json'
            for doc, code in ((receipt(), 0),
                              (receipt(result='fail', checks=[{'name': 'tests', 'result': 'fail'}, {'name': 'security', 'result': 'pass'}]), 1),
                              (receipt(revision='untrusted-content'), 2)):
                raw = json.dumps(doc).encode()
                path.write_bytes(raw)
                args = [str(path), '--sha256', hashlib.sha256(raw).hexdigest(),
                        '--repository', REPOSITORY, '--revision', REVISION,
                        '--require-check', 'tests', '--require-check', 'security',
                        '--not-before', CUTOFF.isoformat()]
                out = io.StringIO()
                with redirect_stdout(out):
                    self.assertEqual(verifier.main(args, now=NOW), code)
                self.assertNotIn('untrusted-content', out.getvalue())
                self.assertFalse(json.loads(out.getvalue())['write_authorized'])
