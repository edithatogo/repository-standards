"""Privacy-safe UTC monthly metrics from bounded, independently supplied event observations."""

from collections import Counter, defaultdict
import re
from statistics import median

from verify_receipt import ReceiptError, timestamp


MAX_EVENTS = 10_000
STATES = {'integration': ('merged', 'failed', 'held', 'unknown'),
          'ci': ('pass', 'fail', 'unknown', 'not_applicable'),
          'repair': ('success', 'failure', 'unknown', 'not_attempted'),
          'truth': ('safe', 'unsafe', 'unknown')}
MEASURES = ('latency_seconds', 'runner_seconds', 'maintenance_seconds', 'cost_usd_cents')
FIELDS = {'event_id', 'scope', 'observed_at', 'accepted', *STATES, *MEASURES}


class MetricsError(ValueError):
    """Fixed rejection reason without event contents."""


def rate(numerator, denominator):
    return {'numerator': numerator, 'denominator': denominator,
            'rate': numerator / denominator if denominator else None}


def measured(rows, key, *, use_median=False):
    values = [row[key] for row in rows if row[key] is not None]
    return {'median' if use_median else 'sum': (median(values) if use_median else sum(values)) if values else None,
            'known': len(values), 'total': len(rows)}


def summarize(events, *, scope):
    """Only comparable, single-scope event sets; no input authenticity or certification claim."""
    if scope not in ('synthetic', 'observed') or not isinstance(events, list) or len(events) > MAX_EVENTS:
        raise MetricsError('invalid_scope_or_budget')
    months = defaultdict(list)
    seen = set()
    for row in events:
        if not isinstance(row, dict) or set(row) != FIELDS or row['scope'] != scope:
            raise MetricsError('invalid_event')
        identifier = row['event_id']
        if (not isinstance(identifier, str) or not re.fullmatch(r'[A-Za-z0-9_.-]{1,100}', identifier)
                or identifier in seen):
            raise MetricsError('invalid_or_duplicate_event')
        seen.add(identifier)
        if (any(row[key] not in states for key, states in STATES.items())
                or row['accepted'] is not None and type(row['accepted']) is not bool
                or any(row[key] is not None and (type(row[key]) is not int or row[key] < 0)
                       for key in MEASURES)):
            raise MetricsError('invalid_measurement')
        try:
            month = timestamp(row['observed_at']).strftime('%Y-%m')
        except ReceiptError:
            raise MetricsError('invalid_timestamp') from None
        months[month].append(row)
    reports = []
    for month, rows in sorted(months.items()):
        report = {'month': month, 'events': len(rows)}
        for key in ('integration', 'ci', 'repair'):
            counts = Counter(row[key] for row in rows)
            report[key] = {state: counts[state] for state in STATES[key]}
        i, c, r = report['integration'], report['ci'], report['repair']
        unsafe = [row for row in rows if row['truth'] == 'unsafe' and row['accepted'] is not None]
        report.update(integration_success=rate(i['merged'], i['merged'] + i['failed']),
                      ci_success=rate(c['pass'], c['pass'] + c['fail']),
                      repair_success=rate(r['success'], r['success'] + r['failure']),
                      false_acceptance=rate(sum(row['accepted'] for row in unsafe), len(unsafe)),
                      unlabelled_or_missing_decision=sum(row['truth'] == 'unknown' or row['accepted'] is None for row in rows),
                      merge_latency_seconds=measured([row for row in rows if row['integration'] == 'merged'],
                                                     'latency_seconds', use_median=True))
        report.update({key: measured(rows, key) for key in MEASURES[1:]})
        reports.append(report)
    return {'schema_version': 1, 'scope': scope, 'months': reports, 'certified': False,
            'input_provenance_verified': False, 'write_authorized': False}
