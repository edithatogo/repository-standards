#!/usr/bin/env python3
"""Read-only, scope-explicit estate evidence; only allowlisted aggregates are public.

API and disk errors are reduced to fixed reason codes. Detailed evidence stays in
an explicitly private file, not the public artifact directory or console output.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from threading import Lock
from typing import Any

API_ROOT = 'https://api.github.com'
SHA = re.compile(r'^[0-9a-f]{40}$')
NAME = re.compile(r'^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$')
STATES = ('pass', 'fail', 'unknown', 'stale', 'not_applicable')
CONTROLS = ('protection', 'current_ci', 'schedule_history', 'exceptions', 'enforcement')
START = '<!-- estate-evidence-v1:start -->'
END = '<!-- estate-evidence-v1:end -->'
MAX_BYTES = 16 * 1024 * 1024
EVIDENCE_TTL = timedelta(hours=24)
RUN_TTL = timedelta(days=8)
SOURCE_REPOSITORY = 'edithatogo/repository-standards'


class EvidenceError(ValueError):
    """A fixed, non-sensitive reason code, never a remote error message."""


@dataclass
class Reply:
    status: int
    value: Any
    more: bool = False
    reason: str | None = None


@dataclass
class Collection:
    items: list[dict[str, Any]]
    complete: bool
    problems: list[str] = field(default_factory=list)


def positive_id(value: Any) -> bool:
    return type(value) is int and value > 0


def stamp(value: Any) -> datetime:
    if not isinstance(value, str):
        raise EvidenceError('invalid_timestamp')
    try:
        result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError:
        raise EvidenceError('invalid_timestamp') from None
    if result.tzinfo is None:
        raise EvidenceError('invalid_timestamp')
    return result.astimezone(UTC)


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def sanitize_reply(status: int, value: Any, more: bool = False) -> Reply:
    if isinstance(value, dict) and value.get('errors'):
        return Reply(status, None, reason='api_errors')
    return Reply(status, value, more)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class API:
    """Bounded HTTPS requests; credentials never follow an off-origin redirect."""
    def __init__(self, token: str, max_requests: int = 12000):
        self._headers = {'Accept': 'application/vnd.github+json',
                         'X-GitHub-Api-Version': '2022-11-28',
                         'User-Agent': 'repository-standards-F01'}
        if token:
            self._headers['Authorization'] = 'Bearer ' + token
        self._opener = urllib.request.build_opener(NoRedirect())
        self._lock = Lock()
        self.max_requests = max_requests
        self.requests = 0

    def get(self, path: str) -> Reply:
        return self.request('GET', path)

    def request(self, method: str, path: str, payload: Any = None) -> Reply:
        if (not path.startswith('/') or path.startswith('//')
                or any(ord(char) < 32 for char in path) or method not in {'GET', 'PATCH'}):
            raise EvidenceError('unsafe_api_destination')
        data = None if payload is None else canonical(payload)
        headers = dict(self._headers)
        if data is not None:
            headers['Content-Type'] = 'application/json'
        for attempt in range(4):
            with self._lock:
                if self.requests >= self.max_requests:
                    return Reply(0, None, reason='request_budget')
                self.requests += 1
            request = urllib.request.Request(API_ROOT + path, headers=headers, data=data, method=method)
            try:
                with self._opener.open(request, timeout=25) as response:
                    raw = response.read(MAX_BYTES + 1)
                    if len(raw) > MAX_BYTES:
                        return Reply(0, None, reason='response_size_budget')
                    value = json.loads(raw) if raw else None
                    return sanitize_reply(response.status, value,
                                          'rel="next"' in response.headers.get('Link', ''))
            except urllib.error.HTTPError as error:
                status = error.code
                location = error.headers.get('Location', '')
                rate_limited = status == 429 or error.headers.get('X-RateLimit-Remaining') == '0'
                # Preserve only the exact documented absence discriminator; no raw errors.
                value = None
                if status in {404, 409}:
                    try:
                        body = json.loads(error.read(4096))
                        if isinstance(body, dict) and body.get('message') in {
                                'Branch not protected', 'Git Repository is empty.'}:
                            value = {'message': body['message']}
                    except (ValueError, OSError):
                        pass
                error.close()
                if status in {301, 302, 307, 308}:
                    parsed = urllib.parse.urlsplit(location)
                    if (method != 'GET' or parsed.scheme != 'https' or parsed.netloc != 'api.github.com'
                            or not parsed.path.startswith('/') or parsed.fragment):
                        return Reply(status, None, reason='unsafe_redirect')
                    path = parsed.path + ('?' + parsed.query if parsed.query else '')
                    continue
                if not rate_limited and status not in {500, 502, 503, 504}:
                    return Reply(status, value, reason=f'http_{status}')
                if attempt == 3:
                    return Reply(status, None, reason='rate_limited' if rate_limited else f'http_{status}')
            except (ValueError, UnicodeError):
                return Reply(0, None, reason='invalid_json')
            except (OSError, urllib.error.URLError):
                if attempt == 3:
                    return Reply(0, None, reason='transport_unavailable')
            time.sleep(min(2 ** attempt, 4))
        return Reply(0, None, reason='redirect_budget')


def pages(api: Any, path: str, key: str | None = None, max_pages: int = 100) -> Collection:
    """Detect truncated/malformed/changing pages; preserve uniquely observed IDs."""
    parts = urllib.parse.urlsplit(path)
    query = dict(urllib.parse.parse_qsl(parts.query))
    found: dict[int, dict[str, Any]] = {}
    total = None
    problems: list[str] = []
    for page in range(1, max_pages + 1):
        query.update(per_page='100', page=str(page))
        reply = api.get(parts.path + '?' + urllib.parse.urlencode(query))
        value = reply.value
        if reply.status != 200 or reply.reason or (isinstance(value, dict) and value.get('errors')):
            problems.append(reply.reason or (f'http_{reply.status}' if reply.status != 200 else 'api_errors'))
            break
        if key:
            if not isinstance(value, dict) or type(value.get('total_count')) is not int:
                problems.append('invalid_collection')
                break
            count = value['total_count']
            if count < 0 or (total is not None and count != total):
                problems.append('collection_changed')
                break
            total = count
            value = value.get(key)
        if not isinstance(value, list):
            problems.append('invalid_collection')
            break
        for item in value:
            if not isinstance(item, dict) or not positive_id(item.get('id')):
                problems.append('invalid_collection_item')
                continue
            if item['id'] in found:
                problems.append('duplicate_collection_identity')
            else:
                found[item['id']] = item
        if problems:
            break
        if not reply.more and len(value) < 100:
            if total is not None and len(found) != total:
                problems.append('total_count_mismatch')
            return Collection(list(found.values()), not problems, sorted(set(problems)))
        if page == max_pages:
            problems.append('page_budget')
    return Collection(list(found.values()), False, sorted(set(problems)))


def valid_repo(row: Any) -> bool:
    return (isinstance(row, dict) and positive_id(row.get('id'))
            and isinstance(row.get('full_name'), str) and bool(NAME.fullmatch(row['full_name']))
            and isinstance(row.get('owner'), dict) and isinstance(row['owner'].get('login'), str)
            and row['full_name'].split('/')[0].casefold() == row['owner']['login'].casefold()
            and all(type(row.get(k)) is bool for k in ('private', 'archived', 'disabled', 'fork'))
            and (row.get('default_branch') is None or isinstance(row['default_branch'], str)))


def inventory_identity(rows: list[dict[str, Any]]) -> list[Any]:
    return sorted((row['id'], row['full_name'].casefold(), row['private'], row['archived'],
                   row['disabled'], row['fork'], row.get('default_branch')) for row in rows)


def discover(api: Any, owner: str) -> dict[str, Any]:
    sources = [('/user/repos?affiliation=owner&visibility=all&sort=full_name&direction=asc',
                None, 'authenticated_owned'),
               ('/installation/repositories', 'repositories', 'installation_accessible_owned'),
               (f'/users/{urllib.parse.quote(owner, safe="")}/repos?type=owner&sort=full_name&direction=asc',
                None, 'public_only')]
    first = None
    for path, key, source in sources:
        first = pages(api, path, key)
        if first.complete or first.items or source == 'public_only':
            break
    assert first is not None
    second = pages(api, path, key)
    problems = list(first.problems) + list(second.problems)
    valid_first, valid_second = [], []
    for target, collection in ((valid_first, first), (valid_second, second)):
        for row in collection.items:
            if not valid_repo(row):
                problems.append('invalid_repository_metadata')
            elif row['owner']['login'].casefold() == owner.casefold():
                target.append(row)
    if inventory_identity(valid_first) != inventory_identity(valid_second):
        problems.append('inventory_changed')
    by_id = {row['id']: row for row in valid_first + valid_second}
    if not by_id:
        problems.append('empty_inventory')
    if source == 'public_only':
        problems.append('private_visibility_unverified')
    return {'source': source, 'complete': first.complete and second.complete and not problems,
            'problems': sorted(set(problems)), 'unobservable_owned_total': None,
            'repositories': sorted(by_id.values(), key=lambda row: row['id'])}


def reconcile(api: Any, registry: list[dict[str, Any]], rows: list[dict[str, Any]],
              owner: str, now: datetime) -> dict[str, Any]:
    by_id = {row['id']: row for row in rows}
    by_name = {row['full_name'].casefold(): row for row in rows}
    matched: set[int] = set()
    seen_names: set[str] = set()
    seen_ids: set[int] = set()
    unavailable = []
    renamed = duplicates = 0
    entries: dict[int, dict[str, Any]] = {}
    for entry in registry:
        name = entry.get('repository', '')
        if not isinstance(name, str) or not NAME.fullmatch(name):
            raise EvidenceError('invalid_registry_name')
        folded = name.casefold()
        if folded in seen_names:
            duplicates += 1
            continue
        seen_names.add(folded)
        repo_id = entry.get('repository_id')
        if positive_id(repo_id):
            if repo_id in seen_ids:
                duplicates += 1
                continue
            seen_ids.add(repo_id)
        row = by_id.get(repo_id) if positive_id(repo_id) else by_name.get(folded)
        reason = 'identity_unavailable'
        if row is None:
            reply = api.get('/repos/' + name)
            if reply.status == 200 and valid_repo(reply.value):
                resolved = reply.value
                row = by_id.get(resolved['id'])
                if positive_id(repo_id) and resolved['id'] != repo_id:
                    row = None
                    reason = 'repository_identity_changed'
                elif resolved['owner']['login'].casefold() != owner.casefold():
                    reason = 'ownership_changed'
                elif row is None:
                    reason = 'not_in_discovery_snapshot'
        if row is None:
            unavailable.append({'repository': name, 'repository_id': repo_id,
                                'state': 'unknown', 'reason': reason})
            continue
        if row['id'] in matched:
            duplicates += 1
            continue
        matched.add(row['id'])
        entries[row['id']] = entry
        renamed += row['full_name'].casefold() != folded
    created = 0
    for row in rows:
        try:
            created += stamp('2026-11-10T08:09:07Z') < stamp(row.get('created_at')) <= now
        except EvidenceError:
            pass
    return {'counts': {'matched': len(matched), 'renamed': renamed,
                       'unregistered': len(by_id.keys() - matched),
                       'known_unavailable': len(unavailable), 'duplicate_registry_entries': duplicates,
                       'new_since_privacy_baseline': created},
            'unavailable': unavailable, 'entries': entries}


def observation(state: str, level: str, now: datetime, reason: str,
                source_sha: str | None = None, run_id: int | None = None,
                evidence_at: str | None = None, details: Any = None) -> dict[str, Any]:
    return {'state': state, 'level': level, 'reason': reason, 'observed_at': now.isoformat(),
            'source_sha': source_sha, 'run_id': run_id, 'evidence_at': evidence_at,
            'details': {} if details is None else details}


def run_observation(item: Any, now: datetime, expected_sha: str | None = None) -> dict[str, Any]:
    if not isinstance(item, dict):
        return observation('unknown', 'observed', now, 'no_run_evidence')
    sha, run_id = item.get('head_sha'), item.get('id')
    if not isinstance(sha, str) or not SHA.fullmatch(sha) or not positive_id(run_id):
        return observation('unknown', 'observed', now, 'invalid_run_identity')
    details = {'status': item.get('status'), 'conclusion': item.get('conclusion')}
    base = dict(source_sha=sha, run_id=run_id, details=details)
    if expected_sha is not None and sha != expected_sha:
        return observation('unknown', 'observed', now, 'commit_mismatch', **base)
    if item.get('status') != 'completed':
        return observation('unknown', 'observed', now, 'run_not_completed', **base)
    try:
        when = stamp(item.get('updated_at'))
    except EvidenceError:
        return observation('unknown', 'observed', now, 'invalid_run_timestamp', **base)
    base['evidence_at'] = when.isoformat()
    if when > now + timedelta(minutes=5):
        return observation('unknown', 'observed', now, 'future_run_timestamp', **base)
    if now - when > RUN_TTL:
        return observation('stale', 'observed', now, 'run_evidence_expired', **base)
    conclusion = item.get('conclusion')
    if conclusion == 'success':
        return observation('pass', 'executed', now, 'observed_run_success', **base)
    if conclusion in {'failure', 'timed_out', 'action_required', 'startup_failure'}:
        return observation('fail', 'observed', now, 'run_failed', **base)
    return observation('unknown', 'observed', now, 'run_not_successful', **base)


def latest_schedule(items: Any, now: datetime, workflow_id: int, branch: str) -> dict[str, Any]:
    if not isinstance(items, list) or not items:
        return observation('unknown', 'observed', now, 'no_schedule_execution_evidence')
    try:
        if any(not isinstance(item, dict) or not positive_id(item.get('id')) for item in items):
            raise EvidenceError('invalid_run_identity')
        latest = max(items, key=lambda item: (stamp(item.get('created_at')), item['id']))
    except EvidenceError:
        return observation('unknown', 'observed', now, 'invalid_schedule_history')
    if latest.get('workflow_id') != workflow_id or latest.get('head_branch') != branch or latest.get('event') != 'schedule':
        return observation('unknown', 'observed', now, 'schedule_scope_mismatch')
    return run_observation(latest, now)


def protection_observation(rules: Collection, protection: Reply, now: datetime, sha: str) -> dict[str, Any]:
    active = [row['id'] for row in rules.items if row.get('enforcement') == 'active']
    details = {'active_ruleset_ids': active, 'rulesets_complete': rules.complete,
               'branch_protection_status': protection.status}
    if active or (protection.status == 200 and isinstance(protection.value, dict)
                  and any(key in protection.value for key in
                          ('required_status_checks', 'required_pull_request_reviews', 'enforce_admins', 'restrictions'))):
        return observation('pass', 'configured', now, 'configuration_not_enforcement', sha, details=details)
    if (rules.complete and protection.status == 404 and isinstance(protection.value, dict)
            and protection.value.get('message') == 'Branch not protected'):
        return observation('fail', 'observed', now, 'protection_observed_absent', sha, details=details)
    return observation('unknown', 'observed', now, 'protection_unavailable', sha, details=details)


def exception_observation(entries: Any, now: datetime) -> dict[str, Any]:
    active = expired = invalid = 0
    expirations = []
    if not isinstance(entries, list):
        entries = [None]
    for entry in entries:
        try:
            if not isinstance(entry, dict) or not isinstance(entry.get('control'), str):
                raise ValueError
            review = date.fromisoformat(entry['review_after'])
            if review < now.date():
                expired += 1
            else:
                expiry = datetime.combine(review + timedelta(days=1), datetime.min.time(), UTC)
                expirations.append(expiry)
                active += 1
        except (KeyError, TypeError, ValueError, OverflowError):
            invalid += 1
    return observation('fail' if expired or invalid else 'pass', 'observed', now,
                       'exception_dates_checked', details={'active': active, 'expired': expired, 'invalid': invalid,
                       'next_expiry': min(expirations).isoformat() if expirations else None})


def combine(items: list[dict[str, Any]], now: datetime, reason: str, sha: str | None = None) -> dict[str, Any]:
    states = {item['state'] for item in items}
    state = next((x for x in ('fail', 'unknown', 'stale') if x in states),
                 'pass' if items and states == {'pass'} else 'unknown')
    return observation(state, 'executed' if state == 'pass' else 'observed', now, reason,
                       sha, details={'observations': items})


def check_observation(checks: Collection, statuses: Collection, now: datetime,
                      sha: str, required: list[str]) -> dict[str, Any]:
    if not checks.complete or not statuses.complete:
        return observation('unknown', 'observed', now, 'partial_check_collection', sha)
    latest: dict[tuple[Any, ...], dict[str, Any]] = {}
    names: set[str] = set()
    for check in checks.items:
        if not isinstance(check.get('name'), str) or not isinstance(check.get('app'), dict):
            return observation('unknown', 'observed', now, 'invalid_check_metadata', sha)
        key = ('check', check['app'].get('id'), check['name'])
        if key not in latest or check['id'] > latest[key]['id']:
            latest[key] = check
    for status in statuses.items:
        if not isinstance(status.get('context'), str):
            return observation('unknown', 'observed', now, 'invalid_status_metadata', sha)
        key = ('status', status['context'])
        if key not in latest or status['id'] > latest[key]['id']:
            latest[key] = status
    observations = []
    for key, item in latest.items():
        if key[0] == 'check':
            names.add(item['name'])
            normal = dict(item, updated_at=item.get('completed_at') or item.get('started_at'))
        else:
            names.add(item['context'])
            normal = dict(item, head_sha=sha, status='queued' if item.get('state') == 'pending' else 'completed',
                          conclusion={'success': 'success', 'failure': 'failure', 'error': 'failure'}.get(item.get('state')))
        observations.append(run_observation(normal, now, sha))
    if set(required) - names:
        observations.append(observation('unknown', 'observed', now, 'required_context_missing', sha))
    return combine(observations, now, 'observed_checks_only_not_enforcement', sha)


def empty_row(repo: dict[str, Any], now: datetime) -> dict[str, Any]:
    fields = ('id', 'full_name', 'private', 'fork', 'archived', 'disabled', 'default_branch', 'created_at')
    return {'repository': {key: repo.get(key) for key in fields}, 'source_sha': None,
            'head_stable': None, 'empty': None, 'risk': 'unclassified',
            'observations': {key: observation('unknown', 'observed', now, 'not_observed') for key in CONTROLS}}


def collect_repo(api: Any, repo: dict[str, Any], entry: dict[str, Any], now: datetime) -> dict[str, Any]:
    row = empty_row(repo, now)
    risk = entry.get('supply_chain_profile')
    if risk in {'baseline', 'published', 'high_risk'}:
        row['risk'] = risk
    if 'exceptions' in entry:
        row['observations']['exceptions'] = exception_observation(entry['exceptions'], now)
    else:
        row['observations']['exceptions'] = observation('unknown', 'observed', now, 'exception_registry_unavailable')
    if repo['archived'] or repo['disabled']:
        for key in ('current_ci', 'schedule_history'):
            row['observations'][key] = observation('not_applicable', 'observed', now, 'inactive_repository')
        return row
    branch = repo.get('default_branch')
    if not isinstance(branch, str) or not branch:
        return row
    root = '/repos/' + repo['full_name']
    ref_path = root + '/git/ref/heads/' + urllib.parse.quote(branch, safe='')
    first = api.get(ref_path)
    if first.status == 409 and isinstance(first.value, dict) and first.value.get('message') == 'Git Repository is empty.':
        row['empty'] = True
        for key in ('current_ci', 'schedule_history'):
            row['observations'][key] = observation('not_applicable', 'observed', now, 'empty_repository')
        return row
    value = first.value
    sha = value.get('object', {}).get('sha') if isinstance(value, dict) else None
    if first.status != 200 or not isinstance(sha, str) or not SHA.fullmatch(sha):
        return row
    row['source_sha'], row['empty'] = sha, False
    rules = pages(api, root + '/rulesets?includes_parents=true')
    protection = api.get(root + '/branches/' + urllib.parse.quote(branch, safe='') + '/protection')
    row['observations']['protection'] = protection_observation(rules, protection, now, sha)
    required = []
    if protection.status == 200 and isinstance(protection.value, dict):
        settings = protection.value.get('required_status_checks') or {}
        if isinstance(settings, dict):
            required = [name for name in settings.get('contexts', []) if isinstance(name, str)]
            required += [item['context'] for item in settings.get('checks', [])
                         if isinstance(item, dict) and isinstance(item.get('context'), str)]
    checks = pages(api, root + f'/commits/{sha}/check-runs?filter=latest', 'check_runs')
    statuses = pages(api, root + f'/commits/{sha}/statuses')
    row['observations']['current_ci'] = check_observation(checks, statuses, now, sha, required)
    workflows = pages(api, root + '/actions/workflows', 'workflows', max_pages=20)
    scheduled = []
    for workflow in workflows.items:
        if workflow.get('state') != 'active':
            continue
        query = urllib.parse.urlencode({'event': 'schedule', 'branch': branch, 'per_page': 1})
        reply = api.get(root + f'/actions/workflows/{workflow["id"]}/runs?' + query)
        payload = reply.value
        if reply.status != 200 or reply.reason or not isinstance(payload, dict):
            result = observation('unknown', 'observed', now, 'schedule_api_unavailable')
        else:
            result = latest_schedule(payload.get('workflow_runs'), now, workflow['id'], branch)
        result['details']['workflow_id'] = workflow['id']
        scheduled.append(result)
    if not workflows.complete:
        scheduled.append(observation('unknown', 'observed', now, 'workflow_list_incomplete'))
    row['observations']['schedule_history'] = combine(scheduled, now, 'schedule_history_not_schedule_configuration')
    # No record is not treated as an absent cron: F01 makes no YAML-parsing claim.
    last = api.get(ref_path)
    last_sha = last.value.get('object', {}).get('sha') if isinstance(last.value, dict) else None
    row['head_stable'] = last.status == 200 and last_sha == sha
    if not row['head_stable']:
        for key in ('current_ci', 'protection'):
            row['observations'][key] = observation('unknown', 'observed', now, 'head_changed_or_unreadable', sha)
    return row


def make_snapshot(rows: list[dict[str, Any]], discovery: dict[str, Any], reconciliation: dict[str, Any],
                  now: datetime, source_sha: str, run_id: int, baselines: list[dict[str, Any]]) -> dict[str, Any]:
    expirations = [now + EVIDENCE_TTL]
    for row in rows:
        expiry = row['observations']['exceptions']['details'].get('next_expiry')
        if expiry:
            expirations.append(stamp(expiry))
    return {'schema_version': 1, 'generated_at': now.isoformat(),
            'expires_at': min(expirations).isoformat(), 'source_repository': SOURCE_REPOSITORY,
            'source_sha': source_sha, 'source_run_id': run_id, 'python_version': sys.version.split()[0],
            'scope': 'credential_accessible_owned_including_forks_archived_disabled',
            'discovery': {key: discovery[key] for key in ('source', 'complete', 'problems', 'unobservable_owned_total')},
            'reconciliation': {key: reconciliation[key] for key in ('counts', 'unavailable')},
            'baselines': baselines, 'repositories': sorted(rows, key=lambda row: row['repository']['id']),
            'input_hashes': {}, 'assurance': 'not_certified'}


def validate_snapshot(snapshot: dict[str, Any], now: datetime) -> None:
    try:
        if snapshot['schema_version'] != 1 or not SHA.fullmatch(snapshot['source_sha']):
            raise EvidenceError('invalid_snapshot_identity')
        generated, expires = stamp(snapshot['generated_at']), stamp(snapshot['expires_at'])
        if generated > now + timedelta(minutes=5) or now > expires or not timedelta(0) < expires - generated <= EVIDENCE_TTL:
            raise EvidenceError('stale_or_future_snapshot')
        identities = set()
        for row in snapshot['repositories']:
            repo_id = row['repository']['id']
            if not positive_id(repo_id) or repo_id in identities:
                raise EvidenceError('duplicate_or_invalid_repository_id')
            identities.add(repo_id)
            if set(row['observations']) != set(CONTROLS):
                raise EvidenceError('missing_observations')
            for key, obs in row['observations'].items():
                if obs['state'] not in STATES or obs['level'] not in {'observed', 'configured', 'executed'}:
                    raise EvidenceError('invalid_observation_state')
                if not now - EVIDENCE_TTL <= stamp(obs['observed_at']) <= now + timedelta(minutes=5):
                    raise EvidenceError('future_observation')
                if obs['state'] == 'pass' and key in {'current_ci', 'schedule_history'}:
                    nested = obs['details'].get('observations', [])
                    if obs['level'] != 'executed' or not nested or any(item['state'] != 'pass' for item in nested):
                        raise EvidenceError('unsupported_execution_claim')
                    for item in nested:
                        if (not positive_id(item['run_id']) or not SHA.fullmatch(item['source_sha'])
                                or item['level'] != 'executed' or item['details'].get('conclusion') != 'success'
                                or item['details'].get('status') != 'completed'
                                or now - stamp(item['evidence_at']) > RUN_TTL
                                or stamp(item['evidence_at']) > now + timedelta(minutes=5)):
                            raise EvidenceError('unsupported_execution_claim')
                    if key == 'current_ci' and (row['head_stable'] is not True or
                            any(item['source_sha'] != row['source_sha'] for item in nested)):
                        raise EvidenceError('unsupported_commit_claim')
                if key == 'protection' and obs['state'] == 'pass':
                    proof = obs['details']
                    if obs['level'] != 'configured' or not (
                            proof.get('active_ruleset_ids') or proof.get('branch_protection_status') == 200):
                        raise EvidenceError('unsupported_configuration_claim')
                if key == 'enforcement' and obs['state'] == 'pass':
                    raise EvidenceError('enforcement_not_tested')
        for row in snapshot['repositories']:
            expiry = row['observations']['exceptions']['details'].get('next_expiry')
            if expiry and expires > stamp(expiry):
                raise EvidenceError('exception_expiry_exceeded')
    except (KeyError, TypeError, AttributeError):
        raise EvidenceError('invalid_snapshot_structure') from None


def drift_key(snapshot: dict[str, Any]) -> str:
    material = [{'id': row['repository']['id'], 'metadata': row['repository'],
                 'sha': row['source_sha'], 'states': {key: value['state'] for key, value in row['observations'].items()}}
                for row in snapshot['repositories']]
    return digest({'repositories': sorted(material, key=lambda row: row['id']),
                   'reconciliation': snapshot['reconciliation']['counts']})


def public_report(snapshot: dict[str, Any]) -> dict[str, Any]:
    rows = snapshot['repositories']
    counts = {'observed_owned': len(rows), 'private': sum(row['repository']['private'] for row in rows),
              'archived': sum(row['repository']['archived'] for row in rows),
              'disabled': sum(row['repository']['disabled'] for row in rows),
              'forks': sum(row['repository']['fork'] for row in rows),
              'empty_observed': sum(row['empty'] is True for row in rows),
              'active_including_forks': sum(not row['repository']['archived'] and not row['repository']['disabled'] for row in rows),
              'legacy_eligible': sum(not any(row['repository'][key] for key in ('archived', 'disabled', 'fork')) for row in rows)}
    count_names = ('matched', 'renamed', 'unregistered', 'known_unavailable',
                   'duplicate_registry_entries', 'new_since_privacy_baseline')
    reconciliation = {name: snapshot['reconciliation']['counts'][name] for name in count_names}
    return {'schema_version': 1, 'visibility': 'aggregate_only', 'assurance': 'not_certified',
            'generated_at': snapshot['generated_at'], 'expires_at': snapshot['expires_at'],
            'source_repository': SOURCE_REPOSITORY, 'source_sha': snapshot['source_sha'],
            'source_run_id': snapshot['source_run_id'], 'python_version': snapshot['python_version'],
            'scope': snapshot['scope'], 'discovery_source': snapshot['discovery']['source'],
            'inventory_complete_for_declared_scope': snapshot['discovery']['complete'],
            'unobservable_owned_total': None, 'counts': counts, 'reconciliation': reconciliation,
            'controls': {key: {state: sum(row['observations'][key]['state'] == state for row in rows)
                               for state in STATES} for key in CONTROLS},
            'baselines': [{key: item[key] for key in
                           ('scope', 'observed_at', 'count', 'expected_historical_count',
                            'source_sha256', 'compliance_trend_comparable')}
                          for item in snapshot['baselines']], 'evidence_sha256': digest(snapshot),
            'drift_key': drift_key(snapshot), 'input_hashes': snapshot.get('input_hashes', {})}



def validate_public(report: dict[str, Any], now: datetime, require_complete: bool = False) -> None:
    """Reject stale/tampered reports before issue updates or external consumption."""
    try:
        if (report['assurance'] != 'not_certified' or report['visibility'] != 'aggregate_only'
                or report['source_repository'] != SOURCE_REPOSITORY
                or not SHA.fullmatch(report['source_sha'])):
            raise EvidenceError('invalid_public_identity')
        generated, expires = stamp(report['generated_at']), stamp(report['expires_at'])
        if generated > now + timedelta(minutes=5) or now > expires or not timedelta(0) < expires - generated <= EVIDENCE_TTL:
            raise EvidenceError('stale_public_evidence')
        if require_complete and report['inventory_complete_for_declared_scope'] is not True:
            raise EvidenceError('partial_inventory_not_authoritative')
        count = report['counts']['observed_owned']
        if type(count) is not int or count < 0 or set(report['controls']) != set(CONTROLS):
            raise EvidenceError('invalid_denominator')
        for values in report['controls'].values():
            if set(values) != set(STATES) or any(type(n) is not int or n < 0 for n in values.values()) or sum(values.values()) != count:
                raise EvidenceError('aggregate_count_mismatch')
        if report['controls']['enforcement']['pass']:
            raise EvidenceError('enforcement_not_tested')
    except (KeyError, TypeError, AttributeError):
        raise EvidenceError('invalid_public_structure') from None


def markdown(report: dict[str, Any]) -> str:
    lines = [START, '## F01 estate evidence', '',
             f"Observed owned repositories: **{report['counts']['observed_owned']}**.",
             f"Inventory complete for credential-visible scope: **{report['inventory_complete_for_declared_scope']}**.",
             'Unobservable owned total is unknown. This is not an estate compliance certificate.', '',
             '| Control | Pass | Fail | Unknown | Stale | Not applicable |', '| --- | ---: | ---: | ---: | ---: | ---: |']
    for key in CONTROLS:
        lines.append('| ' + key + ' | ' + ' | '.join(str(report['controls'][key][state]) for state in STATES) + ' |')
    lines += ['', 'Protection passes mean observed configuration only. CI passes cover observed exact-commit checks, not proven merge enforcement.',
              'Schedule history does not infer cron configuration; a workflow with no scheduled run remains unknown.',
              f"Generated: {report['generated_at']}; expires: {report['expires_at']}.",
              f"Source: `{report['source_sha']}`; audit run: `{report['source_run_id']}`.", END]
    return '\n'.join(lines)


def exclusive_write(path: Path, content: bytes, mode: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_NOFOLLOW', 0), mode)
        with os.fdopen(fd, 'wb') as handle:
            handle.write(content)
    except OSError:
        raise EvidenceError('output_not_fresh_or_writable') from None


def write_outputs(snapshot: dict[str, Any], private_path: Path, public_dir: Path, now: datetime) -> dict[str, Any]:
    validate_snapshot(snapshot, now)
    if private_path.resolve().is_relative_to(public_dir.resolve()):
        raise EvidenceError('private_output_inside_public_directory')
    report = public_report(snapshot)
    exclusive_write(private_path, canonical(snapshot) + b'\n', 0o600)
    files = {'estate-evidence.json': json.dumps(report, indent=2, sort_keys=True).encode() + b'\n',
             'estate-evidence.md': markdown(report).encode() + b'\n'}
    checksums = ''.join(hashlib.sha256(data).hexdigest() + '  ' + name + '\n' for name, data in files.items())
    for name, data in files.items():
        exclusive_write(public_dir / name, data, 0o644)
    exclusive_write(public_dir / 'CHECKSUMS.sha256', checksums.encode(), 0o644)
    return report


def reconcile_text(body: str, block: str) -> str:
    legacy_start, legacy_end = '<!-- estate-conformance:start -->', '<!-- estate-conformance:end -->'
    for left, right in ((START, END), (legacy_start, legacy_end)):
        if body.count(left) != body.count(right) or body.count(left) > 1:
            raise EvidenceError('ambiguous_issue_markers')
        if left in body and body.index(left) > body.index(right):
            raise EvidenceError('ambiguous_issue_markers')
    # Retire the bounded legacy-generated section, never preserve private rows in
    # a newly published aggregate receipt. Notes outside generated blocks survive.
    if legacy_start in body:
        before, rest = body.split(legacy_start, 1)
        _, after = rest.split(legacy_end, 1)
        body = before + ('' if START in body else block) + after
    if START in body:
        left, rest = body.split(START, 1)
        _, right = rest.split(END, 1)
        return left + block + right
    return body.rstrip() + '\n\n' + block


def schema_check(document: dict[str, Any], path: Path) -> None:
    # Only a repository-owned local schema is compiled; no remote references.
    import fastjsonschema
    schema = json.loads(path.read_text(encoding='utf-8'))
    if re.search(r'"\$ref"\s*:\s*"(?!#)', json.dumps(schema)):
        raise EvidenceError('remote_schema_reference')
    try:
        fastjsonschema.compile(schema, use_default=False)(document)
    except fastjsonschema.JsonSchemaException:
        raise EvidenceError('schema_validation_failed') from None


def baselines(root: Path) -> list[dict[str, Any]]:
    inputs = [('audits/latest/estate-conformance.json', 'legacy_active_nonfork', 163),
              ('conductor/tracks/privacy_secrets_rollout_20261110/metadata.json', 'privacy_all_owned', 303)]
    result = []
    for relative, scope, expected in inputs:
        path = root / relative
        data = path.read_bytes()
        content = json.loads(data)
        if scope == 'legacy_active_nonfork':
            count = content.get('repository_count', len(content.get('repositories', [])))
            observed_at = content.get('generated_at')
        else:
            count = content['inventory_counts']['total']
            observed_at = content['rollout_checkpoint']['as_of']
        # Historical inputs are preserved, never silently rewritten to current counts.
        result.append({'scope': scope, 'observed_at': observed_at, 'count': count,
                       'expected_historical_count': expected, 'source_sha256': hashlib.sha256(data).hexdigest(),
                       'compliance_trend_comparable': False})
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--owner', default='edithatogo')
    parser.add_argument('--registry', type=Path, default=Path('registry/repositories.json'))
    parser.add_argument('--private-output', type=Path, required=True)
    parser.add_argument('--public-dir', type=Path, required=True)
    parser.add_argument('--source-sha', default=os.environ.get('GITHUB_SHA', ''))
    parser.add_argument('--run-id', type=int, default=int(os.environ.get('GITHUB_RUN_ID', '0')))
    parser.add_argument('--workers', type=int, default=4)
    args = parser.parse_args(argv)
    if not re.fullmatch(r'[A-Za-z0-9-]+', args.owner) or not SHA.fullmatch(args.source_sha) or not 1 <= args.workers <= 4:
        print('{"error":"invalid_audit_arguments"}')
        return 2
    # Retrieve each candidate before selecting it; no short-circuit leaves a token behind.
    tokens = [os.environ.pop(key, '') for key in ('ESTATE_AUDIT_TOKEN', 'GH_TOKEN', 'GITHUB_TOKEN')]
    token = next((item for item in tokens if item), '')
    root = Path(__file__).resolve().parents[1]
    try:
        if not token:
            raise EvidenceError('estate_credential_unavailable')
        api = API(token)
        now = datetime.now(UTC)
        registry = json.loads(args.registry.read_text(encoding='utf-8-sig'))['repositories']
        inventory = discover(api, args.owner)
        reconciliation = reconcile(api, registry, inventory['repositories'], args.owner, now)
        entries = reconciliation.pop('entries')
        def collect(repo):
            try:
                return collect_repo(api, repo, entries.get(repo['id'], {}), now)
            except (OSError, ValueError, KeyError, TypeError, AttributeError):
                return empty_row(repo, now)
        with ThreadPoolExecutor(max_workers=args.workers) as executor:
            rows = list(executor.map(collect, inventory['repositories']))
        snapshot = make_snapshot(rows, inventory, reconciliation, now, args.source_sha, args.run_id, baselines(root))
        snapshot['input_hashes'] = {name: hashlib.sha256(path.read_bytes()).hexdigest() for name, path in {
            'registry': args.registry, 'collector': Path(__file__),
            'private_schema': root / 'schemas/estate-evidence.schema.json',
            'public_schema': root / 'schemas/estate-evidence-public.schema.json'}.items()}
        schema_check(snapshot, root / 'schemas/estate-evidence.schema.json')
        schema_check(public_report(snapshot), root / 'schemas/estate-evidence-public.schema.json')
        report = write_outputs(snapshot, args.private_output, args.public_dir, datetime.now(UTC))
        print(json.dumps(report, sort_keys=True))  # Strictly allowlisted aggregates, never raw rows.
        return 0 if inventory['complete'] else 3
    except EvidenceError as error:
        code = str(error) if re.fullmatch(r'[a-z_]{1,64}', str(error)) else 'invalid_evidence'
        print(json.dumps({'error': code}))
        return 2
    except (OSError, ValueError, KeyError, TypeError, ImportError):
        print('{"error":"evidence_collection_or_validation_unavailable"}')
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
