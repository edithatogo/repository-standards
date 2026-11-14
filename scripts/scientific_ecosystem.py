#!/usr/bin/env python3
"""Read-only scientific policy and receipt validation; never runtime proof."""
from __future__ import annotations

import argparse
from datetime import datetime
import json
import math
from pathlib import Path
import re

CANDIDATE_CHECKS = ('security', 'build', 'numerical', 'consumer', 'resource')
STAGES = ('runtime-build', 'compiler-bootstrap', 'hpc-install', 'scheduler-run')


def validate_policy(policy: dict) -> list[str]:
    """Reject unknown providers, reverse application edges and cycles."""
    errors = []
    caps = policy.get('capabilities', {})
    if not isinstance(caps, dict) or not caps:
        return ['capabilities must be a nonempty object']
    for name, item in caps.items():
        if not isinstance(item, dict):
            return ['capability must be an object']
        if item.get('kind') not in ('library', 'application', 'policy'):
            errors.append(f'{name}: unknown kind')
        if not item.get('owns') or not item.get('repository'):
            errors.append(f'{name}: missing owner scope')
        providers = item.get('providers')
        if not isinstance(providers, list) or any(not isinstance(x, str) for x in providers):
            return ['providers must be a string list']
    if errors:
        return errors
    caps = {name: {**item, 'providers': list(item['providers'])} for name, item in caps.items()}
    adapters = policy.get('planned_adapters', [])
    if not isinstance(adapters, list):
        return ['planned_adapters must be a list']
    for adapter in adapters:
        if not isinstance(adapter, dict):
            return ['planned adapter must be an object']
        consumer, provider = adapter.get('consumer'), adapter.get('provider')
        if not isinstance(consumer, str) or not isinstance(provider, str) or consumer not in caps or provider not in caps:
            return ['planned adapter has unknown provider or consumer']
        caps[consumer]['providers'].append(provider)
    for name, item in caps.items():
        for provider in item['providers']:
            if provider not in caps:
                errors.append(f'{name}: unknown provider {provider}')
            elif item['kind'] == 'library' and caps[provider].get('kind') == 'application':
                errors.append(f'{name}: library depends on application {provider}')
    if errors:
        return errors
    visited, active = set(), set()

    def visit(name):
        if name in active:
            errors.append(f'dependency cycle at {name}')
            return
        if name in visited:
            return
        active.add(name)
        for provider in caps[name]['providers']:
            visit(provider)
        active.remove(name)
        visited.add(name)

    for name in caps:
        visit(name)
    return errors


def validate_candidate(record: dict) -> list[str]:
    """Require all promotion checks and actionable retained-version exceptions."""
    errors = []
    if not record.get('candidate') or not re.fullmatch(r'[0-9a-f]{40}', str(record.get('source_revision', ''))):
        errors.append('candidate and exact revision required')
    status = record.get('status')
    if status not in ('candidate', 'qualified', 'blocked'):
        errors.append('unknown candidate status')
    checks = record.get('checks', {})
    if not isinstance(checks, dict):
        return errors + ['checks must be an object']
    if status == 'qualified':
        for gate in CANDIDATE_CHECKS:
            if checks.get(gate) != 'pass':
                errors.append(f'qualification requires {gate} pass')
    if status == 'blocked':
        exception = record.get('exception', {})
        if not isinstance(exception, dict):
            exception = {}
        for key in ('blocker', 'capability', 'owner', 'revisit'):
            if not isinstance(exception.get(key), str) or not exception[key].strip():
                errors.append(f'exception.{key} required')
    return errors


