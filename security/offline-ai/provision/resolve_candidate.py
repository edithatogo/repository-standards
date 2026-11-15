#!/usr/bin/env python3
"""Resolve public dependency metadata into an explicitly unreviewed candidate.

The candidate is never consumed directly by prepare_vendor.py. Its hashes and
versions must be reviewed and committed with a separate catalog update first.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUTPUTS = ("requirements.extra.lock", "promptfoo/package.json", "promptfoo/package-lock.json")
MAX_FILE_BYTES = 1024 * 1024
CHUNK_CHARACTERS = 2048


def module():
    spec = importlib.util.spec_from_file_location("vendor_preparation", HERE / "prepare_vendor.py")
    imported = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(imported)
    return imported


def run(command, *, cwd=None):
    # Only public registry metadata and public lockfile inputs are involved.
    subprocess.run(command, cwd=cwd, check=True, timeout=600, stdin=subprocess.DEVNULL)


def candidate(destination):
    if sys.version_info[:3] != (3, 15, 1) or destination.exists() or destination.is_symlink():
        raise ValueError("candidate-preflight")
    destination.mkdir(parents=True)
    prep = module()
    complete = destination / "resolved.lock"
    run(["uv", "pip", "compile", str(HERE / "requirements.candidate.in"),
         "--constraint", str(ROOT / "privacy/requirements.lock"),
         "--excludes", str(HERE / "requirements.exclude.in"),
         "--python", sys.executable, "--python-platform", "x86_64-manylinux_2_28",
         "--only-binary=:all:", "--generate-hashes", "--no-header", "--no-annotate",
         "--default-index", "https://pypi.org/simple", "--output-file", str(complete)])
    existing, resolved = prep.read_lock(ROOT / "privacy/requirements.lock"), prep.read_lock(complete)
    for name in existing.keys() & resolved.keys():
        if existing[name][0] != resolved[name][0]:
            raise ValueError("candidate-constraint-conflict")
    prep.write_lock(destination / "requirements.extra.lock",
                    {name: value for name, value in resolved.items() if name not in existing})
    complete.unlink()
    npm = destination / "promptfoo"
    npm.mkdir()
    shutil.copyfile(HERE / "promptfoo/package.json", npm / "package.json")
    run(["npm", "install", "--package-lock-only", "--ignore-scripts", "--no-audit", "--no-fund",
         "--omit=dev", "--registry=https://registry.npmjs.org"], cwd=npm)
    sources = prep.read_json(HERE / "sources.json")
    prep.validate_npm_lock(npm / "package.json", npm / "package-lock.json",
                           sources["promptfoo"]["integrity"])
    records = []
    for relative in OUTPUTS:
        payload = (destination / relative).read_bytes()
        if len(payload) > MAX_FILE_BYTES:
            raise ValueError("candidate-size")
        records.append({"path": relative, "size_bytes": len(payload),
                        "sha256": hashlib.sha256(payload).hexdigest(),
                        "git_blob_sha": hashlib.sha1(
                            f"blob {len(payload)}\0".encode("ascii") + payload,
                            usedforsecurity=False).hexdigest()})
    receipt = {"schema_version": 1, "kind": "unreviewed-upstream-lock-candidate",
               "qualified": False, "reviewed": False, "files": records,
               "python_version": ".".join(str(v) for v in sys.version_info[:3])}
    (destination / "candidate-receipt.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return receipt


def emit_public_locks(destination, receipt):
    """Emit only the three fixed public lock paths, with verifiable chunk order."""
    if tuple(item["path"] for item in receipt["files"]) != OUTPUTS:
        raise ValueError("candidate-path")
    for record in receipt["files"]:
        payload = (destination / record["path"]).read_bytes()
        if len(payload) > MAX_FILE_BYTES or hashlib.sha256(payload).hexdigest() != record["sha256"]:
            raise ValueError("candidate-content")
        text = payload.decode("utf-8")
        total = (len(text) + CHUNK_CHARACTERS - 1) // CHUNK_CHARACTERS
        for index in range(total):
            print("OFFLINE_LOCK_CHUNK " + json.dumps(
                {"path": record["path"], "index": index, "total": total,
                 "data": text[index * CHUNK_CHARACTERS:(index + 1) * CHUNK_CHARACTERS]},
                ensure_ascii=True, separators=(",", ":")))
    print("OFFLINE_LOCK_RECEIPT " + json.dumps(receipt, sort_keys=True, separators=(",", ":")))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destination", required=True, type=Path)
    args = parser.parse_args()
    destination = args.destination.absolute()
    try:
        receipt = candidate(destination)
        emit_public_locks(destination, receipt)
    except (Exception, KeyboardInterrupt):
        print("Offline dependency candidate failed", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
