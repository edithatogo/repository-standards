"""Advisory native Git and CI retry baseline; never publish or mutate refs."""

import os
import re
import subprocess
from pathlib import Path


SHA = re.compile(r'[0-9a-f]{40}')
MAX_ATTEMPTS = 3  # Initial run and at most two reruns.


def valid_sha(value):
    return isinstance(value, str) and SHA.fullmatch(value) is not None


def merge_preview(repo: Path, head, base):
    """Preview a merge in a caller-created, isolated bare object store.

    The caller must supply trusted configuration, acquired objects only, no
    credentials/network and an isolated process. The result is not acceptance.
    """
    if not valid_sha(head) or not valid_sha(base):
        raise ValueError('full commit SHAs required')
    env = {key: os.environ[key] for key in ('PATH', 'SYSTEMROOT', 'WINDIR') if key in os.environ}
    env.update(GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull,
               GIT_TERMINAL_PROMPT='0', GIT_NO_REPLACE_OBJECTS='1',
               GIT_ATTR_NOSYSTEM='1', GIT_NO_LAZY_FETCH='1', LC_ALL='C')

    def git(*args):
        return subprocess.run(['git', '-C', str(repo), '-c', f'core.attributesFile={os.devnull}', *args], env=env,
                              capture_output=True, timeout=60, check=False)

    bare = git('rev-parse', '--is-bare-repository')
    if bare.returncode or bare.stdout.strip() != b'true':
        raise ValueError('isolated bare repository required')
    # Refuse configurations capable of changing merge semantics or invoking helpers.
    config = git('config', '--local', '--no-includes', '--name-only', '--get-regexp',
                 r'^(merge\.|include\.|includeif\.|diff\.|filter\.|core\.(attributesfile|fsmonitor)|extensions\.)')
    if config.returncode != 1 or config.stdout:
        raise ValueError('unsupported local Git configuration')
    if any((repo / path).exists() for path in ('info/attributes', 'info/grafts', 'shallow')):
        raise ValueError('unsupported local Git metadata')
    for revision in (head, base):
        obj = git('cat-file', '-t', revision)
        if obj.returncode or obj.stdout.strip() != b'commit':
            raise ValueError('commit unavailable')
        paths = git('ls-tree', '-r', '-z', '--name-only', revision)
        if paths.returncode:
            raise ValueError('tree unavailable')
        # ponytail: hold attributes until their merge-driver semantics are qualified.
        if any(path.rsplit(b'/', 1)[-1] == b'.gitattributes' for path in paths.stdout.split(b'\0')):
            return {'disposition': 'hold_attributes', 'head_sha': head, 'base_sha': base}
    result = git('merge-tree', '--write-tree', head, base)
    receipt = {'head_sha': head, 'base_sha': base}
    if result.returncode == 1:
        return {'disposition': 'unresolved_conflict', **receipt}
    tree = result.stdout.splitlines()[0].decode('ascii') if result.stdout else ''
    if result.returncode or not valid_sha(tree):
        raise ValueError('merge preview failed')
    return {'disposition': 'candidate_tree', 'tree_sha': tree, **receipt}


def retry_disposition(run, expected_head, tested_base, current_base):
    """Classify trusted GitHub metadata, not untrusted job log text.

    The caller supplies independently observed tested and current base SHAs.
    A retry candidate still requires fresh PR/hold/policy checks and a writer.
    """
    if not isinstance(run, dict) or not all(valid_sha(s) for s in (expected_head, tested_base, current_base)):
        return 'hold'
    if (tested_base != current_base or run.get('head_sha') != expected_head
            or run.get('event') != 'pull_request' or type(run.get('id')) is not int
            or run['id'] < 1 or type(run.get('run_attempt')) is not int or run['run_attempt'] < 1):
        return 'hold'
    if run.get('status') in ('queued', 'in_progress', 'waiting', 'requested', 'pending'):
        return 'wait'
    if run.get('status') != 'completed' or run.get('conclusion') != 'startup_failure':
        return 'hold'
    if run['run_attempt'] >= MAX_ATTEMPTS:
        return 'budget_exhausted'
    return 'inspect_retry_candidate'
