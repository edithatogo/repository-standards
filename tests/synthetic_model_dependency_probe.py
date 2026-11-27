"""Explicit Linux canary; synthetic wheels only, no model or network requests."""

import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from zipfile import ZipFile, ZipInfo


def main():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        wheelhouse = root / 'wheels'
        wheelhouse.mkdir()
        locks = []
        for name, dependency in (('fixture_alpha', 'fixture-beta==1.0'), ('fixture_beta', None)):
            wheel = wheelhouse / f'{name}-1.0-py3-none-any.whl'
            info = f'{name}-1.0.dist-info'
            with ZipFile(wheel, 'w') as archive:
                metadata = f'Metadata-Version: 2.1\nName: {name.replace("_", "-")}\nVersion: 1.0\n'
                if dependency:
                    metadata += f'Requires-Dist: {dependency}\n'
                archive.writestr(ZipInfo(info + '/METADATA'), metadata + '\n')
                archive.writestr(ZipInfo(info + '/WHEEL'), 'Wheel-Version: 1.0\nGenerator: synthetic-fixture\nRoot-Is-Purelib: true\nTag: py3-none-any\n')
                archive.writestr(ZipInfo(info + '/RECORD'), '')
            locks.append(f'{name}==1.0 --hash=sha256:{hashlib.sha256(wheel.read_bytes()).hexdigest()}')
        lock = root / 'requirements.lock'
        cmd = ['unshare', '--user', '--map-root-user', '--net', '--fork', sys.executable,
               '-I', '-m', 'pip', '--isolated', 'install', '--dry-run', '--ignore-installed',
               '--no-cache-dir', '--require-hashes', '--no-index', '--only-binary=:all:',
               '--find-links', str(wheelhouse), '-r', str(lock)]
        env = {'PATH': '/usr/bin:/bin', 'HOME': tmp, 'PIP_CONFIG_FILE': '/dev/null', 'PIP_DISABLE_PIP_VERSION_CHECK': '1'}
        cases = [('complete_closure', '\n'.join(locks)+'\n', 0, 'Would install fixture-alpha-1.0 fixture-beta-1.0'),
                 ('missing_transitive_hash', locks[0]+'\n', 1, 'Hashes are required'),
                 ('wrong_wheel_digest', '\n'.join([locks[0], locks[1].rsplit(':', 1)[0]+':'+'0'*64])+'\n', 1, 'DO NOT MATCH THE HASHES')]
        results = []
        for name, content, expected, marker in cases:
            lock.write_text(content)
            result = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=30)
            passed = result.returncode == expected and marker.lower() in (result.stdout + result.stderr).lower()
            results.append({'case': name, 'exit_code': result.returncode, 'passed': passed})
            if not passed:
                print(json.dumps({'cases': results, 'sandbox_qualified': False, 'model_executed': False}))
                return 2
        print(json.dumps({'cases': results, 'sandbox_qualified': False, 'model_executed': False}))
        return 0


if __name__ == '__main__':
    raise SystemExit(main())
