"""Prepare and verify the pinned native Semgrep bundle for hosted SAST."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import urllib.request

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import probe_semgrep_rust as semgrep  # noqa: E402

LOCK = HERE / "hosted-sast-rpm-lock.json"
ALMA_BASE = "https://repo.almalinux.org/almalinux/9/BaseOS/x86_64/os/Packages/"


def load_lock() -> dict:
    lock = json.loads(LOCK.read_bytes())
    tool = lock["semgrep"]
    if (lock["schema_version"] != 1 or tool["version"] != semgrep.VERSION
            or tool["wheel_sha256"] != semgrep.WHEEL_SHA256
            or len(tool["assets"]) != semgrep.LIBRARY_COUNT + 1):
        raise ValueError("Hosted SAST lock identity")
    return lock


def verify_bundle(root: Path, lock: dict) -> None:
    library_dir = root / "libs"
    if (root.is_symlink() or library_dir.is_symlink()
            or {p.name for p in root.iterdir()} != {"libs", semgrep.CORE}):
        raise ValueError("Hosted SAST inventory")
    assets = lock["semgrep"]["assets"]
    libraries = {f"libs/{path.name}" for path in library_dir.iterdir()}
    if set(assets) != libraries | {semgrep.CORE}:
        raise ValueError("Hosted SAST inventory")
    for name, expected in assets.items():
        path = root / name
        info = path.lstat()
        if not stat.S_ISREG(info.st_mode) or info.st_size != expected["size_bytes"]:
            raise ValueError("Hosted SAST payload identity")
        with path.open("rb") as stream:
            if hashlib.file_digest(stream, "sha256").hexdigest() != expected["sha256"]:
                raise ValueError("Hosted SAST payload identity")


def verify_payload(payload: bytes, expected: dict) -> None:
    if (len(payload) != expected["size_bytes"]
            or hashlib.sha256(payload).hexdigest() != expected["sha256"]):
        raise ValueError("Hosted SAST package identity")


def prepare(destination: Path, bsdtar: str, lock: dict) -> None:
    semgrep.prepare(destination)
    replacements = set()
    with tempfile.TemporaryDirectory(prefix="hosted-sast-rpm-") as temporary:
        archive = Path(temporary) / "signed.rpm"
        for package in lock["packages"]:
            url = package["url"]
            if not url.startswith(ALMA_BASE) or not 0 < package["size_bytes"] < 16 * 1024 * 1024:
                raise ValueError("Hosted SAST package source")
            with urllib.request.urlopen(url, timeout=40) as response:
                if not response.geturl().startswith(ALMA_BASE):
                    raise ValueError("Hosted SAST package download origin")
                payload = response.read(package["size_bytes"] + 1)
            verify_payload(payload, package)
            archive.write_bytes(payload)
            for library in package["libraries"]:
                name = library["name"]
                target = destination / "libs" / name
                if Path(name).name != name or not target.is_file() or name in replacements:
                    raise ValueError("Hosted SAST replacement inventory")
                binary = subprocess.check_output(
                    [bsdtar, "-xOf", str(archive), library["path"]], timeout=30
                )
                verify_payload(binary, library)
                target.write_bytes(binary)
                replacements.add(name)
    if len(replacements) != 8:
        raise ValueError("Hosted SAST replacement inventory")
    verify_bundle(destination, lock)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: hosted_sast_assets.py NEW_BUNDLE BSDTAR", file=sys.stderr)
        raise SystemExit(2)
    try:
        lock = load_lock()
        prepare(Path(sys.argv[1]), sys.argv[2], lock)
        print(json.dumps(lock, sort_keys=True))
    except (OSError, ValueError, KeyError, subprocess.SubprocessError):
        print("Hosted SAST asset preparation failed", file=sys.stderr)
        raise SystemExit(2) from None
