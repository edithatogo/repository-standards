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
    "privacy/licenses/presidio-MIT.txt",
    "scripts/build_privacy_wheels.py", "scripts/install_gitleaks.py",
    "security/offline-ai/provision/requirements.extra.lock",
    "security/offline-ai/provision/promptfoo/package.json",
    "security/offline-ai/provision/promptfoo/package-lock.json",
    "security/offline-ai/provision/dependency-review.json",
}
NATIVE_SMOKE = """import assert from 'node:assert/strict';
import {createClient} from '@libsql/client/node';
import {transformSync} from 'esbuild';
const db = createClient({url: 'file::memory:'});
try {
  await db.execute('CREATE TABLE native_smoke (value INTEGER NOT NULL)');
  await db.execute({sql: 'INSERT INTO native_smoke VALUES (?)', args: [42]});
  const result = await db.execute('SELECT value FROM native_smoke');
  assert.equal(result.rows[0].value, 42);
} finally { db.close(); }
assert.match(transformSync('const value: number = 42;', {loader: 'ts'}).code,
             /value = 42/);
"""


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
    lines = ["# Exact Linux x64 Python 3.15.2 dependency hashes.\n"]
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
            "os": "linux", "architecture": "x86_64", "python": "3.15.2"}):
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
    review = read_json(HERE / "dependency-review.json")
    if (review.get("schema_version") != 1
            or review.get("status") != "reviewed-for-preparation"):
        raise PreparationError("dependency-review")
    for relative in ("requirements.extra.lock", "promptfoo/package.json",
                     "promptfoo/package-lock.json"):
        key = "security/offline-ai/provision/" + relative
        if review.get("locked_inputs", {}).get(key, {}).get("sha256") != catalog["policy_inputs"][key]:
            raise PreparationError("dependency-review")
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


def stage_gitleaks_candidate(binary, target, payloads, receipt, lock):
    """Stage only the exact frozen, unreviewed binary in a local evidence image."""
    names = {"go.mod", "go.sum", "modules.json", "module-closure.json", "gitleaks-LICENSE.txt"}
    expected = lock.get("metadata_sha256") if isinstance(lock, dict) else None
    build = receipt.get("build") if isinstance(receipt, dict) else None
    source = receipt.get("source") if isinstance(receipt, dict) else None
    binary_record = lock.get("binary") if isinstance(lock, dict) else None
    if (lock.get("schema_version") != 1 or lock.get("kind") != "unreviewed-gitleaks-image-candidate"
            or lock.get("reviewed") is not False or not isinstance(expected, dict)
            or set(expected) != names or set(payloads) != names
            or any(not isinstance(value, bytes) or hashlib.sha256(value).hexdigest() != expected[name]
                   for name, value in payloads.items())
            or not isinstance(source, dict) or source.get("commit") != lock.get("source_commit")
            or receipt.get("catalog_sha256") != lock.get("catalog_sha256")
            or receipt.get("module_closure_verified") is not True
            or receipt.get("fixture") != {"status": "passed", "kind": "existing-clean-and-canary-git"}
            or receipt.get("report_permissions") != {"status": "passed", "mode": "0600",
                                                      "paths": ["new", "existing"]}
            or receipt.get("status") != "candidate_complete" or receipt.get("last_stage") != "complete"
            or receipt.get("reviewed") is not False or receipt.get("image_qualified") is not False
            or not isinstance(binary_record, dict) or not isinstance(build, dict)
            or build.get("binary_sha256") != binary_record.get("sha256")):
        raise PreparationError("gitleaks-candidate-identity")
    info = binary.lstat()
    if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1
            or type(binary_record.get("size_bytes")) is not int
            or info.st_size != binary_record["size_bytes"]
            or not HASH.fullmatch(binary_record.get("sha256", ""))
            or digest(binary) != binary_record["sha256"]
            or target.name != "gitleaks" or target.parent.name != "bin"
            or target.parent.is_symlink() or not target.parent.is_dir()
            or target.exists() or target.is_symlink()):
        raise PreparationError("gitleaks-candidate-binary")
    created = False
    try:
        with binary.open("rb") as source_stream, target.open("xb") as output:
            created = True
            shutil.copyfileobj(source_stream, output)
        target.chmod(0o755)
        if target.stat().st_size != binary_record["size_bytes"] or digest(target) != binary_record["sha256"]:
            raise PreparationError("gitleaks-candidate-copy")
    except BaseException:
        if created:
            target.unlink(missing_ok=True)
        raise


