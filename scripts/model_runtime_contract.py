"""Build a bounded, synthetic-only offline dependency probe; no model execution."""

import hashlib
import re
from pathlib import Path


MAX_LOCK = 64 * 1024
MAX_WHEELS = 256
MAX_BYTES = 512 * 1024 * 1024


class RuntimeContractError(ValueError):
    """Fixed rejection reason."""


def matches(value, pattern):
    return isinstance(value, str) and re.fullmatch(pattern, value) is not None


def lock_hashes(raw):
    if not isinstance(raw, bytes) or not 0 < len(raw) <= MAX_LOCK:
        raise RuntimeContractError('lock_size')
    names, hashes = set(), set()
    try:
        lines = raw.decode('ascii').splitlines()
    except UnicodeError:
        raise RuntimeContractError('invalid_lock') from None
    for line in lines:
        match = re.fullmatch(r'([A-Za-z0-9][A-Za-z0-9_.-]*)==([A-Za-z0-9][A-Za-z0-9._+!-]*)( +--hash=sha256:[0-9a-f]{64})+', line)
        if not match:
            raise RuntimeContractError('invalid_lock')
        name = re.sub(r'[-_.]+', '-', match[1]).lower()
        if name in names:
            raise RuntimeContractError('duplicate_package')
        names.add(name)
        hashes.update(re.findall(r'--hash=sha256:([0-9a-f]{64})', line))
    if not names or len(names) > MAX_WHEELS:
        raise RuntimeContractError('lock_budget')
    return hashes


def dependency_probe_argv(root, *, image, expected_lock_digest):
    """Trusted caller provisions immutable private inputs and a qualified local image.

    The returned argv is a dry-run resolution candidate, not proof of sandbox
    enforcement or complete dependency closure. No model or arbitrary command.
    A future executor must independently verify isolation and enforce timeout.
    """
    if (not matches(image, r'[a-z0-9][a-z0-9./_-]*@sha256:[0-9a-f]{64}')
            or not matches(expected_lock_digest, r'[0-9a-f]{64}')):
        raise RuntimeContractError('invalid_pin')
    root = Path(root).absolute()
    try:
        if (not root.is_dir() or root.resolve(strict=True) != root or root == Path('/')
                or ',' in str(root) or any(ord(c) < 32 for c in str(root))
                or {p.name for p in root.iterdir()} != {'requirements.lock', 'wheels'}):
            raise RuntimeContractError('invalid_input_directory')
        lock, wheelhouse = root / 'requirements.lock', root / 'wheels'
        if (lock.is_symlink() or not lock.is_file() or lock.stat().st_size > MAX_LOCK
                or wheelhouse.is_symlink() or not wheelhouse.is_dir()):
            raise RuntimeContractError('invalid_input_directory')
        raw = lock.read_bytes()
        if hashlib.sha256(raw).hexdigest() != expected_lock_digest:
            raise RuntimeContractError('lock_digest_mismatch')
        hashes = lock_hashes(raw)
        wheels = list(wheelhouse.iterdir())
        if not 0 < len(wheels) <= MAX_WHEELS:
            raise RuntimeContractError('wheel_inventory')
        total = 0
        for wheel in wheels:
            if (wheel.is_symlink() or not wheel.is_file()
                    or not matches(wheel.name, r'[A-Za-z0-9][A-Za-z0-9_.+-]*\.whl')):
                raise RuntimeContractError('wheel_inventory')
            total += wheel.stat().st_size
            if total > MAX_BYTES:
                raise RuntimeContractError('wheel_budget')
            with wheel.open('rb') as stream:
                if hashlib.file_digest(stream, 'sha256').hexdigest() not in hashes:
                    raise RuntimeContractError('unlocked_wheel')
    except OSError:
        raise RuntimeContractError('input_unavailable') from None
    return ['docker', 'run', '--rm', '--pull=never', '--platform=linux/amd64',
            '--network=none', '--read-only', '--cap-drop=ALL', '--security-opt=no-new-privileges',
            '--user=65534:65534', '--pids-limit=64', '--memory=1g', '--memory-swap=1g', '--cpus=1',
            '--ipc=none', '--tmpfs', '/tmp:rw,noexec,nosuid,nodev,size=128m',
            '--mount', f'type=bind,src={root},dst=/input,readonly',
            '--env', 'HOME=/tmp', '--env', 'PIP_CONFIG_FILE=/dev/null',
            '--env', 'PIP_DISABLE_PIP_VERSION_CHECK=1', '--env', 'HF_HUB_OFFLINE=1',
            '--env', 'TRANSFORMERS_OFFLINE=1', '--entrypoint', 'python', image,
            '-I', '-m', 'pip', '--isolated', 'install', '--dry-run', '--ignore-installed',
            '--no-cache-dir', '--require-hashes', '--no-index', '--only-binary=:all:',
            '--find-links', '/input/wheels', '-r', '/input/requirements.lock']
