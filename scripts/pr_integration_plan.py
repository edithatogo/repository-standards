#!/usr/bin/env python3
"""Read-only PR triage; observations never authorize a GitHub mutation."""

import argparse
import json
import re
from datetime import UTC, datetime
from pathlib import Path


MAX_PRS = 100
HOLD_LABELS = {'do-not-merge', 'manual-review', 'scientific-hold', 'hold'}
SHA = re.compile(r'[0-9a-f]{40}')


def disposition(row, default_branch):
    if not all(type(row.get(key)) is bool for key in ('isDraft', 'isCrossRepository')):
        raise ValueError('missing PR eligibility metadata')
    labels = row.get('labels')
    if not isinstance(labels, list) or not all(
        isinstance(label, dict) and isinstance(label.get('name'), str) for label in labels
    ):
        raise ValueError('invalid label observation')
    if not all(isinstance(row.get(key), str) for key in (
        'baseRefName', 'mergeable', 'mergeStateStatus', 'reviewDecision'
    )):
        raise ValueError('missing PR state')
    if (row['isDraft'] or row['isCrossRepository'] or row['baseRefName'] != default_branch
            or HOLD_LABELS.intersection(label['name'].casefold() for label in labels)
            or row['reviewDecision'] not in ('', 'APPROVED')):
        return 'hold'
    state, mergeable = row['mergeStateStatus'], row['mergeable']
    if state == 'DIRTY' and mergeable == 'CONFLICTING':
        return 'inspect_conflict'
    if state == 'UNKNOWN' or mergeable != 'MERGEABLE':
        return 'wait'
    if state == 'BEHIND':
        return 'inspect_base_update'
    if state == 'UNSTABLE':
        return 'inspect_checks'
    if state != 'CLEAN':
        return 'hold'
    checks = row.get('statusCheckRollup')
    if not isinstance(checks, list) or not checks or not all(
        isinstance(check, dict) and (
            check.get('state') == 'SUCCESS' if 'state' in check else
            check.get('status') == 'COMPLETED' and check.get('conclusion') == 'SUCCESS'
        ) for check in checks
    ):
        return 'inspect_checks'
    # A rollup is only a snapshot: it may omit checks or describe a stale base.
    return 'inspect_merge_candidate'


def plan(rows, default_branch):
    if not isinstance(rows, list) or len(rows) > MAX_PRS:
        raise ValueError('PR inventory missing or exceeds bounded scan')
    results = []
    seen = set()
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError('invalid PR record')
        number = row.get('number')
        if type(number) is not int or number < 1 or number in seen:
            raise ValueError('invalid or duplicate PR number')
        if not all(isinstance(row.get(key), str) and SHA.fullmatch(row[key])
                   for key in ('baseRefOid', 'headRefOid')):
            raise ValueError('invalid PR revision')
        seen.add(number)
        results.append({'number': number, 'base_sha': row['baseRefOid'],
                        'head_sha': row['headRefOid'],
                        'disposition': disposition(row, default_branch)})
    return {'schema_version': 1, 'mode': 'plan_only', 'write_authorized': False,
            'pull_requests': sorted(results, key=lambda row: row['number'])}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--repository', required=True)
    parser.add_argument('--default-branch', required=True)
    parser.add_argument('--revision', required=True)
    args = parser.parse_args()
    receipt = plan(json.loads(args.input.read_text()), args.default_branch)
    if not SHA.fullmatch(args.revision):
        raise ValueError('invalid scanner revision')
    receipt.update(repository=args.repository, scanner_revision=args.revision,
                   observed_at=datetime.now(UTC).isoformat())
    args.output.write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