def load_gitleaks_image_candidate():
    """Load the frozen source-build identity without treating it as reviewed."""
    path = HERE / "gitleaks-image-candidate.json"
    if path.is_symlink() or not path.is_file():
        raise PreparationError("gitleaks-candidate-lock")
    lock = read_json(path)
    names = {"go.mod", "go.sum", "modules.json", "module-closure.json", "gitleaks-LICENSE.txt"}
    binary = lock.get("binary")
    metadata = lock.get("metadata_sha256")
    artifact = lock.get("dependency_artifact")
    if (lock.get("schema_version") != 1 or lock.get("kind") != "unreviewed-gitleaks-image-candidate"
            or lock.get("reviewed") is not False or not re.fullmatch(r"[0-9a-f]{40}", lock.get("source_commit", ""))
            or not HASH.fullmatch(lock.get("catalog_sha256", ""))
            or lock["catalog_sha256"] != digest(HERE / "gitleaks-build-sources.json")
            or not isinstance(binary, dict) or not HASH.fullmatch(binary.get("sha256", ""))
            or type(binary.get("size_bytes")) is not int or not 0 < binary["size_bytes"] <= 128 * 1024 * 1024
            or not isinstance(metadata, dict) or set(metadata) != names
            or any(not isinstance(value, str) or not HASH.fullmatch(value) for value in metadata.values())
            or not isinstance(artifact, dict) or not HASH.fullmatch(artifact.get("archive_sha256", ""))
            or not re.fullmatch(r"[0-9a-f]{40}", artifact.get("policy_commit", ""))
            or type(artifact.get("id")) is not int or type(artifact.get("run_id")) is not int):
        raise PreparationError("gitleaks-candidate-lock")
    return lock


