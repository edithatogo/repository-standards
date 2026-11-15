#!/usr/bin/env python3
"""Update one existing public issue with schema-validated, fresh aggregates only."""
from __future__ import annotations

import argparse
import json
import os
from datetime import UTC, datetime
from pathlib import Path
import sys

# Deliberate trusted-source import; the collector never imports consumer code.
sys.path.insert(0, str(Path(__file__).resolve().parent))
import estate_evidence as evidence


def publish(api, report: dict, issue_number: int, now: datetime) -> bool:
    evidence.validate_public(report, now, require_complete=True)
    if type(issue_number) is not int or issue_number < 1:
        raise evidence.EvidenceError('invalid_issue_number')
    path = f'/repos/{evidence.SOURCE_REPOSITORY}/issues/{issue_number}'
    reply = api.get(path)
    if reply.status != 200 or not isinstance(reply.value, dict) or 'pull_request' in reply.value:
        raise evidence.EvidenceError('issue_read_unavailable')
    body = reply.value.get('body') or ''
    if not isinstance(body, str):
        raise evidence.EvidenceError('invalid_issue_body')
    updated = evidence.reconcile_text(body, evidence.markdown(report))
    if updated == body:
        return False
    if len(updated.encode()) > 60000:
        raise evidence.EvidenceError('issue_body_budget')
    result = api.request('PATCH', path, {'body': updated})
    if result.status != 200:
        raise evidence.EvidenceError('issue_update_unavailable')
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--issue-number', type=int, default=16)
    args = parser.parse_args()
    token = os.environ.pop('ISSUE_TOKEN', '')
    try:
        if not token:
            raise evidence.EvidenceError('issue_credential_unavailable')
        report = json.loads(args.report.read_text())
        schema = Path(__file__).resolve().parents[1] / 'schemas/estate-evidence-public.schema.json'
        evidence.schema_check(report, schema)
        changed = publish(evidence.API(token), report, args.issue_number, datetime.now(UTC))
        print(json.dumps({'aggregate_issue_updated': changed}))
        return 0
    except (OSError, ValueError, TypeError, KeyError, ImportError):
        print('{"error":"aggregate_issue_reconciliation_unavailable"}')
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
