#!/usr/bin/env python3
"""Prepare source-pinned assets online for a later offline image build.

Preparation records provenance and input hashes. It does not qualify an image,
register a runner, or approve a newly resolved dependency candidate.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
ERROR = "Offline vendor preparation failed"
STAGES = ("binaries", "python", "promptfoo", "model")
HASH = re.compile(r"[0-9a-f]{64}\Z")
PIN = re.compile(r"([A-Za-z0-9][A-Za-z0-9_.-]*)==([A-Za-z0-9][A-Za-z0-9.+!-]*)\Z")
ALLOWED_HOSTS = {"github.com", "files.pythonhosted.org", "download-r2.pytorch.org"}
POLICY_INPUTS = {
    "privacy/requirements.lock", "privacy/build-requirements.lock",
    "scripts/build_privacy_wheels.py", "scripts/install_gitleaks.py",
    "security/offline-ai/provision/requirements.extra.lock",
    "security/offline-ai/provision/promptfoo/package.json",
    "security/offline-ai/provision/promptfoo/package-lock.json",
}


class PreparationError(RuntimeError):
    """Only the fixed CLI error label is published."""


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise PreparationError("duplicate-json-key")
        result[key] = value
    return result


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique_object)


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def read_lock(path):
    """Accept only exact named versions and SHA256 hashes."""
    pins = {}
    text = path.read_text(encoding="utf-8").replace("\\\n", " ")
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        match = PIN.fullmatch(parts[0])
        if match is None or len(parts) < 2:
            raise PreparationError("python-lock")
        name = re.sub(r"[-_.]+", "-", match[1]).lower()
        hashes = []
        for item in parts[1:]:
            if not item.startswith("--hash=sha256:") or not HASH.fullmatch(item[14:]):
                raise PreparationError("python-lock")
            hashes.append(item[14:])
        if name in pins:
            raise PreparationError("python-lock")
        pins[name] = (match[2], set(hashes))
    if not pins:
        raise PreparationError("python-lock")
    return pins


def merge_locks(*paths):
    merged = {}
    for path in paths:
        for name, (version, hashes) in read_lock(path).items():
            if name in merged and merged[name][0] != version:
                raise PreparationError("python-lock-conflict")
            merged.setdefault(name, (version, set()))[1].update(hashes)
    return merged


def write_lock(path, pins):
    lines = ["# Exact Linux x64 Python 3.15.1 dependency hashes.\n"]
    for name, (version, hashes) in sorted(pins.items()):
        lines.append(f"{name}=={version} " + " ".join(
            "--hash=sha256:" + value for value in sorted(hashes)) + "\n")
    path.write_text("".join(lines), encoding="utf-8")


def validate_npm_lock(package_path, lock_path, expected_integrity):
    package, lock = read_json(package_path), read_json(lock_path)
    if (package.get("dependencies") != {"promptfoo": "0.125.1"}
            or package.get("private") is not True or lock.get("lockfileVersion") != 3
            or not isinstance(lock.get("packages"), dict)):
        raise PreparationError("npm-lock")
    packages = lock["packages"]
    if packages.get("", {}).get("dependencies") != package["dependencies"]:
        raise PreparationError("npm-lock")
    for name, entry in packages.items():
        if not name:
            continue
        url = urllib.parse.urlsplit(entry.get("resolved", ""))
        version = entry.get("version", "")
        integrity = entry.get("integrity", "")
        if (not name.startswith("node_modules/") or ".." in Path(name).parts
                or url.scheme != "https" or url.hostname != "registry.npmjs.org"
                or url.username or url.password or url.query or url.fragment
                or not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+(?:[-+][A-Za-z0-9.-]+)?", version)
                or not integrity.startswith("sha512-")):
            raise PreparationError("npm-lock")
        try:
            value = base64.b64decode(integrity[7:], validate=True)
        except ValueError:
            raise PreparationError("npm-lock") from None
        if len(value) != 64:
            raise PreparationError("npm-lock")
    promptfoo = packages.get("node_modules/promptfoo", {})
    if promptfoo.get("version") != "0.125.1" or promptfoo.get("integrity") != expected_integrity:
        raise PreparationError("npm-source")


def load_catalog():
    catalog = read_json(HERE / "sources.json")
    if (catalog.get("schema_version") != 1 or catalog.get("target") != {
            "os": "linux", "architecture": "x86_64", "python": "3.15.1"}):
        raise PreparationError("source-catalog")
    # Only a separate reviewed commit may promote generated candidate locks.
    if catalog.get("lock_status") != "reviewed":
        raise PreparationError("lock-readiness")
    if set(catalog.get("downloads", {})) != {"gitleaks", "opengrep", "torch"}:
        raise PreparationError("source-catalog")
    for source in catalog["downloads"].values():
        url = urllib.parse.urlsplit(source.get("url", ""))
        if (url.scheme != "https" or url.hostname not in ALLOWED_HOSTS
                or url.username or url.password or url.query or url.fragment
                or not HASH.fullmatch(source.get("sha256", ""))
                or type(source.get("maximum_bytes")) is not int
                or not 0 < source["maximum_bytes"] <= 1024 * 1024 * 1024
                or not source.get("version") or not source.get("provenance_url")):
            raise PreparationError("source-catalog")
    if set(catalog.get("policy_inputs", {})) != POLICY_INPUTS:
        raise PreparationError("policy-input")
    for relative, expected in catalog["policy_inputs"].items():
        path = ROOT / relative
        if (not path.resolve().is_relative_to(ROOT) or not HASH.fullmatch(expected)
                or digest(path) != expected):
            raise PreparationError("policy-input")
    pins = merge_locks(ROOT / "privacy/requirements.lock", HERE / "requirements.extra.lock")
    for name, version in {"gliner": "0.2.30", "pytest": "9.2.0", "protobuf": "7.36.2"}.items():
        if pins.get(name, (None,))[0] != version:
            raise PreparationError("python-root-pin")
    if set(catalog.get("python_roots", {})) != {"gliner", "pytest"}:
        raise PreparationError("python-root-source")
    for name, source in catalog["python_roots"].items():
        if (pins[name][0] != source.get("version")
                or source.get("sha256") not in pins[name][1]):
            raise PreparationError("python-root-source")
    validate_npm_lock(HERE / "promptfoo/package.json", HERE / "promptfoo/package-lock.json",
                      catalog["promptfoo"]["integrity"])
    return catalog


def download(source, destination):
    """Hash a bounded streamed download before publishing it for a consumer."""
    if destination.exists() or destination.is_symlink():
        raise PreparationError("download-destination")
    request = urllib.request.Request(source["url"],
                                     headers={"User-Agent": "repository-standards-offline-preparation"})
    checksum, total = hashlib.sha256(), 0
    try:
        with destination.open("xb") as target, urllib.request.urlopen(request, timeout=90) as response:
            if urllib.parse.urlsplit(response.url).scheme != "https":
                raise PreparationError("download-transport")
            while chunk := response.read(1024 * 1024):
                total += len(chunk)
                if total > source["maximum_bytes"]:
                    raise PreparationError("download-size")
                checksum.update(chunk)
                target.write(chunk)
        if checksum.hexdigest() != source["sha256"]:
            raise PreparationError("download-hash")
        if source.get("size_bytes") is not None and total != source["size_bytes"]:
            raise PreparationError("download-size")
        destination.chmod(0o644)
    except BaseException:
        destination.unlink(missing_ok=True)
        raise


def run(command, *, cwd=None, timeout=1800):
    environment = os.environ.copy()
    environment["SOURCE_DATE_EPOCH"] = "315532800"
    result = subprocess.run(command, cwd=cwd, stdin=subprocess.DEVNULL,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                            check=False, timeout=timeout, env=environment)
    if result.returncode:
        raise PreparationError("preparation-command")


def binaries(vendor, work, catalog):
    (vendor / "bin").mkdir(mode=0o755)
    archive = work / "gitleaks.tar.gz"
    download(catalog["downloads"]["gitleaks"], archive)
    spec = importlib.util.spec_from_file_location(
        "pinned_gitleaks_installer", ROOT / "scripts/install_gitleaks.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    payload = module.extract_verified(archive.read_bytes(), "linux_x64.tar.gz",
                                      catalog["downloads"]["gitleaks"]["sha256"])
    (vendor / "bin/gitleaks").write_bytes(payload)
    download(catalog["downloads"]["opengrep"], vendor / "bin/opengrep")
    for path in (vendor / "bin").iterdir():
        path.chmod(0o755)


def python_wheels(vendor, work, catalog):
    wheels, builder = vendor / "python-wheels", work / "builder"
    wheels.mkdir(mode=0o755)
    run(["uv", "venv", "--python", sys.executable, str(builder)])
    python = str(builder / "bin/python")
    run(["uv", "pip", "install", "--python", python, "--require-hashes", "--only-binary=:all:",
         "--default-index", "https://pypi.org/simple", "-r", str(ROOT / "privacy/build-requirements.lock")])
    run([python, "-I", str(ROOT / "scripts/build_privacy_wheels.py"), "--destination", str(wheels)])
    expected = {"presidio_analyzer": "2.2.366+python315.1",
                "presidio_anonymizer": "2.2.366+python315.1", "pyyaml": "6.0.3"}
    pins = merge_locks(ROOT / "privacy/requirements.lock", HERE / "requirements.extra.lock")
    for name, source in catalog["python_roots"].items():
        pins[name] = (source["version"], {source["sha256"]})
    built = sorted(wheels.glob("*.whl"))
    if len(built) != len(expected):
        raise PreparationError("built-wheel-inventory")
    for name, version in expected.items():
        matches = [p for p in built if p.name.lower().startswith(f"{name}-{version}-")]
        if len(matches) != 1:
            raise PreparationError("built-wheel-inventory")
        pins[name.replace("_", "-")] = (version, {digest(matches[0])})
    torch = catalog["downloads"]["torch"]
    torch_name = urllib.parse.unquote(Path(urllib.parse.urlsplit(torch["url"]).path).name)
    download(torch, wheels / torch_name)
    pins["torch"] = ("2.15.0+cpu", {torch["sha256"]})
    lock = vendor / "requirements.lock"
    write_lock(lock, pins)
    run([sys.executable, "-I", "-m", "pip", "download", "--no-cache-dir",
         "--disable-pip-version-check", "--only-binary=:all:", "--no-deps", "--require-hashes",
         "--index-url", "https://pypi.org/simple", "--find-links", str(wheels),
         "--dest", str(wheels), "-r", str(lock)])
    runtime = work / "runtime"
    run(["uv", "venv", "--python", sys.executable, str(runtime)])
    runtime_python = str(runtime / "bin/python")
    run(["uv", "pip", "install", "--python", runtime_python, "--no-index", "--find-links", str(wheels),
         "--require-hashes", "--only-binary=:all:", "-r", str(lock)])
    run(["uv", "pip", "check", "--python", runtime_python])
    return runtime_python


def promptfoo(vendor):
    target = vendor / "promptfoo"
    target.mkdir(mode=0o755)
    for name in ("package.json", "package-lock.json"):
        shutil.copyfile(HERE / "promptfoo" / name, target / name)
    run(["npm", "ci", "--ignore-scripts", "--omit=dev", "--no-audit", "--no-fund",
         "--registry=https://registry.npmjs.org"], cwd=target)


def inventory(vendor):
    """Inventory only image input trees, without following links."""
    mappings = {"bin/gitleaks": "/usr/local/bin/gitleaks",
                "bin/opengrep": "/usr/local/bin/opengrep",
                "requirements.lock": "/opt/offline-ai/requirements.lock",
                "python-wheels": "/opt/offline-ai/wheels",
                "promptfoo": "/opt/promptfoo", "models/gliner-pii": "/opt/models/gliner-pii"}
    files, links = [], []
    for relative, image_path in mappings.items():
        pending = [(vendor / relative, image_path)]
        while pending:
            path, mapped = pending.pop()
            info = path.lstat()
            if stat.S_ISLNK(info.st_mode):
                if relative != "promptfoo":
                    raise PreparationError("asset-link")
                links.append({"path": mapped, "target": os.readlink(path)})
            elif stat.S_ISDIR(info.st_mode):
                path.chmod(0o755)
                pending.extend((child, mapped + "/" + child.name) for child in path.iterdir())
            elif stat.S_ISREG(info.st_mode) and info.st_nlink == 1:
                path.chmod(0o755 if info.st_mode & 0o111 else 0o644)
                files.append({"path": mapped, "sha256": digest(path)})
            else:
                raise PreparationError("asset-type")
    return {"schema_version": 2, "files": sorted(files, key=lambda x: x["path"]),
            "symlinks": sorted(links, key=lambda x: x["path"])}


def finalize(vendor, receipt, catalog):
    if (receipt.get("sources_catalog_sha256") != digest(HERE / "sources.json")
            or receipt.get("stages") != {stage: "passed" for stage in STAGES}
            or not HASH.fullmatch(receipt.get("model_provenance_sha256", ""))):
        raise PreparationError("incomplete-provenance")
    if load_catalog() != catalog:
        raise PreparationError("changed-provenance")
    manifest = vendor / "manifest.json"
    with manifest.open("x", encoding="utf-8") as stream:
        json.dump(inventory(vendor), stream, indent=2, sort_keys=True)
        stream.write("\n")
    sys.path.insert(0, str(ROOT / "security/offline-ai"))
    from security.verify_vendor import verify_vendor
    verify_vendor(vendor)
    receipt["manifest_sha256"] = digest(manifest)


def prepare(destination, receipt_path):
    if (sys.version_info[:3] != (3, 15, 1) or platform.system() != "Linux"
            or platform.machine() != "x86_64"):
        raise PreparationError("runtime")
    for path in (destination, receipt_path):
        if path.exists() or path.is_symlink() or not path.parent.is_dir():
            raise PreparationError("destination")
    catalog = load_catalog()
    receipt = {"schema_version": 1, "kind": "offline-vendor-preparation", "status": "failed",
               "sources_catalog_sha256": digest(HERE / "sources.json"),
               "policy_inputs": catalog["policy_inputs"], "upstream_sources": catalog["downloads"],
               "stages": {stage: "not-run" for stage in STAGES}, "image_qualified": False,
               "runner_registered": False}
    destination.mkdir(mode=0o755)
    current = "binaries"
    try:
        with tempfile.TemporaryDirectory(prefix="offline-vendor-build-") as temporary:
            work = Path(temporary)
            binaries(destination, work, catalog)
            receipt["stages"][current] = "passed"
            current = "python"
            runtime = python_wheels(destination, work, catalog)
            receipt["stages"][current] = "passed"
            current = "promptfoo"
            promptfoo(destination)
            receipt["stages"][current] = "passed"
            current = "model"
            model_receipt = receipt_path.with_name(receipt_path.stem + "-model.json")
            (destination / "models").mkdir(mode=0o755)
            run([runtime, "-I", str(HERE / "prepare_model.py"), "--destination",
                 str(destination / "models/gliner-pii"), "--receipt", str(model_receipt)])
            receipt["model_provenance_sha256"] = digest(model_receipt)
            receipt["stages"][current] = "passed"
            current = "manifest"
            finalize(destination, receipt, catalog)
            receipt["status"] = "prepared"
    except BaseException:
        receipt["failed_stage"] = current
        if current in STAGES:
            receipt["stages"][current] = "failed"
        raise
    finally:
        with receipt_path.open("x", encoding="utf-8") as stream:
            os.fchmod(stream.fileno(), 0o600)
            json.dump(receipt, stream, indent=2, sort_keys=True)
            stream.write("\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destination", required=True, type=Path)
    parser.add_argument("--receipt", required=True, type=Path)
    args = parser.parse_args()
    try:
        prepare(args.destination.absolute(), args.receipt.absolute())
    except (Exception, KeyboardInterrupt):
        print(ERROR, file=sys.stderr)
        return 2
    print("Offline vendor preparation passed; qualification still required")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
