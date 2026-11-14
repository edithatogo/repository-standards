"""F01 acceptance counterexamples: unavailable evidence is never success."""
from __future__ import annotations

import copy
import io
import json
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import estate_evidence as e

NOW = datetime(2026, 11, 14, 6, tzinfo=UTC)
SHA = 'a' * 40
OTHER = 'b' * 40


def repository(number=1, name='owner/example', **changes):
    result = dict(id=number, full_name=name, owner={'login': name.split('/')[0]},
                  private=False, fork=False, archived=False, disabled=False,
                  default_branch='main', created_at='2026-01-01T00:00:00Z',
                  pushed_at='2026-11-14T00:00:00Z')
    result.update(changes)
    return result


def run(**changes):
    result = dict(id=10, head_sha=SHA, workflow_id=20, event='schedule',
                  head_branch='main', status='completed', conclusion='success',
                  created_at='2026-11-14T00:00:00Z', updated_at='2026-11-14T00:01:00Z')
    result.update(changes)
    return result


class FakeAPI:
    def __init__(self, replies):
        self.replies = list(replies)
        self.paths = []

    def get(self, path):
        self.paths.append(path)
        if not self.replies:
            raise AssertionError('Unexpected request')
        reply = self.replies.pop(0)
        return reply


class PaginationTests(unittest.TestCase):
    def test_complete_multi_page_uses_bounded_numbered_pages(self):
        rows = [{'id': i} for i in range(1, 101)]
        api = FakeAPI([e.Reply(200, rows), e.Reply(200, [{'id': 101}])])
        result = e.pages(api, '/collection?sort=full_name')
        self.assertTrue(result.complete)
        self.assertEqual(len(result.items), 101)
        self.assertIn('page=2', api.paths[-1])
        self.assertIn('per_page=100', api.paths[-1])

    def test_explicit_next_link_on_short_page_is_followed(self):
        api = FakeAPI([e.Reply(200, [{'id': 1}], more=True), e.Reply(200, [{'id': 2}])])
        result = e.pages(api, '/collection')
        self.assertTrue(result.complete)
        self.assertEqual([x['id'] for x in result.items], [1, 2])

    def test_partial_response_retains_first_page_without_false_completeness(self):
        api = FakeAPI([e.Reply(200, [{'id': 1}], more=True), e.Reply(403, None)])
        result = e.pages(api, '/collection')
        self.assertFalse(result.complete)
        self.assertEqual(result.items, [{'id': 1}])
        self.assertIn('http_403', result.problems)

    def test_repeated_pages_are_bounded_and_deduplicated(self):
        api = FakeAPI([e.Reply(200, [{'id': 1}], more=True)] * 3)
        result = e.pages(api, '/collection')
        self.assertFalse(result.complete)
        self.assertEqual(result.items, [{'id': 1}])
        self.assertLessEqual(len(api.paths), 2)

    def test_duplicate_identity_with_changed_data_is_inconsistent(self):
        api = FakeAPI([e.Reply(200, [{'id': 1, 'x': 1}], more=True),
                       e.Reply(200, [{'id': 1, 'x': 2}])])
        self.assertFalse(e.pages(api, '/collection').complete)

    def test_total_mismatch_cannot_become_complete(self):
        for value in ({'total_count': 2, 'items': [{'id': 1}]},
                      {'total_count': 0, 'items': [{'id': 1}]}):
            with self.subTest(value=value):
                self.assertFalse(e.pages(FakeAPI([e.Reply(200, value)]), '/c', 'items').complete)

    def test_total_changing_across_pages_is_inconsistent(self):
        replies = [e.Reply(200, {'total_count': 2, 'items': [{'id': 1}]}, more=True),
                   e.Reply(200, {'total_count': 3, 'items': [{'id': 2}]})]
        self.assertFalse(e.pages(FakeAPI(replies), '/c', 'items').complete)

    def test_malformed_errors_and_missing_ids_fail_closed(self):
        for value in (None, {}, {'errors': ['sensitive'], 'items': []}, [None],
                      [{'name': 'missing-id'}], [{'id': True}]):
            with self.subTest(value=value):
                result = e.pages(FakeAPI([e.Reply(200, value)]), '/c')
                self.assertFalse(result.complete)
                self.assertNotIn('sensitive', str(result.problems))

    def test_page_budget_is_explicit(self):
        result = e.pages(FakeAPI([e.Reply(200, [{'id': 1}], more=True)]), '/c', max_pages=1)
        self.assertFalse(result.complete)
        self.assertIn('page_budget', result.problems)


