#!/usr/bin/env python3
"""Install a checksum-verified upstream Gitleaks binary, without executing a shell."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import platform
import tarfile
import tempfile
import urllib.request
import zipfile
from pathlib import Path

VERSION = "8.30.1"
# GitHub release asset digests, verified 2026-11-10 against the upstream release API.
ASSETS = {
    ("Linux", "x86_64"): (
        "linux_x64.tar.gz",
        "551f6fc83ea457d62a0d98237cbad105af8d557003051f41f3e7ca7b3f2470eb",
    ),
    ("Linux", "aarch64"): (
        "linux_arm64.tar.gz",
        "e4a487ee7ccd7d3a7f7ec08657610aa3606637dab924210b3aee62570fb4b080",
    ),
    ("Darwin", "arm64"): (
        "darwin_arm64.tar.gz",
        "b40ab0ae55c505963e365f271a8d3846efbc170aa17f2607f13df610a9aeb6a5",
    ),
    ("Darwin", "x86_64"): (
        "darwin_x64.tar.gz",
        "dfe101a4db2255fc85120ac7f3d25e4342c3c20cf749f2c20a18081af1952709",
    ),
    ("Windows", "AMD64"): (
        "windows_x64.zip",
        "d29144deff3a68aa93ced33dddf84b7fdc26070add4aa0f4513094c8332afc4e",
    ),
    ("Windows", "ARM64"): (
        "windows_arm64.zip",
        "b95f5e4f5c425cedca7ee203d9afd29597e692c4924a12ed42f970537c72cc0f",
    ),
}


def extract_verified(payload: bytes, suffix: str, checksum: str) -> bytes:
    if hashlib.sha256(payload).hexdigest() != checksum:
        raise ValueError("release checksum mismatch")
    member = "gitleaks.exe" if suffix.endswith(".zip") else "gitleaks"
    if suffix.endswith(".zip"):
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            if archive.getinfo(member).file_size > 64 * 1024 * 1024:
                raise ValueError("binary too large")
            return archive.read(member)
    with tarfile.open(fileobj=io.BytesIO(payload), mode="r:gz") as archive:
        info = archive.getmember(member)
        if not info.isfile() or info.size > 64 * 1024 * 1024:
            raise ValueError("invalid binary archive member")
        stream = archive.extractfile(info)
        if stream is None:
            raise ValueError("missing binary")
        return stream.read()


def install(destination: Path) -> Path:
    suffix, checksum = ASSETS[(platform.system(), platform.machine())]
    url = f"https://github.com/gitleaks/gitleaks/releases/download/v{VERSION}/gitleaks_{VERSION}_{suffix}"
    request = urllib.request.Request(
        url, headers={"User-Agent": "repository-standards-privacy-guard"}
    )
    with urllib.request.urlopen(request, timeout=90) as response:
        payload = response.read(64 * 1024 * 1024 + 1)
    if len(payload) > 64 * 1024 * 1024:
        raise ValueError("release archive too large")
    binary = extract_verified(payload, suffix, checksum)
    destination.mkdir(parents=True, exist_ok=True)
    name = "gitleaks.exe" if suffix.endswith(".zip") else "gitleaks"
    target = destination / name
    with tempfile.NamedTemporaryFile(dir=destination, delete=False) as temporary:
        temporary.write(binary)
        temporary_path = Path(temporary.name)
    try:
        temporary_path.chmod(0o700)
        os.replace(temporary_path, target)
    finally:
        temporary_path.unlink(missing_ok=True)
    return target


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destination", type=Path, required=True)
    args = parser.parse_args()
    try:
        install(args.destination)
    except Exception:  # noqa: BLE001 - never print third-party exception data at the public CLI boundary
        print(json.dumps({"tool": "gitleaks", "status": "installation_error"}))
        return 2
    print(
        json.dumps({"tool": "gitleaks", "version": VERSION, "checksum_verified": True})
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
