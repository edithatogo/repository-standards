#!/usr/bin/env python3
"""Offline consistency check for v1 receipts; never verifies provenance or authorizes writes."""

import argparse
import hashlib
import json
import math
import re
from datetime import UTC, datetime
from pathlib import Path

import fastjsonschema


MAX_BYTES = 1024 * 1024
SCHEMA = Path(__file__).resolve().parents[1] / 'schemas/verification-receipt.schema.json'


class ReceiptError(ValueError):
    """A fixed reason code, never receipt contents."""


def matches(value, pattern):
    return isinstance(value, str) and re.fullmatch(pattern, value) is not None


def unique_names(names):
    if (not isinstance(names, (list, tuple)) or not names
            or any(not isinstance(n, str) or not n or n != n.strip()
                   or not n.isprintable() for n in names)
            or len(set(names)) != len(names)):
        raise ReceiptError('invalid_check_inventory')
    return set(names)


def timestamp(value):
    if not matches(value, r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})'):
        raise ReceiptError('invalid_timestamp')
    try:
        return datetime.fromisoformat(value.replace('Z', '+00:00')).astimezone(UTC)
    except (ValueError, OverflowError):
        raise ReceiptError('invalid_timestamp') from None


def strict_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ReceiptError('duplicate_json_key')
        result[key] = value
    return result


def finite_float(value):
    number = float(value)
    if not math.isfinite(number):
        raise ReceiptError('nonfinite_number')
    return number


def inspect_receipt(raw, *, expected_digest, repository, revision, required_checks, not_before, now):
    """Compare bytes to independently supplied expectations, not receipt-owned policy.

    The caller must obtain the digest, identity, check inventory and freshness
    cutoff from a trusted route. A matching digest is not an attestation. Artifact
    paths, evidence strings and source code are never accessed or executed.
    """
    if (not matches(expected_digest, r'[0-9a-f]{64}')
            or not matches(repository, r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+')
            or not matches(revision, r'[0-9a-f]{40}')):
        raise ReceiptError('invalid_expected_identity')
    required = unique_names(required_checks)
    if (not isinstance(not_before, datetime) or not isinstance(now, datetime)
            or not_before.utcoffset() is None or now.utcoffset() is None or not_before > now):
        raise ReceiptError('invalid_freshness_policy')
    if not isinstance(raw, bytes) or not 0 < len(raw) <= MAX_BYTES:
        raise ReceiptError('receipt_size')
    if hashlib.sha256(raw).hexdigest() != expected_digest:
        raise ReceiptError('digest_mismatch')
    try:
        data = json.loads(raw.decode('utf-8'), object_pairs_hook=strict_pairs,
                          parse_float=finite_float, parse_constant=finite_float)
    except ReceiptError:
        raise
    except (ValueError, RecursionError):
        raise ReceiptError('invalid_json') from None
    # The existing repository-owned schema uses the supported common keywords.
    # No caller-supplied schema or external schema reference is accepted.
    try:
        schema = json.loads(SCHEMA.read_text(encoding='utf-8'))
        if re.search(r'"\$ref"\s*:\s*"(?!#)', json.dumps(schema)):
            raise ReceiptError('remote_schema_reference')
        fastjsonschema.compile(schema, use_default=False)(data)
    except ReceiptError:
        raise
    except (OSError, ValueError, RecursionError, fastjsonschema.JsonSchemaException):
        raise ReceiptError('schema_validation_failed') from None
    if type(data['schema_version']) is not int:
        raise ReceiptError('schema_validation_failed')
    if data['repository'] != repository or data['revision'] != revision:
        raise ReceiptError('identity_mismatch')
    if not not_before <= timestamp(data['generated_at']) <= now:
        raise ReceiptError('outside_freshness_window')
    names = unique_names([check['name'] for check in data['checks']])
    if not required <= names:
        raise ReceiptError('required_check_missing')
    statuses = {check['result'] for check in data['checks']}
    result = 'fail' if 'fail' in statuses else 'partial' if 'skip' in statuses else 'pass'
    if data['result'] != result:
        raise ReceiptError('aggregate_mismatch')
    return {'mode': 'offline_consistency_only', 'result': result,
            'check_count': len(names), 'required_check_count': len(required),
            'provenance_verified': False, 'write_authorized': False}


def main(argv=None, *, now=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('receipt', type=Path)
    parser.add_argument('--sha256', required=True, help='Independently trusted receipt digest')
    parser.add_argument('--repository', required=True)
    parser.add_argument('--revision', required=True)
    parser.add_argument('--require-check', action='append', required=True)
    parser.add_argument('--not-before', required=True, help='Trusted UTC freshness cutoff (RFC 3339)')
    args = parser.parse_args(argv)
    try:
        with args.receipt.open('rb') as stream:
            raw = stream.read(MAX_BYTES + 1)
        result = inspect_receipt(raw, expected_digest=args.sha256, repository=args.repository,
                                 revision=args.revision, required_checks=args.require_check,
                                 not_before=timestamp(args.not_before), now=now if now is not None else datetime.now(UTC))
    except (OSError, ReceiptError) as error:
        print(json.dumps({'mode': 'offline_consistency_only', 'result': 'invalid',
                          'reason': str(error) if isinstance(error, ReceiptError) else 'receipt_unavailable',
                          'provenance_verified': False, 'write_authorized': False}))
        return 2
    print(json.dumps(result))
    return 0 if result['result'] == 'pass' else 1


if __name__ == '__main__':
    raise SystemExit(main())
