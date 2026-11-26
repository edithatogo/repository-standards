import unittest

from pr_integration_plan import plan


def pr(**changes):
    return {
        'number': 7, 'isDraft': False, 'isCrossRepository': False,
        'baseRefName': 'main', 'baseRefOid': 'a' * 40, 'headRefOid': 'b' * 40,
        'labels': [], 'reviewDecision': '', 'mergeable': 'MERGEABLE',
        'mergeStateStatus': 'CLEAN',
        'statusCheckRollup': [{'status': 'COMPLETED', 'conclusion': 'SUCCESS'}],
        **changes,
    }


class IntegrationPlanTests(unittest.TestCase):
    def test_clean_is_only_candidate_never_authorization(self):
        result = plan([pr()], 'main')
        self.assertEqual(result['mode'], 'plan_only')
        self.assertEqual(result['pull_requests'][0]['disposition'], 'inspect_merge_candidate')
        self.assertFalse(result['write_authorized'])

    def test_holds_take_precedence_over_conflict_and_green(self):
        for changes in ({'isDraft': True}, {'isCrossRepository': True},
                        {'labels': [{'name': 'scientific-hold'}]},
                        {'reviewDecision': 'CHANGES_REQUESTED'},
                        {'baseRefName': 'release'}):
            with self.subTest(changes=changes):
                row = plan([pr(mergeable='CONFLICTING', mergeStateStatus='DIRTY', **changes)], 'main')['pull_requests'][0]
                self.assertEqual(row['disposition'], 'hold')

    def test_conflict_behind_and_unknown_are_distinct(self):
        for state, mergeable, expected in (
            ('DIRTY', 'CONFLICTING', 'inspect_conflict'),
            ('BEHIND', 'MERGEABLE', 'inspect_base_update'),
            ('UNKNOWN', 'UNKNOWN', 'wait'),
            ('BLOCKED', 'MERGEABLE', 'hold'),
            ('UNSTABLE', 'MERGEABLE', 'inspect_checks'),
        ):
            with self.subTest(state=state):
                self.assertEqual(plan([pr(mergeStateStatus=state, mergeable=mergeable)], 'main')['pull_requests'][0]['disposition'], expected)

    def test_clean_with_missing_failed_or_pending_checks_is_not_candidate(self):
        for checks in ([], None, [{'status': 'COMPLETED', 'conclusion': 'FAILURE'}],
                       [{'status': 'IN_PROGRESS', 'conclusion': None}],
                       [{'state': 'PENDING'}], [{'state': 'ERROR'}],
                       [{'status': 'COMPLETED', 'conclusion': 'SKIPPED'}]):
            with self.subTest(checks=checks):
                self.assertEqual(plan([pr(statusCheckRollup=checks)], 'main')['pull_requests'][0]['disposition'], 'inspect_checks')

    def test_missing_state_or_identity_is_rejected(self):
        for key in ('mergeable', 'reviewDecision', 'labels', 'headRefOid', 'isDraft', 'isCrossRepository'):
            row = pr()
            del row[key]
            with self.subTest(key=key), self.assertRaises(ValueError):
                plan([row], 'main')
        with self.assertRaises(ValueError):
            plan([pr(headRefOid='unknown')], 'main')

    def test_cap_and_duplicate_rows_fail_closed(self):
        with self.assertRaises(ValueError):
            plan([pr(number=n) for n in range(1, 102)], 'main')
        with self.assertRaises(ValueError):
            plan([pr(), pr()], 'main')

    def test_no_raw_untrusted_text_is_retained(self):
        row = plan([pr(title='untrusted', body='secret', labels=[{'name': 'arbitrary text'}])], 'main')['pull_requests'][0]
        self.assertEqual(set(row), {'number', 'base_sha', 'head_sha', 'disposition'})