class InventoryTests(unittest.TestCase):
    def test_stable_inventory_includes_private_forks_archives_and_disabled(self):
        rows = [repository(), repository(2, 'owner/private', private=True),
                repository(3, 'owner/fork', fork=True), repository(4, 'owner/old', archived=True),
                repository(5, 'owner/disabled', disabled=True), repository(6, 'other/not-owned')]
        result = e.discover(FakeAPI([e.Reply(200, rows)] * 2), 'owner')
        self.assertTrue(result['complete'])
        self.assertEqual(len(result['repositories']), 5)
        self.assertEqual(result['source'], 'authenticated_owned')
        self.assertIsNone(result['unobservable_owned_total'])

    def test_installation_scope_is_not_claimed_as_all_owned(self):
        rows = [repository()]
        api = FakeAPI([e.Reply(403, None), e.Reply(200, {'total_count': 1, 'repositories': rows}),
                       e.Reply(200, {'total_count': 1, 'repositories': rows})])
        result = e.discover(api, 'owner')
        self.assertTrue(result['complete'])
        self.assertEqual(result['source'], 'installation_accessible_owned')
        self.assertIsNone(result['unobservable_owned_total'])

    def test_public_fallback_is_partial_not_whole_estate(self):
        rows = [repository()]
        api = FakeAPI([e.Reply(403, None), e.Reply(403, None), e.Reply(200, rows), e.Reply(200, rows)])
        result = e.discover(api, 'owner')
        self.assertFalse(result['complete'])
        self.assertEqual(result['source'], 'public_only')

    def test_inventory_change_between_passes_is_explicit(self):
        api = FakeAPI([e.Reply(200, [repository()]),
                       e.Reply(200, [repository(), repository(2, 'owner/new')])])
        result = e.discover(api, 'owner')
        self.assertFalse(result['complete'])
        self.assertIn('inventory_changed', result['problems'])
        self.assertEqual(len(result['repositories']), 2)

    def test_empty_accessible_inventory_does_not_establish_whole_estate(self):
        result = e.discover(FakeAPI([e.Reply(200, [])] * 2), 'owner')
        self.assertFalse(result['complete'])
        self.assertIn('empty_inventory', result['problems'])

    def test_missing_classification_is_not_assumed_public_active(self):
        row = repository()
        del row['private']
        result = e.discover(FakeAPI([e.Reply(200, [row])] * 2), 'owner')
        self.assertFalse(result['complete'])
        self.assertIn('invalid_repository_metadata', result['problems'])

    def test_rename_reconciles_stable_id_and_preserves_new_creation_distinction(self):
        rows = [repository(1, 'owner/renamed'), repository(2, 'owner/old-unregistered'),
                repository(3, 'owner/new', created_at='2026-11-12T00:00:00Z')]
        registry = [{'repository': 'owner/old', 'repository_id': 1}]
        result = e.reconcile(FakeAPI([]), registry, rows, 'owner', NOW)
        self.assertEqual(result['counts']['renamed'], 1)
        self.assertEqual(result['counts']['unregistered'], 2)
        self.assertEqual(result['counts']['new_since_privacy_baseline'], 1)
        self.assertEqual(result['counts']['known_unavailable'], 0)

    def test_registry_without_id_resolves_alias_but_forbidden_is_not_deleted(self):
        rows = [repository(1, 'owner/renamed')]
        registry = [{'repository': 'owner/old'}, {'repository': 'owner/hidden'}]
        result = e.reconcile(FakeAPI([e.Reply(200, rows[0]), e.Reply(404, None)]),
                             registry, rows, 'owner', NOW)
        self.assertEqual(result['counts']['renamed'], 1)
        self.assertEqual(result['counts']['known_unavailable'], 1)
        self.assertEqual(result['unavailable'][0]['state'], 'unknown')
        self.assertNotIn('deleted', result['unavailable'][0]['reason'])

    def test_duplicate_registry_aliases_do_not_duplicate_missing_or_live_denominators(self):
        row = repository()
        registry = [{'repository': 'owner/example'}, {'repository': 'OWNER/EXAMPLE'}]
        result = e.reconcile(FakeAPI([]), registry, [row], 'owner', NOW)
        self.assertEqual(result['counts']['matched'], 1)
        self.assertEqual(result['counts']['duplicate_registry_entries'], 1)


