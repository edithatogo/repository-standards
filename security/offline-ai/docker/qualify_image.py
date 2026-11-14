#!/usr/bin/env python3
"""Qualify an already provisioned image; never pull assets or register a runner.

The receipt covers actual scanner/model execution in the restricted container.
It does not approve asset provenance, register a runner, or qualify real agents.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tarfile
import tempfile
import uuid


POLICY = Path(__file__).resolve().parents[3]
IMAGE_PATTERN = re.compile(r"localhost/offline-ai-security@sha256:[0-9a-f]{64}\Z")
OFFLINE_ENV = {
    "HOME": "/tmp", "PYTHONPATH": "/policy/security/offline-ai", "PYTHONSAFEPATH": "1",
    "SECURITY_ASSET_MANIFEST": "/opt/offline-ai/manifest.json",
    "GLINER_MODEL_DIR": "/opt/models/gliner-pii",
    "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1", "HF_DATASETS_OFFLINE": "1",
    "HF_HOME": "/opt/models", "XDG_CACHE_HOME": "/tmp/cache", "TMPDIR": "/tmp",
    "HF_HUB_DISABLE_TELEMETRY": "1", "PIP_NO_INDEX": "1", "npm_config_offline": "true",
    "PROMPTFOO_CONFIG_DIR": "/tmp/promptfoo", "PROMPTFOO_DISABLE_TELEMETRY": "1",
    "PROMPTFOO_DISABLE_UPDATE": "1", "PROMPTFOO_DISABLE_REMOTE_GENERATION": "true",
    "PROMPTFOO_DISABLE_REDTEAM_REMOTE_GENERATION": "true",
    "PROMPTFOO_DISABLE_SHARING": "1", "PROMPTFOO_SELF_HOSTED": "1",
    "PYTHONDONTWRITEBYTECODE": "1", "PYTEST_ADDOPTS": "-p no:cacheprovider",
}


class QualificationError(RuntimeError):
    """Only fixed control names may reach the operator's logs."""


def execute(command, label, *, capture=False, timeout=30, env=None):
    try:
        result = subprocess.run(
            command, stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE if capture else subprocess.DEVNULL,
            stderr=subprocess.DEVNULL, timeout=timeout, check=False, env=env,
        )
        if result.returncode:
            raise QualificationError(label)
        if capture:
            if len(result.stdout) > 65536:
                raise QualificationError(label)
            return result.stdout.decode("utf-8").strip()
    except (OSError, UnicodeError, subprocess.TimeoutExpired):
        raise QualificationError(label) from None
    return ""


def stages(manifest_sha256):
    return [
        ("runtime", ["python", "-I", "-c",
                     "import sys, shutil; assert sys.version_info[:3] == (3, 15, 1); "
                     "assert all(shutil.which(name) for name in "
                     "('gitleaks', 'opengrep', 'python', 'promptfoo', 'git', 'node'))"]),
        ("network-preflight", ["python", "-m", "security.verify_network"]),
        ("manifest-binding", ["python", "-I", "-c",
                              "import hashlib, pathlib, sys; "
                              "assert hashlib.sha256(pathlib.Path('/opt/offline-ai/manifest.json').read_bytes()).hexdigest() == sys.argv[1]",
                              manifest_sha256]),
        ("asset-preflight", ["python", "-m", "security.verify_assets"]),
        ("gitleaks-fixtures", ["python", "/policy/security/offline-ai/scripts/verify_gitleaks.py"]),
        ("sast-fixtures", ["python", "/policy/security/offline-ai/scripts/verify_sast_fixtures.py"]),
        ("dlp-model", ["python", "/policy/security/offline-ai/scripts/qualify_model.py"]),
        ("promptfoo-mock", ["promptfoo", "eval", "-c",
                            "/policy/security/offline-ai/promptfooconfig.yaml", "--no-cache", "--no-progress"]),
    ]


def preflight(args):
    if (not IMAGE_PATTERN.fullmatch(args.image)
            or not re.fullmatch(r"[0-9a-f]{40}", args.policy_sha)
            or not re.fullmatch(r"[0-9a-f]{64}", args.manifest_sha256)
            or not 1 <= args.stage_timeout <= 1800):
        raise QualificationError("input-preflight")
    if any(character in str(POLICY) for character in (",", "\n", "\r")):
        raise QualificationError("policy-path")
    receipt = Path(args.receipt).absolute()
    parent = receipt.parent.resolve(strict=True)
    if receipt.exists() or receipt.is_symlink() or parent.is_relative_to(POLICY):
        raise QualificationError("receipt-preflight")
    receipt = parent / receipt.name
    command = ["git", "--no-replace-objects", "-C", str(POLICY)]
    if execute(command + ["rev-parse", "--show-toplevel"], "policy-preflight", capture=True) != str(POLICY):
        raise QualificationError("policy-preflight")
    if execute(command + ["rev-parse", "HEAD"], "policy-preflight", capture=True) != args.policy_sha:
        raise QualificationError("policy-preflight")
    if execute(command + ["status", "--porcelain", "--untracked-files=all"], "policy-preflight", capture=True):
        raise QualificationError("policy-preflight")
    # A remote Docker daemon would bind its own filesystem, not the verified checkout.
    endpoint = os.environ.get("DOCKER_HOST") or execute(
        ["docker", "context", "inspect", "--format", "{{.Endpoints.docker.Host}}"],
        "docker-context", capture=True,
    )
    if not endpoint.startswith("unix:///") or any(c.isspace() for c in endpoint):
        raise QualificationError("docker-context")
    docker = ["docker", "--host=" + endpoint]
    environment = {key: value for key, value in os.environ.items()
                   if key not in ("DOCKER_HOST", "DOCKER_CONTEXT")}
    try:
        digests = json.loads(execute(
            docker + ["image", "inspect", args.image, "--format", "{{json .RepoDigests}}"],
            "image-preflight", capture=True, env=environment,
        ))
    except (TypeError, ValueError):
        raise QualificationError("image-preflight") from None
    if not isinstance(digests, list) or args.image not in digests:
        raise QualificationError("image-preflight")
    return receipt, docker, environment


