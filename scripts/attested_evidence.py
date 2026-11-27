"""Authenticate exact evidence bytes with the installed trusted GitHub CLI.

Only non-reusable, main-branch GitHub-hosted producers are supported initially.
The caller must obtain the expected digest and producer identity independently.
No payload claims, current snapshot, authorization or scientific validity follow
from a producer attestation. The CLI installation/configuration is trusted.
"""

import argparse
import hashlib
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path


MAX_BYTES = 16 * 1024 * 1024


class AttestationError(ValueError):
    """Fixed reason code without untrusted content or CLI output."""


def matches(value, pattern):
    return isinstance(value, str) and re.fullmatch(pattern, value) is not None


def authenticate_bytes(raw, *, expected_digest, producer_repository, producer_revision, workflow):
    if (not matches(expected_digest, r'[0-9a-f]{64}')
            or not matches(producer_repository, r'[A-Za-z0-9][A-Za-z0-9-]{0,99}/[A-Za-z0-9_][A-Za-z0-9_.-]{0,99}')
            or not matches(producer_revision, r'[0-9a-f]{40}')
            or not matches(workflow, r'[A-Za-z0-9_][A-Za-z0-9_.-]{0,99}\.ya?ml')):
        raise AttestationError('invalid_trusted_context')
    if not isinstance(raw, bytes) or not 0 < len(raw) <= MAX_BYTES:
        raise AttestationError('artifact_size')
    digest = hashlib.sha256(raw).hexdigest()
    if digest != expected_digest:
        raise AttestationError('digest_mismatch')
    try:
        with tempfile.TemporaryDirectory(prefix='evidence-verification-') as directory:
            artifact = Path(directory) / 'artifact.json'
            artifact.write_bytes(raw)
            args = ['gh', 'attestation', 'verify', str(artifact),
                    '--hostname', 'github.com', '--repo', producer_repository,
                    '--source-digest', producer_revision, '--signer-digest', producer_revision,
                    '--source-ref', 'refs/heads/main',
                    '--signer-workflow', f'{producer_repository}/.github/workflows/{workflow}',
                    '--cert-oidc-issuer', 'https://token.actions.githubusercontent.com',
                    '--predicate-type', 'https://slsa.dev/provenance/v1',
                    '--digest-alg', 'sha256', '--deny-self-hosted-runners', '--limit', '10']
            env = dict(os.environ, GH_HOST='github.com', GH_PROMPT_DISABLED='1',
                       GH_NO_UPDATE_NOTIFIER='1', GH_NO_EXTENSION_UPDATE_NOTIFIER='1')
            result = subprocess.run(args, cwd=directory, env=env, stdin=subprocess.DEVNULL,
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                    timeout=120, check=False)
            if result.returncode != 0 or artifact.read_bytes() != raw:
                raise AttestationError('attestation_unverified')
    except (OSError, subprocess.SubprocessError):
        raise AttestationError('attestation_unverified') from None
    return {'artifact_sha256': digest, 'producer_attestation_verified': True,
            'snapshot_verified': False, 'write_authorized': False}


def inspect_attested_receipt(raw, *, expected_digest, producer_repository, producer_revision,
                             workflow, repository, revision, required_checks, not_before, now):
    """Validate claims against trusted context, then authenticate those exact bytes."""
    from verify_receipt import inspect_receipt

    result = inspect_receipt(raw, expected_digest=expected_digest, repository=repository,
                             revision=revision, required_checks=required_checks,
                             not_before=not_before, now=now)
    return {**result, **authenticate_bytes(raw, expected_digest=expected_digest,
            producer_repository=producer_repository, producer_revision=producer_revision,
            workflow=workflow)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('artifact', type=Path)
    parser.add_argument('--sha256', required=True)
    parser.add_argument('--producer-repository', required=True)
    parser.add_argument('--producer-revision', required=True)
    parser.add_argument('--workflow', required=True)
    args = parser.parse_args(argv)
    try:
        with args.artifact.open('rb') as stream:
            raw = stream.read(MAX_BYTES + 1)
        result = authenticate_bytes(raw, expected_digest=args.sha256,
                                    producer_repository=args.producer_repository,
                                    producer_revision=args.producer_revision, workflow=args.workflow)
    except (OSError, AttestationError) as error:
        print(json.dumps({'reason': str(error) if isinstance(error, AttestationError) else 'artifact_unavailable',
                          'producer_attestation_verified': False, 'snapshot_verified': False,
                          'write_authorized': False}))
        return 2
    print(json.dumps(result))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