class ObservationTests(unittest.TestCase):
    def test_exact_fresh_success_is_execution_not_enforcement(self):
        obs = e.run_observation(run(), NOW, expected_sha=SHA)
        self.assertEqual(obs['state'], 'pass')
        self.assertEqual(obs['level'], 'executed')
        self.assertEqual(obs['source_sha'], SHA)
        self.assertEqual(obs['run_id'], 10)

    def test_queued_cancelled_skipped_neutral_and_wrong_sha_never_pass(self):
        cases = [run(status='queued', conclusion=None), run(status='in_progress', conclusion=None),
                 run(conclusion='cancelled'), run(conclusion='skipped'), run(conclusion='neutral'),
                 run(head_sha=OTHER), run(head_sha=''), run(id=None)]
        for item in cases:
            with self.subTest(item=item):
                self.assertNotEqual(e.run_observation(item, NOW, expected_sha=SHA)['state'], 'pass')

    def test_executed_failure_is_separate_from_unknown(self):
        self.assertEqual(e.run_observation(run(conclusion='failure'), NOW)['state'], 'fail')
        self.assertEqual(e.run_observation(None, NOW)['state'], 'unknown')

    def test_freshness_including_future_and_invalid_timestamps(self):
        old = run(updated_at='2026-10-01T00:00:00Z')
        self.assertEqual(e.run_observation(old, NOW)['state'], 'stale')
        for stamp in ('yesterday', '2026-11-16T00:00:00Z', '2026-11-14T01:00:00'):
            self.assertEqual(e.run_observation(run(updated_at=stamp), NOW)['state'], 'unknown')

    def test_latest_run_not_latest_completed_success(self):
        items = [run(id=9), run(id=10, status='queued', conclusion=None,
                                created_at='2026-11-14T01:00:00Z')]
        obs = e.latest_schedule(items, NOW, workflow_id=20, branch='main')
        self.assertEqual(obs['state'], 'unknown')
        self.assertEqual(obs['run_id'], 10)

    def test_wrong_event_or_branch_cannot_prove_schedule_execution(self):
        for item in (run(event='push'), run(head_branch='feature')):
            self.assertEqual(e.latest_schedule([item], NOW, 20, 'main')['state'], 'unknown')

    def test_protection_requires_conclusive_reads_and_active_configuration(self):
        empty = e.Collection([], True, [])
        denied = e.Reply(403, None)
        self.assertEqual(e.protection_observation(empty, denied, NOW, SHA)['state'], 'unknown')
        ambiguous = e.Reply(404, {'message': 'Not Found'})
        self.assertEqual(e.protection_observation(empty, ambiguous, NOW, SHA)['state'], 'unknown')
        absent = e.Reply(404, {'message': 'Branch not protected'})
        self.assertEqual(e.protection_observation(empty, absent, NOW, SHA)['state'], 'fail')
        for enforcement in ('disabled', 'evaluate'):
            rules = e.Collection([{'id': 1, 'enforcement': enforcement}], True, [])
            self.assertNotEqual(e.protection_observation(rules, absent, NOW, SHA)['state'], 'pass')
        rules = e.Collection([{'id': 2, 'enforcement': 'active'}], True, [])
        obs = e.protection_observation(rules, denied, NOW, SHA)
        self.assertEqual(obs['state'], 'pass')
        self.assertEqual(obs['level'], 'configured')

    def test_exception_expiry_is_recomputed_at_observation_time(self):
        entries = [{'control': 'ci', 'review_after': '2026-11-14'}]
        self.assertEqual(e.exception_observation(entries, NOW)['state'], 'pass')
        self.assertEqual(e.exception_observation(entries, NOW + timedelta(days=1))['state'], 'fail')
        for entries in ([{'control': 'x'}], [{'control': 'x', 'review_after': None}],
                        [{'control': 'x', 'review_after': 'garbage'}]):
            self.assertEqual(e.exception_observation(entries, NOW)['state'], 'fail')

    def test_required_missing_check_and_nonterminal_latest_cannot_pass(self):
        checks = [{'id': 1, 'name': 'lint', 'app': {'id': 1}, 'head_sha': SHA,
                   'status': 'completed', 'conclusion': 'success', 'completed_at': '2026-11-14T00:00:00Z'}]
        collection = e.Collection(checks, True, [])
        statuses = e.Collection([], True, [])
        self.assertEqual(e.check_observation(collection, statuses, NOW, SHA, ['test'])['state'], 'unknown')
        self.assertEqual(e.check_observation(collection, statuses, NOW, SHA, ['lint'])['state'], 'pass')
        pending = dict(checks[0], id=2, status='queued', conclusion=None)
        collection.items.append(pending)
        self.assertNotEqual(e.check_observation(collection, statuses, NOW, SHA, ['lint'])['state'], 'pass')

    def test_partial_collection_or_no_checks_is_not_clean(self):
        for coll in (e.Collection([], True, []), e.Collection([], False, ['http_403'])):
            self.assertEqual(e.check_observation(coll, e.Collection([], True, []), NOW, SHA, [])['state'], 'unknown')