@contextmanager
def policy_snapshot(commit):
    """Export committed files once; ignored files and later edits cannot enter."""
    with tempfile.TemporaryDirectory(prefix="offline-policy-") as temporary:
        snapshot = Path(temporary) / "policy"
        snapshot.mkdir(mode=0o755)
        try:
            with tempfile.TemporaryFile() as stream:
                result = subprocess.run(
                    ["git", "--no-replace-objects", "-C", str(POLICY),
                     "archive", "--format=tar", commit],
                    stdin=subprocess.DEVNULL, stdout=stream, stderr=subprocess.DEVNULL,
                    timeout=30, check=False,
                )
                if result.returncode:
                    raise QualificationError("policy-snapshot")
                stream.seek(0)
                with tarfile.open(fileobj=stream) as archive:
                    if any(member.issym() or member.islnk() for member in archive.getmembers()):
                        raise QualificationError("policy-snapshot")
                    archive.extractall(snapshot, filter="data")
        except (OSError, tarfile.TarError, subprocess.TimeoutExpired):
            raise QualificationError("policy-snapshot") from None
        yield snapshot


def container_command(docker, image, name, command, snapshot):
    result = docker + [
        "run", "--rm", "--pull=never", "--network=none", "--read-only", "--cap-drop=ALL",
        "--security-opt=no-new-privileges", "--pids-limit=256", "--memory=8g", "--cpus=4",
        "--user=65534:65534", "--name=" + name, "--entrypoint=" + command[0],
        "--tmpfs", "/tmp:rw,nosuid,size=2g,mode=1777",
        "--mount", f"type=bind,src={snapshot},dst=/policy,readonly",
        "--workdir", "/policy/security/offline-ai",
    ]
    for key, value in OFFLINE_ENV.items():
        result.extend(["-e", key + "=" + value])
    return result + [image, *command[1:]]


def write_receipt(path, receipt):
    # Publish a complete private file without overwriting an earlier qualification.
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                         prefix=".qualification-", delete=False) as stream:
            temporary = Path(stream.name)
            os.fchmod(stream.fileno(), 0o600)
            json.dump(receipt, stream, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def qualify(args):
    receipt_path, docker, environment = preflight(args)
    controls = stages(args.manifest_sha256)
    receipt = {
        "schema_version": 1, "kind": "offline-image-qualification", "status": "failed",
        "image": args.image, "policy_commit": args.policy_sha,
        "asset_manifest_sha256": args.manifest_sha256,
        "stages": [{"name": label, "status": "not-run"} for label, _ in controls],
        "cleanup_status": "not-needed",
        "application_adapters_qualified": False, "runner_registration_qualified": False,
    }
    with policy_snapshot(args.policy_sha) as snapshot:
        for index, (label, command) in enumerate(controls):
            name = "offline-qualification-" + uuid.uuid4().hex
            try:
                execute(container_command(docker, args.image, name, command, snapshot), label,
                        timeout=args.stage_timeout, env=environment)
            except (QualificationError, KeyboardInterrupt):
                receipt["stages"][index]["status"] = "failed"
                # Killing the Docker client on timeout need not stop its container.
                try:
                    execute(docker + ["rm", "--force", name], "container-cleanup", env=environment)
                    receipt["cleanup_status"] = "passed"
                except QualificationError:
                    receipt["cleanup_status"] = "failed"
                write_receipt(receipt_path, receipt)
                failure = label + ("; container-cleanup" if receipt["cleanup_status"] == "failed" else "")
                raise QualificationError(failure) from None
            receipt["stages"][index]["status"] = "passed"
            print("Image qualification control passed: " + label)
    receipt["status"] = "passed"
    write_receipt(receipt_path, receipt)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", required=True)
    parser.add_argument("--policy-sha", required=True)
    parser.add_argument("--manifest-sha256", required=True)
    parser.add_argument("--receipt", required=True)
    parser.add_argument("--stage-timeout", type=int, default=600)
    args = parser.parse_args(argv)
    try:
        qualify(args)
    except QualificationError as error:
        print("Image qualification failed: " + str(error), file=sys.stderr)
        return 2
    except (OSError, ValueError):
        print("Image qualification failed: local-io", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("Image qualification failed: interrupted", file=sys.stderr)
        return 130
    print("Image qualification passed; local receipt written")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