def binaries(vendor, work, catalog, *, candidate_lock=None):
    (vendor / "bin").mkdir(mode=0o755)
    if candidate_lock is None:
        archive = work / "gitleaks.tar.gz"
        download(catalog["downloads"]["gitleaks"], archive)
        spec = importlib.util.spec_from_file_location(
            "pinned_gitleaks_installer", ROOT / "scripts/install_gitleaks.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        payload = module.extract_verified(archive.read_bytes(), "linux_x64.tar.gz",
                                          catalog["downloads"]["gitleaks"]["sha256"])
        (vendor / "bin/gitleaks").write_bytes(payload)
    else:
        spec = importlib.util.spec_from_file_location("gitleaks_candidate", HERE / "gitleaks_candidate.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        target = vendor / "bin/gitleaks"
        try:
            module.candidate(work / "gitleaks-evidence", local_binary=lambda binary, payloads, receipt:
                             stage_gitleaks_candidate(binary, target, payloads, receipt, candidate_lock))
            if not target.is_file() or target.is_symlink():
                raise PreparationError("gitleaks-candidate-missing")
        except BaseException:
            target.unlink(missing_ok=True)
            raise
    download(catalog["downloads"]["opengrep"], vendor / "bin/opengrep")
    for path in (vendor / "bin").iterdir():
        path.chmod(0o755)


def stage_privacy_wheels(built_directory, wheels):
    """Copy only the exact built wheels; uv output metadata stays in scratch."""
    if not stat.S_ISDIR(built_directory.lstat().st_mode):
        raise PreparationError("built-wheel-inventory")
    expected = {"presidio_analyzer": "2.2.366+python315.2",
                "presidio_anonymizer": "2.2.366+python315.2", "pyyaml": "6.0.3"}
    built = []
    for path in sorted(built_directory.iterdir()):
        info = path.lstat()
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise PreparationError("built-wheel-inventory")
        # uv 0.13.8 prepare_output_directory writes this exact build-only file.
        if path.name == ".gitignore" and path.read_bytes() == b"*":
            continue
        if path.suffix != ".whl":
            raise PreparationError("built-wheel-inventory")
        built.append(path)
    if len(built) != len(expected):
        raise PreparationError("built-wheel-inventory")
    selected = {}
    for name, version in expected.items():
        matches = [path for path in built if path.name.lower().startswith(f"{name}-{version}-")]
        if len(matches) != 1:
            raise PreparationError("built-wheel-inventory")
        selected[name.replace("_", "-")] = (version, matches[0])
    pins = {}
    for name, (version, source) in selected.items():
        destination = wheels / source.name
        shutil.copyfile(source, destination)
        pins[name] = (version, {digest(destination)})
    return pins


def python_wheels(vendor, work, catalog):
    wheels, builder = vendor / "python-wheels", work / "builder"
    wheels.mkdir(mode=0o755)
    run(["uv", "venv", "--python", sys.executable, str(builder)])
    python = str(builder / "bin/python")
    run(["uv", "pip", "install", "--python", python, "--require-hashes", "--only-binary=:all:",
         "--default-index", "https://pypi.org/simple", "-r", str(ROOT / "privacy/build-requirements.lock")])
    built_directory = work / "built-wheels"
    run([python, "-I", str(ROOT / "scripts/build_privacy_wheels.py"),
         "--destination", str(built_directory)])
    pins = merge_locks(ROOT / "privacy/requirements.lock", HERE / "requirements.extra.lock")
    for name, source in catalog["python_roots"].items():
        pins[name] = (source["version"], {source["sha256"]})
    pins.update(stage_privacy_wheels(built_directory, wheels))
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
    run(["npm", "ci", "--ignore-scripts", "--omit=dev", "--include=optional", "--no-audit", "--no-fund",
         "--registry=https://registry.npmjs.org"], cwd=target)
    # Both native artifacts are published, SRI-bound optional packages in the lock.
    # Exercise the local SQLite binding and esbuild binary without install scripts.
    run(["node", "--input-type=module", "-e", NATIVE_SMOKE], cwd=target, timeout=60)


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


def prepare(destination, receipt_path, *, gitleaks_candidate_evidence_only=False):
    if (sys.version_info[:3] != (3, 15, 2) or platform.system() != "Linux"
            or platform.machine() != "x86_64"):
        raise PreparationError("runtime")
    for path in (destination, receipt_path):
        if path.exists() or path.is_symlink() or not path.parent.is_dir():
            raise PreparationError("destination")
    catalog = load_catalog()
    candidate_lock = load_gitleaks_image_candidate() if gitleaks_candidate_evidence_only else None
    receipt = {"schema_version": 1, "kind": "offline-vendor-preparation", "status": "failed",
               "sources_catalog_sha256": digest(HERE / "sources.json"),
               "policy_inputs": catalog["policy_inputs"], "upstream_sources": dict(catalog["downloads"]),
               "stages": {stage: "not-run" for stage in STAGES}, "image_qualified": False,
               "runner_registered": False}
    if candidate_lock is not None:
        receipt["upstream_sources"]["gitleaks"] = {
            "kind": "unreviewed-source-build-evidence-only",
            "source_commit": candidate_lock["source_commit"],
            "binary_sha256": candidate_lock["binary"]["sha256"],
            "candidate_lock_sha256": digest(HERE / "gitleaks-image-candidate.json"),
            "dependency_artifact": candidate_lock["dependency_artifact"],
        }
    destination.mkdir(mode=0o755)
    current = "binaries"
    try:
        with tempfile.TemporaryDirectory(prefix="offline-vendor-build-") as temporary:
            work = Path(temporary)
            binaries(destination, work, catalog, candidate_lock=candidate_lock)
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
    parser.add_argument("--gitleaks-candidate-evidence-only", action="store_true")
    args = parser.parse_args()
    try:
        prepare(args.destination.absolute(), args.receipt.absolute(),
                gitleaks_candidate_evidence_only=args.gitleaks_candidate_evidence_only)
    except (Exception, KeyboardInterrupt):
        print(ERROR, file=sys.stderr)
        return 2
    print("Offline vendor preparation passed; qualification still required")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