class PublicationTests(unittest.TestCase):
    def snapshot(self):
        row = e.empty_row(repository(private=True, name='owner/very-private-project'), NOW)
        row['observations']['current_ci'] = e.observation('unknown', 'observed', NOW,
                                                         'private-api-error', source_sha=SHA)
        return e.make_snapshot([row], {'source': 'authenticated_owned', 'complete': True,
                                      'problems': [], 'unobservable_owned_total': None},
                               {'counts': {'known_unavailable': 0, 'unregistered': 1, 'matched': 0,
                                           'renamed': 0, 'duplicate_registry_entries': 0,
                                           'new_since_privacy_baseline': 0}, 'unavailable': []},
                               NOW, SHA, 123, [])

    def test_public_projection_has_no_identities_paths_or_error_text(self):
        snapshot = self.snapshot()
        snapshot['repositories'][0]['extra'] = 'secret-marker'
        report = e.public_report(snapshot)
        text = json.dumps(report)
        for secret in ('very-private-project', 'private-api-error', 'secret-marker', 'owner/'):
            self.assertNotIn(secret, text)
        self.assertEqual(report['counts']['private'], 1)
        self.assertEqual(report['assurance'], 'not_certified')

    def test_snapshot_validation_rejects_duplicates_stale_and_forged_pass(self):
        snapshot = self.snapshot()
        e.validate_snapshot(snapshot, NOW)
        duplicate = copy.deepcopy(snapshot)
        duplicate['repositories'].append(copy.deepcopy(duplicate['repositories'][0]))
        with self.assertRaises(e.EvidenceError):
            e.validate_snapshot(duplicate, NOW)
        with self.assertRaises(e.EvidenceError):
            e.validate_snapshot(snapshot, NOW + timedelta(days=2))
        forged = copy.deepcopy(snapshot)
        forged['repositories'][0]['observations']['current_ci']['state'] = 'pass'
        with self.assertRaises(e.EvidenceError):
            e.validate_snapshot(forged, NOW)

    def test_drift_fingerprint_is_deterministic_and_ignores_observation_clock(self):
        first = self.snapshot()
        second = copy.deepcopy(first)
        second['generated_at'] = '2026-11-14T07:00:00+00:00'
        self.assertEqual(e.drift_key(first), e.drift_key(second))
        second['repositories'][0]['observations']['current_ci']['state'] = 'fail'
        self.assertNotEqual(e.drift_key(first), e.drift_key(second))

    def test_issue_reconciliation_is_bounded_idempotent_and_rejects_ambiguous_markers(self):
        block = e.START + '\naggregate only\n' + e.END
        body = 'Owner notes\n\n' + block + '\n\nOther notes'
        self.assertEqual(e.reconcile_text(body, block), body)
        self.assertEqual(e.reconcile_text('Owner notes', block).count(e.START), 1)
        with self.assertRaises(e.EvidenceError):
            e.reconcile_text(body + block, block)

    def test_private_evidence_is_mode_600_and_public_has_only_aggregate_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            e.write_outputs(self.snapshot(), root / 'private.json', root / 'public', NOW)
            self.assertEqual((root / 'private.json').stat().st_mode & 0o777, 0o600)
            for path in (root / 'public').iterdir():
                self.assertNotIn('very-private-project', path.read_text())
            self.assertEqual(sorted(p.name for p in (root / 'public').iterdir()),
                             ['CHECKSUMS.sha256', 'estate-evidence.json', 'estate-evidence.md'])

    def test_existing_output_or_symlink_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / 'private.json'
            target.write_text('keep')
            with self.assertRaises(e.EvidenceError):
                e.write_outputs(self.snapshot(), target, root / 'public', NOW)
            self.assertEqual(target.read_text(), 'keep')


