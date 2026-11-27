import unittest
from datetime import UTC, datetime

import remediation_plan_contract as contract


NOW = datetime(2026, 11, 27, 10, tzinfo=UTC)
SOURCE = 'a' * 40
HEAD = 'b' * 40
BLOB = 'c' * 40
OWNER = 'fixture-owner'
REPO = 'owner/example'


def plan(**changes):
    body = {'schema_version': 1, 'mode': 'plan_only', 'materiality': 'low',
            'repository': REPO, 'source_tree': SOURCE, 'target_head': HEAD,
            'owner': OWNER, 'issued_at': '2026-11-27T09:00:00Z',
            'expires_at': '2026-11-27T11:00:00Z',
            'additions': [{'path': 'docs/new.md', 'blob': BLOB}], **changes}
    return dict(body, idempotency_key=contract.plan_key(body))


class PlanContractTests(unittest.TestCase):
    def inspect(self, candidate=None, **changes):
        context = {'repository': REPO, 'source_tree': SOURCE, 'target_head': HEAD,
                   'owner': OWNER, 'allowed_additions': {'docs/new.md': BLOB},
                   'existing_paths': ['docs/old.md'], 'snapshot_complete': True,
                   'seen_keys': set(), 'now': NOW, **changes}
        return contract.inspect_plan(plan() if candidate is None else candidate, **context)

    def test_additive_candidate_is_advisory_only(self):
        result = self.inspect()
        self.assertEqual(result['disposition'], 'inspect_candidate')
        self.assertEqual(result['addition_count'], 1)
        self.assertFalse(result['write_authorized'])
        self.assertFalse(result['snapshot_verified'])

    def test_stale_source_target_and_owner_fail(self):
        for change in ({'source_tree': 'd' * 40}, {'target_head': 'd' * 40},
                       {'owner': 'another-owner'}, {'repository': 'owner/other'}):
            with self.subTest(change=change), self.assertRaisesRegex(contract.PlanError, 'identity_mismatch'):
                self.inspect(plan(**change))
        with self.assertRaisesRegex(contract.PlanError, 'invalid_context'):
            self.inspect(target_head='b' * 7)

    def test_expired_future_and_unbounded_ttl_fail(self):
        for change in ({'expires_at': '2026-11-27T10:00:00Z'},
                       {'issued_at': '2026-11-27T10:00:01Z'},
                       {'expires_at': '2026-11-28T09:00:01Z'},
                       {'issued_at': '2026-11-27T09:00:00'}):
            with self.subTest(change=change), self.assertRaises(contract.PlanError):
                self.inspect(plan(**change))

    def test_target_collision_never_overwrites_even_identical_content(self):
        for paths in (['docs/new.md'], ['Docs/New.md'], ['docs'], ['docs/new.md/child'], ['Docs/old.md']):
            with self.subTest(paths=paths), self.assertRaisesRegex(contract.PlanError, 'path_collision'):
                self.inspect(existing_paths=paths)

    def test_unknown_or_inconsistent_snapshot_fails_closed(self):
        with self.assertRaisesRegex(contract.PlanError, 'snapshot_incomplete'):
            self.inspect(existing_paths=[], snapshot_complete=False)
        for paths in (['a', 'a/b'], ['A', 'a'], ['A/one', 'a/two'], ['../file']):
            with self.subTest(paths=paths), self.assertRaises(contract.PlanError):
                self.inspect(existing_paths=paths)

    def test_unsafe_paths_and_outside_allowlist_fail(self):
        for path in ('../new', '/new', 'docs//new', 'docs/../new', 'docs\\new',
                     '.git/config', 'docs/a\n.md', 'docs/CON', 'docs/other.md'):
            with self.subTest(path=path), self.assertRaises(contract.PlanError):
                self.inspect(plan(additions=[{'path': path, 'blob': BLOB}]))
        with self.assertRaisesRegex(contract.PlanError, 'addition_not_allowed'):
            self.inspect(plan(additions=[{'path': 'docs/new.md', 'blob': 'd' * 40}]))

    def test_duplicate_and_prefix_collisions_in_plan_fail(self):
        for names in (['docs/new.md', 'docs/new.md'], ['docs/New.md', 'docs/new.md'],
                      ['docs/new.md', 'docs/new.md/child'], ['Docs/one.md', 'docs/two.md']):
            additions = [{'path': path, 'blob': BLOB} for path in sorted(names)]
            with self.subTest(names=names), self.assertRaises(contract.PlanError):
                self.inspect(plan(additions=additions), allowed_additions={path: BLOB for path in names})

    def test_invalid_scope_and_bounded_count(self):
        for change in ({'mode': 'apply'}, {'materiality': 'high'}, {'schema_version': True},
                       {'unexpected': True}, {'additions': []},
                       {'additions': [{'path': 'docs/new.md', 'blob': BLOB, 'delete': True}]}):
            with self.subTest(change=change), self.assertRaises(contract.PlanError):
                self.inspect(plan(**change))
        additions = [{'path': f'docs/{n:02}.md', 'blob': BLOB} for n in range(contract.MAX_ADDITIONS + 1)]
        with self.assertRaises(contract.PlanError):
            self.inspect(plan(additions=additions), allowed_additions={row['path']: BLOB for row in additions})

    def test_key_is_order_independent_for_object_fields_and_binds_values(self):
        candidate = plan()
        key = candidate['idempotency_key']
        self.assertEqual(key, contract.plan_key(dict(reversed(list(candidate.items())))))
        changed = dict(candidate, expires_at='2026-11-27T12:00:00Z')
        with self.assertRaisesRegex(contract.PlanError, 'key_mismatch'):
            self.inspect(changed)
        self.assertNotEqual(key, contract.plan_key(changed))

    def test_duplicate_key_is_reported_without_authorizing_write(self):
        candidate = plan()
        result = self.inspect(candidate, seen_keys={candidate['idempotency_key']})
        self.assertEqual(result['disposition'], 'already_recorded')
        self.assertFalse(result['write_authorized'])
        with self.assertRaisesRegex(contract.PlanError, 'identity_mismatch'):
            self.inspect(candidate, seen_keys={candidate['idempotency_key']}, target_head='d' * 40)
