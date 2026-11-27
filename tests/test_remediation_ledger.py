import sqlite3
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path

import remediation_plan_contract as contract
import remediation_ledger as ledger


NOW = datetime(2026, 11, 27, 10, tzinfo=UTC)
BLOB = 'c' * 40


def candidate(paths=('docs/new.md',), blob=BLOB, **changes):
    body = dict(schema_version=1, mode='plan_only', materiality='low',
                repository='owner/example', source_tree='a' * 40,
                target_head='b' * 40, owner='fixture-owner',
                issued_at='2026-11-27T09:00:00Z', expires_at='2026-11-27T11:00:00Z',
                additions=[dict(path=p, blob=blob) for p in sorted(paths)])
    body.update(changes)
    return dict(body, idempotency_key=contract.plan_key(body))


class LedgerTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.database = Path(tmp.name) / 'reservations.sqlite'

    def reserve(self, plan=None, repository_id=7, **changes):
        p = candidate() if plan is None else plan
        context = {k: p[k] for k in ('repository', 'source_tree', 'target_head', 'owner')}
        context.update(allowed_additions={x['path']: x['blob'] for x in p['additions']},
                       existing_paths=[], snapshot_complete=True, now=NOW)
        context.update(changes)
        return ledger.record_plan(self.database, p, repository_id=repository_id, **context)

    def test_reissued_plan_with_new_expiry_and_head_is_duplicate(self):
        initial = candidate()
        self.assertEqual(self.reserve(initial)['disposition'], 'recorded')
        revised = candidate(expires_at='2026-11-27T12:00:00Z', target_head='d' * 40)
        self.assertNotEqual(initial['idempotency_key'], revised['idempotency_key'])
        result = self.reserve(revised)
        self.assertEqual(result['disposition'], 'already_recorded')
        self.assertFalse(result['write_authorized'])
        self.assertFalse(result['operation_executed'])

    def test_stable_repository_id_handles_renamed_repository(self):
        self.reserve()
        self.assertEqual(self.reserve(candidate(repository='owner/renamed'))['disposition'], 'already_recorded')
        self.assertEqual(self.reserve(repository_id=8)['disposition'], 'recorded')

    def test_conflicting_blob_case_and_directory_paths_hold(self):
        self.reserve()
        for p in (candidate(blob='e' * 40), candidate(paths=('Docs/New.md',)),
                  candidate(paths=('docs/new.md/child',)), candidate(paths=('Docs/other.md',)),
                  candidate(paths=('docs',))):
            with self.subTest(p=p['additions']), self.assertRaises(contract.PlanError):
                self.reserve(p)
        self.assertEqual(self.reserve(candidate(paths=('docs/other.md',)))['disposition'], 'recorded')

    def test_partial_overlap_is_atomic_and_does_not_record_new_path(self):
        self.reserve()
        with self.assertRaisesRegex(contract.PlanError, 'partial_overlap'):
            self.reserve(candidate(paths=('docs/new.md', 'docs/other.md')))
        self.assertEqual(self.reserve(candidate(paths=('docs/other.md',)))['disposition'], 'recorded')

    def test_invalid_plan_never_creates_ledger(self):
        with self.assertRaises(contract.PlanError):
            self.reserve(target_head='e' * 40)
        self.assertFalse(self.database.exists())
        with self.assertRaises(contract.PlanError):
            self.reserve(repository_id=True)
        self.assertFalse(self.database.exists())

    def test_concurrent_reservations_cannot_both_win(self):
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: self.reserve()['disposition'], range(2)))
        self.assertEqual(sorted(results), ['already_recorded', 'recorded'])

    def test_locked_ledger_fails_closed(self):
        self.reserve()
        with sqlite3.connect(self.database) as connection:
            connection.execute('BEGIN IMMEDIATE')
            with self.assertRaisesRegex(contract.PlanError, 'ledger_unavailable'):
                self.reserve(candidate(paths=('docs/other.md',)))
        self.assertEqual(self.reserve(candidate(paths=('docs/other.md',)))['disposition'], 'recorded')