class TransportTests(unittest.TestCase):
    def test_no_network_for_non_api_or_credential_destination(self):
        api = e.API('test-only')
        for path in ('https://attacker.example/', '//attacker.example/', '/repos/a/b\nAuthorization: bad'):
            with self.assertRaises(e.EvidenceError):
                api.get(path)

    def test_http200_partial_graphql_error_is_unavailable(self):
        reply = e.sanitize_reply(200, {'errors': [{'message': 'sensitive'}], 'data': {'x': 1}})
        self.assertEqual(reply.reason, 'api_errors')
        self.assertIsNone(reply.value)

    def test_request_budget_is_bounded_without_exposing_token(self):
        api = e.API('sensitive-token', max_requests=0)
        reply = api.get('/repos/owner/repo')
        self.assertEqual(reply.reason, 'request_budget')
        self.assertNotIn('sensitive-token', repr(reply))


class CollectorTests(unittest.TestCase):
    def replies(self, final_sha=SHA, protection=None):
        check = {'id': 90, 'name': 'policy', 'app': {'id': 1}, 'head_sha': SHA,
                 'status': 'completed', 'conclusion': 'success',
                 'completed_at': '2026-11-14T00:00:00Z'}
        return [e.Reply(200, {'object': {'sha': SHA}}), e.Reply(200, []),
                protection or e.Reply(403, None),
                e.Reply(200, {'total_count': 1, 'check_runs': [check]}), e.Reply(200, []),
                e.Reply(200, {'total_count': 1, 'workflows': [{'id': 20, 'state': 'active'}]}),
                e.Reply(200, {'total_count': 1, 'workflow_runs': [run()]}),
                e.Reply(200, {'object': {'sha': final_sha}})]

    def test_repository_capture_is_bound_to_head_and_run_without_claiming_enforcement(self):
        api = FakeAPI(self.replies())
        row = e.collect_repo(api, repository(), {'exceptions': []}, NOW)
        self.assertTrue(row['head_stable'])
        self.assertEqual(row['source_sha'], SHA)
        self.assertEqual(row['observations']['current_ci']['state'], 'pass')
        self.assertEqual(row['observations']['schedule_history']['state'], 'pass')
        self.assertEqual(row['observations']['protection']['state'], 'unknown')
        self.assertEqual(row['observations']['enforcement']['state'], 'unknown')
        self.assertNotIn('status=completed', ' '.join(api.paths))

    def test_head_moves_during_collection_revokes_current_commit_claim(self):
        row = e.collect_repo(FakeAPI(self.replies(OTHER)), repository(), {'exceptions': []}, NOW)
        self.assertFalse(row['head_stable'])
        self.assertEqual(row['observations']['current_ci']['state'], 'unknown')

    def test_unregistered_exception_policy_is_unknown_not_empty_pass(self):
        row = e.collect_repo(FakeAPI(self.replies()), repository(), {}, NOW)
        self.assertEqual(row['observations']['exceptions']['state'], 'unknown')

    def test_archived_and_disabled_repositories_are_kept_without_execution_claims(self):
        for flags in ({'archived': True}, {'disabled': True}):
            row = e.collect_repo(FakeAPI([]), repository(**flags), {}, NOW)
            self.assertEqual(row['observations']['current_ci']['state'], 'not_applicable')
            self.assertEqual(row['repository']['id'], 1)

    def test_ambiguous_head_404_is_unknown_not_empty(self):
        row = e.collect_repo(FakeAPI([e.Reply(404, None)]), repository(), {}, NOW)
        self.assertIsNone(row['empty'])
        self.assertIsNone(row['source_sha'])

    def test_confirmed_empty_repository_is_retained(self):
        row = e.collect_repo(FakeAPI([e.Reply(409, {'message': 'Git Repository is empty.'})]), repository(), {}, NOW)
        self.assertTrue(row['empty'])
        self.assertEqual(row['observations']['current_ci']['state'], 'not_applicable')

    def test_error_payload_is_not_treated_as_observed_protection(self):
        obs = e.protection_observation(e.Collection([], True, []),
                                       e.Reply(200, {'message': 'incomplete'}), NOW, SHA)
        self.assertEqual(obs['state'], 'unknown')


