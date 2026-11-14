"""Adversarial review counterexamples for F01's transport and claim boundary."""
from __future__ import annotations

import io
import unittest
import urllib.error
from unittest.mock import Mock, patch

import estate_evidence as e
import test_estate_evidence as cases


class ReviewTests(unittest.TestCase):
    def test_calendar_overflow_is_invalid_exception_not_collector_crash(self):
        result = e.exception_observation([{'control': 'ci', 'review_after': '9999-12-31'}], cases.NOW)
        self.assertEqual(result['state'], 'fail')
        self.assertEqual(result['details']['invalid'], 1)
        self.assertEqual(result['details']['active'], 0)

    def test_ambiguous_git_conflict_does_not_prove_empty_repository(self):
        row = e.collect_repo(cases.FakeAPI([e.Reply(409, None)]), cases.repository(), {}, cases.NOW)
        self.assertIsNone(row['empty'])
        self.assertEqual(row['observations']['current_ci']['state'], 'unknown')

    def test_name_cannot_disagree_with_owner_metadata(self):
        row = cases.repository(name='someone-else/repo', owner={'login': 'owner'})
        result = e.discover(cases.FakeAPI([e.Reply(200, [row])] * 2), 'owner')
        self.assertFalse(result['complete'])
        self.assertEqual(result['repositories'], [])

    def test_registry_stable_id_mismatch_cannot_apply_policy_to_recreated_name(self):
        old = {'repository': 'owner/example', 'repository_id': 99, 'exceptions': []}
        new = cases.repository(number=1)
        result = e.reconcile(cases.FakeAPI([e.Reply(200, new)]), [old], [new], 'owner', cases.NOW)
        self.assertEqual(result['counts']['known_unavailable'], 1)
        self.assertEqual(result['counts']['matched'], 0)
        self.assertEqual(result['entries'], {})

    def test_legacy_generated_issue_section_migrates_without_republishing_private_rows(self):
        old_start, old_end = '<!-- estate-conformance:start -->', '<!-- estate-conformance:end -->'
        body = 'Owner notes\n' + old_start + '\nprivate-legacy-fixture\n' + old_end + '\nOther notes'
        block = e.START + '\nAggregates\n' + e.END
        updated = e.reconcile_text(body, block)
        self.assertNotIn('private-legacy-fixture', updated)
        self.assertNotIn(old_start, updated)
        self.assertTrue(updated.startswith('Owner notes'))
        self.assertTrue(updated.endswith('Other notes'))
        self.assertEqual(e.reconcile_text(updated, block), updated)

    def test_forged_future_run_under_fresh_envelope_is_rejected(self):
        snapshot = cases.PublicationTests().snapshot()
        row = snapshot['repositories'][0]
        row['source_sha'], row['head_stable'] = cases.SHA, True
        obs = e.run_observation(cases.run(), cases.NOW, cases.SHA)
        obs['evidence_at'] = '2099-01-01T00:00:00+00:00'
        row['observations']['current_ci'] = e.combine([obs], cases.NOW, 'observed_checks_only_not_enforcement', cases.SHA)
        with self.assertRaises(e.EvidenceError):
            e.validate_snapshot(snapshot, cases.NOW)

    def test_present_protection_claim_requires_observed_configuration(self):
        snapshot = cases.PublicationTests().snapshot()
        snapshot['repositories'][0]['observations']['protection'] = e.observation(
            'pass', 'configured', cases.NOW, 'configuration_not_enforcement', cases.SHA)
        with self.assertRaises(e.EvidenceError):
            e.validate_snapshot(snapshot, cases.NOW)

    def test_permission_denial_is_not_retried_and_error_details_are_dropped(self):
        api = e.API('test-token')
        error = urllib.error.HTTPError('https://api.github.com/repos/owner/repo', 403,
                                       'secret-remote-error', {}, io.BytesIO(b'{"message":"secret"}'))
        api._opener = Mock()
        api._opener.open.side_effect = error
        with patch.object(e.time, 'sleep') as sleep:
            result = api.get('/repos/owner/repo')
        self.assertEqual(api._opener.open.call_count, 1)
        sleep.assert_not_called()
        self.assertEqual(result.reason, 'http_403')
        self.assertNotIn('secret', repr(result))

    def test_rate_limit_retry_is_bounded(self):
        api = e.API('test-token')
        api._opener = Mock()
        api._opener.open.side_effect = [urllib.error.HTTPError(
            'https://api.github.com/repos/owner/repo', 429, 'rate limit', {}, io.BytesIO(b'')) for _ in range(4)]
        with patch.object(e.time, 'sleep') as sleep:
            result = api.get('/repos/owner/repo')
        self.assertEqual(api._opener.open.call_count, 4)
        self.assertEqual(sleep.call_count, 3)
        self.assertEqual(result.reason, 'rate_limited')

    def test_off_origin_redirect_never_receives_authorization(self):
        api = e.API('test-token')
        api._opener = Mock()
        api._opener.open.side_effect = urllib.error.HTTPError(
            'https://api.github.com/repos/owner/repo', 301, 'moved',
            {'Location': 'https://attacker.example/steal'}, io.BytesIO(b''))
        result = api.get('/repos/owner/repo')
        self.assertEqual(api._opener.open.call_count, 1)
        self.assertEqual(result.reason, 'unsafe_redirect')


if __name__ == '__main__':
    unittest.main()
