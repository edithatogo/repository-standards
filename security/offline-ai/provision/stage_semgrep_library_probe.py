"""Stage exact signed-package payloads for the isolated Semgrep trial."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import urllib.request

BASE = "https://repo.almalinux.org/almalinux/9/BaseOS/x86_64/os/Packages/"


def require(condition):
    if not condition:
        raise ValueError("Semgrep library probe input identity")


def verify(payload, entry):
    require(len(payload) == entry["size_bytes"])
    require(hashlib.sha256(payload).hexdigest() == entry["sha256"])


def stage(libraries, bsdtar):
    committed = Path(__file__).with_name("semgrep-library-probe.json")
    lock = json.loads(committed.read_bytes())
    require(lock["schema_version"] == 1 and len(lock["packages"]) == 6)
    verified = {}
    with tempfile.TemporaryDirectory(prefix="semgrep-library-probe-") as directory:
        archive = Path(directory) / "signed.rpm"
        for package in lock["packages"]:
            url = package["url"]
            require(url.startswith(BASE) and 0 < package["size_bytes"] < 16 * 1024 * 1024)
            with urllib.request.urlopen(url, timeout=40) as response:
                require(response.geturl().startswith(BASE))
                payload = response.read(package["size_bytes"] + 1)
            verify(payload, package)
            archive.write_bytes(payload)
            for item in package["libraries"]:
                name = item["name"]
                target = libraries / name
                require(Path(name).name == name and target.is_file() and not target.is_symlink())
                require(target not in verified)
                binary = subprocess.check_output(
                    [bsdtar, "-xOf", str(archive), item["path"]], timeout=30
                )
                verify(binary, item)
                require(binary.startswith(b"\x7fELF\x02\x01") and binary[18:20] == b"\x3e\0")
                verified[target] = binary
    require(len(verified) == 8)
    for target, binary in verified.items():
        target.write_bytes(binary)
    print(json.dumps({path.name: hashlib.sha256(data).hexdigest()
                      for path, data in sorted(verified.items())}, sort_keys=True))


if __name__ == "__main__":
    stage(Path(sys.argv[1]).resolve(strict=True), sys.argv[2])