class AdditionalTruthfulnessTests(unittest.TestCase):
    snapshot = PublicationTests.snapshot

    def test_fresh_envelope_cannot_refresh_old_observations(self):
        snapshot = self.snapshot()
        snapshot['repositories'][0]['observations']['protection']['observed_at'] = '2026-01-01T00:00:00Z'
        with self.assertRaises(e.EvidenceError):
            e.validate_snapshot(snapshot, NOW)

    def test_baseline_extras_cannot_leak_into_public_output(self):
        snapshot = self.snapshot()
        snapshot['baselines'] = [{'scope': 'legacy_active_nonfork', 'observed_at': '2026-07-31T00:00:00Z',
                                  'count': 163, 'expected_historical_count': 163,
                                  'source_sha256': 'c' * 64, 'compliance_trend_comparable': False,
                                  'private_paths': 'secret-fixture'}]
        self.assertNotIn('secret-fixture', json.dumps(e.public_report(snapshot)))

    def test_duplicate_unavailable_stable_identity_counted_once(self):
        registry = [{'repository': 'owner/old', 'repository_id': 99},
                    {'repository': 'owner/renamed', 'repository_id': 99}]
        result = e.reconcile(FakeAPI([e.Reply(404, None)]), registry, [], 'owner', NOW)
        self.assertEqual(result['counts']['known_unavailable'], 1)
        self.assertEqual(result['counts']['duplicate_registry_entries'], 1)

    def test_partial_snapshot_cannot_replace_authoritative_issue_block(self):
        report = e.public_report(self.snapshot())
        report['inventory_complete_for_declared_scope'] = False
        with self.assertRaises(e.EvidenceError):
            e.validate_public(report, NOW, require_complete=True)

    def test_aggregate_count_tampering_is_rejected(self):
        report = e.public_report(self.snapshot())
        report['controls']['current_ci']['pass'] = 100
        with self.assertRaises(e.EvidenceError):
            e.validate_public(report, NOW)



class ExpiryBoundaryTests(unittest.TestCase):
    def test_snapshot_expires_before_an_active_exception_changes_calendar_day(self):
        snapshot = PublicationTests().snapshot()
        row = snapshot['repositories'][0]
        row['observations']['exceptions'] = e.exception_observation(
            [{'control': 'x', 'review_after': '2026-11-14'}], NOW)
        snapshot = e.make_snapshot([row], snapshot['discovery'], snapshot['reconciliation'],
                                   NOW, SHA, 123, [])
        self.assertEqual(e.stamp(snapshot['expires_at']), datetime(2026, 11, 15, tzinfo=UTC))
        with self.assertRaises(e.EvidenceError):
            e.validate_snapshot(snapshot, datetime(2026, 11, 15, 0, 0, 1, tzinfo=UTC))

if __name__ == '__main__':
    unittest.main()
