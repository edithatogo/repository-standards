import unittest

import assurance_metrics as metrics


def event(identifier, **changes):
    row = dict(event_id=identifier, scope='synthetic', observed_at='2026-11-27T09:00:00Z',
               integration='merged', ci='pass', repair='success', truth='unsafe', accepted=False,
               latency_seconds=60, runner_seconds=120, maintenance_seconds=30, cost_usd_cents=5)
    row.update(changes)
    return row


class MetricsTests(unittest.TestCase):
    def test_denominators_and_unknowns_are_explicit(self):
        rows = [event('a', accepted=True), event('b', integration='failed', ci='fail', repair='failure',
                    latency_seconds=None, accepted=False, cost_usd_cents=None),
                event('c', integration='held', ci='unknown', repair='unknown', truth='unknown',
                      accepted=None, latency_seconds=None, runner_seconds=None, maintenance_seconds=None, cost_usd_cents=None)]
        report = metrics.summarize(rows, scope='synthetic')['months'][0]
        self.assertEqual(report['integration'], {'merged': 1, 'failed': 1, 'held': 1, 'unknown': 0})
        self.assertEqual(report['ci_success'], {'numerator': 1, 'denominator': 2, 'rate': 0.5})
        self.assertEqual(report['false_acceptance'], {'numerator': 1, 'denominator': 2, 'rate': 0.5})
        self.assertEqual(report['unlabelled_or_missing_decision'], 1)
        self.assertEqual(report['cost_usd_cents'], {'sum': 5, 'known': 1, 'total': 3})
        self.assertEqual(report['runner_seconds'], {'sum': 240, 'known': 2, 'total': 3})
        self.assertEqual(report['merge_latency_seconds'], {'median': 60, 'known': 1, 'total': 1})

    def test_missing_labels_and_cost_do_not_become_zero_rates(self):
        report = metrics.summarize([event('a', integration='unknown', ci='unknown', repair='not_attempted',
            truth='unknown', accepted=None, cost_usd_cents=None, latency_seconds=None)], scope='synthetic')['months'][0]
        self.assertIsNone(report['false_acceptance']['rate'])
        self.assertIsNone(report['ci_success']['rate'])
        self.assertIsNone(report['cost_usd_cents']['sum'])
        self.assertIsNone(report['merge_latency_seconds']['median'])

    def test_months_are_utc_and_input_order_independent(self):
        rows = [event('a', observed_at='2026-12-01T01:00:00+02:00'), event('b', observed_at='2026-12-01T00:00:00Z')]
        result = metrics.summarize(rows, scope='synthetic')
        self.assertEqual([m['month'] for m in result['months']], ['2026-11', '2026-12'])
        self.assertEqual(result, metrics.summarize(list(reversed(rows)), scope='synthetic'))
        self.assertFalse(result['certified'])

    def test_duplicate_mixed_invalid_and_private_extra_fields_rejected(self):
        cases = [[event('a'), event('a')], [event('b', scope='observed')],
                 [event('c', accepted=1)], [event('d', cost_usd_cents=-1)],
                 [event('e', runner_seconds=True)], [event('f', observed_at='2026-11-27')],
                 [event('g', private_note='not retained')]]
        for rows in cases:
            with self.subTest(rows=rows), self.assertRaises(metrics.MetricsError):
                metrics.summarize(rows, scope='synthetic')