def validate_receipt(record: dict) -> list[str]:
    """Validate terminal resource evidence without conflating stage claims."""
    errors = []
    for key in ('repository', 'revision', 'runner', 'cache_state', 'started_at', 'finished_at', 'stop_reason'):
        if not isinstance(record.get(key), str) or not record[key].strip():
            errors.append(f'{key} required')
    if not re.fullmatch(r'[0-9a-f]{40}', str(record.get('revision', ''))):
        errors.append('exact revision required')
    for key in ('source_hashes', 'toolchains'):
        if not isinstance(record.get(key), dict) or not record[key]:
            errors.append(f'{key} required')
    toolchains = record.get('toolchains', {})
    if isinstance(toolchains, dict) and any(not isinstance(v, str) or not v.strip() for v in toolchains.values()):
        errors.append('toolchain identities must be nonempty strings')
    hashes = record.get('source_hashes', {})
    if isinstance(hashes, dict) and any(not re.fullmatch(r'[0-9a-f]{64}', str(v)) for v in hashes.values()):
        errors.append('source hashes must be SHA256')
    command = record.get('command')
    if not isinstance(command, list) or not command or any(not isinstance(x, str) for x in command) or not command[0].strip():
        errors.append('command argv required')
    if type(record.get('concurrency')) is not int or record['concurrency'] < 1:
        errors.append('positive integer concurrency required')
    try:
        start = datetime.fromisoformat(record.get('started_at', ''))
        finish = datetime.fromisoformat(record.get('finished_at', ''))
        if start.tzinfo is None or finish.tzinfo is None or finish < start:
            errors.append('ordered timezone-aware timestamps required')
    except (TypeError, ValueError):
        errors.append('valid timestamps required')
    if record.get('result') not in ('pass', 'fail', 'partial'):
        errors.append('terminal result required')
    if type(record.get('exit_code')) is not int:
        errors.append('integer exit code required; use negative signal for termination')
    if record.get('result') == 'pass' and (record.get('exit_code') != 0 or record.get('stop_reason') != 'completed'):
        errors.append('pass requires zero exit and completed reason')
    stage = record.get('stage')
    if stage not in STAGES:
        errors.append('known stage required')
    if stage == 'compiler-bootstrap':
        for key in ('packaging_requirement', 'bootstrap_binary'):
            if not isinstance(record.get(key), str) or not record[key].strip():
                errors.append(f'compiler-bootstrap requires {key}')
        components = record.get('source_built_components')
        if not isinstance(components, list) or not components or any(not isinstance(x, str) or not x.strip() for x in components):
            errors.append('source_built_components must be a nonempty string list')
    if stage == 'scheduler-run' and (not isinstance(record.get('job_id'), str) or not record['job_id'].strip()):
        errors.append('scheduler-run requires job_id')
    measurement = record.get('measurement', {})
    if not isinstance(measurement, dict):
        return errors + ['measurement must be an object']
    if measurement.get('memory_method') not in ('descendant-rss', 'cgroup-peak'):
        errors.append('memory requires descendant-rss or cgroup-peak')
    for key in ('interval_seconds', 'peak_rss_bytes', 'disk_growth_bytes'):
        value = measurement.get(key)
        if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
            errors.append(f'finite nonnegative measurement.{key} required')
    if measurement.get('memory_method') == 'descendant-rss' and measurement.get('interval_seconds') == 0:
        errors.append('sampling interval must be positive')
    if not isinstance(measurement.get('limitations'), list) or not measurement['limitations'] or any(not isinstance(x, str) or not x.strip() for x in measurement['limitations']):
        errors.append('measurement limitations required')
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('kind', choices=('policy', 'candidate', 'receipt'))
    parser.add_argument('path', type=Path)
    args = parser.parse_args()
    try:
        record = json.loads(args.path.read_text())
        if not isinstance(record, dict):
            raise ValueError('document must be an object')
        errors = {'policy': validate_policy, 'candidate': validate_candidate, 'receipt': validate_receipt}[args.kind](record)
    except (OSError, ValueError, TypeError) as exc:
        errors = [str(exc)]
    print(json.dumps({'validation': 'fail' if errors else 'pass', 'errors': errors}))
    return int(bool(errors))


if __name__ == '__main__':
    raise SystemExit(main())
