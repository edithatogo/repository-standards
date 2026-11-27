"""Offline contract for bounded additive managed-file candidates; no writer."""

import hashlib
import json
import re
from datetime import UTC, datetime, timedelta


MAX_ADDITIONS = 10
MAX_PATHS = 10_000
MAX_TTL = timedelta(hours=24)
FIELDS = {'schema_version', 'mode', 'materiality', 'repository', 'source_tree',
          'target_head', 'owner', 'issued_at', 'expires_at', 'additions', 'idempotency_key'}
WINDOWS_RESERVED = {'CON', 'PRN', 'AUX', 'NUL'} | {f'{prefix}{i}' for prefix in ('COM', 'LPT') for i in range(1, 10)}


class PlanError(ValueError):
    """Fixed rejection reason; no untrusted plan content."""


def matches(value, pattern):
    return isinstance(value, str) and re.fullmatch(pattern, value) is not None


def sha(value):
    return matches(value, r'[0-9a-f]{40}')


def portable_path(path):
    if not matches(path, r'[A-Za-z0-9._/-]{1,240}'):
        return False
    return all(part and part not in ('.', '..') and part.casefold() != '.git'
               and not part.endswith('.') and part.split('.')[0].upper() not in WINDOWS_RESERVED
               for part in path.split('/'))


def parents(path):
    parts = path.split('/')
    return ('/'.join(parts[:i]) for i in range(1, len(parts)))


def path_inventory(paths):
    if not isinstance(paths, (list, tuple)) or len(paths) > MAX_PATHS or not all(map(portable_path, paths)):
        raise PlanError('invalid_path_inventory')
    folded = {path.casefold() for path in paths}
    if len(folded) != len(paths) or any(parent in folded for path in folded for parent in parents(path)):
        raise PlanError('path_collision')
    spellings = {}
    for path in paths:
        for entry in (*parents(path), path):
            if spellings.setdefault(entry.casefold(), entry) != entry:
                raise PlanError('path_collision')


def timestamp(value):
    if not matches(value, r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z'):
        raise PlanError('invalid_timestamp')
    try:
        return datetime.fromisoformat(value[:-1] + '+00:00')
    except ValueError:
        raise PlanError('invalid_timestamp') from None


def plan_key(plan):
    """Digest of canonical plan body; independent of dictionary key order."""
    if not isinstance(plan, dict):
        raise PlanError('invalid_plan')
    try:
        body = {k: v for k, v in plan.items() if k != 'idempotency_key'}
        return hashlib.sha256(json.dumps(body, sort_keys=True, separators=(',', ':'),
                                         allow_nan=False).encode()).hexdigest()
    except (TypeError, ValueError, RecursionError):
        raise PlanError('invalid_plan') from None


def inspect_plan(plan, *, repository, source_tree, target_head, owner,
                 allowed_additions, existing_paths, snapshot_complete, seen_keys, now):
    """Check decoded synthetic data against independent expectations, never apply.

    A trusted caller must bind the allowlist (including exact source blob IDs)
    and complete leaf-path inventory to the independently obtained tree/head.
    This function does not fetch, authenticate or modify either repository.
    """
    if (not matches(repository, r'[A-Za-z0-9_.-]{1,100}/[A-Za-z0-9_.-]{1,100}')
            or not matches(owner, r'[A-Za-z0-9_.-]{1,100}')
            or not sha(source_tree) or not sha(target_head)
            or not isinstance(now, datetime) or now.utcoffset() is None
            or not isinstance(seen_keys, (set, frozenset)) or len(seen_keys) > MAX_PATHS
            or any(not matches(key, r'[0-9a-f]{64}') for key in seen_keys)
            or not isinstance(allowed_additions, dict) or not 0 < len(allowed_additions) <= MAX_PATHS
            or any(not portable_path(path) or not sha(blob) for path, blob in allowed_additions.items())):
        raise PlanError('invalid_context')
    if snapshot_complete is not True:
        raise PlanError('snapshot_incomplete')
    path_inventory(existing_paths)
    if (not isinstance(plan, dict) or set(plan) != FIELDS
            or type(plan['schema_version']) is not int or plan['schema_version'] != 1
            or plan['mode'] != 'plan_only' or plan['materiality'] != 'low'):
        raise PlanError('invalid_plan')
    if (plan['repository'], plan['source_tree'], plan['target_head'], plan['owner']) != (repository, source_tree, target_head, owner):
        raise PlanError('identity_mismatch')
    issued, expires = timestamp(plan['issued_at']), timestamp(plan['expires_at'])
    if not issued <= now.astimezone(UTC) < expires or expires - issued > MAX_TTL:
        raise PlanError('outside_plan_lifetime')
    additions = plan['additions']
    if not isinstance(additions, list) or not 0 < len(additions) <= MAX_ADDITIONS:
        raise PlanError('invalid_additions')
    for row in additions:
        if (not isinstance(row, dict) or set(row) != {'path', 'blob'}
                or not portable_path(row['path']) or not sha(row['blob'])):
            raise PlanError('invalid_addition')
        if allowed_additions.get(row['path']) != row['blob']:
            raise PlanError('addition_not_allowed')
    paths = [row['path'] for row in additions]
    if paths != sorted(paths):
        raise PlanError('noncanonical_addition_order')
    path_inventory([*existing_paths, *paths])
    key = plan_key(plan)
    if plan['idempotency_key'] != key:
        raise PlanError('key_mismatch')
    return {'disposition': 'already_recorded' if key in seen_keys else 'inspect_candidate',
            'addition_count': len(paths), 'idempotency_key': key,
            'snapshot_verified': False, 'write_authorized': False}
