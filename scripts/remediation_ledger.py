"""Persistent advisory reservations; never an operation executor or writer grant."""

import sqlite3
from contextlib import closing

from remediation_plan_contract import MAX_PATHS, PlanError, inspect_plan, path_inventory, sha


# ponytail: one local SQLite database and a short write transaction; no distributed lease.
# Trusted caller owns the private database path and independently binds the numeric
# repository ID to the validated repository identity. No automatic expiry/release.
def record_plan(database, plan, *, repository_id, **context):
    if type(repository_id) is not int or not 0 < repository_id < 2**63:
        raise PlanError('invalid_repository_id')
    checked = inspect_plan(plan, **context, seen_keys=set())
    additions = {row['path']: row['blob'] for row in plan['additions']}
    try:
        with closing(sqlite3.connect(database, timeout=1)) as db, db:
            db.execute('BEGIN IMMEDIATE')
            db.execute('''CREATE TABLE IF NOT EXISTS reservations (
                repository_id INTEGER NOT NULL, path TEXT NOT NULL COLLATE NOCASE,
                blob TEXT NOT NULL, plan_digest TEXT NOT NULL,
                PRIMARY KEY (repository_id, path))''')
            rows = db.execute('SELECT path, blob FROM reservations WHERE repository_id = ? LIMIT ?',
                              (repository_id, MAX_PATHS + 1)).fetchall()
            path_inventory([path for path, _ in rows])
            if any(not sha(blob) for _, blob in rows):
                raise PlanError('invalid_ledger_record')
            recorded = dict(rows)
            duplicates = set(additions) & set(recorded)
            if any(recorded[path] != additions[path] for path in duplicates):
                raise PlanError('operation_conflict')
            new_paths = sorted(set(additions) - duplicates)
            path_inventory([*recorded, *new_paths])
            if duplicates and new_paths:
                raise PlanError('partial_overlap')
            if new_paths:
                db.executemany('INSERT INTO reservations VALUES (?, ?, ?, ?)',
                               [(repository_id, path, additions[path], checked['idempotency_key'])
                                for path in new_paths])
    except (sqlite3.Error, OSError, OverflowError):
        raise PlanError('ledger_unavailable') from None
    return {**checked, 'disposition': 'recorded' if new_paths else 'already_recorded',
            'operation_executed': False, 'write_authorized': False}
