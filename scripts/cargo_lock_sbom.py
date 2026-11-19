#!/usr/bin/env python3
"""Emit a resolved CycloneDX 1.6 inventory of every package in Cargo.lock.

This is a source-resolution inventory, including build/dev/optional/target
dependencies. It is not evidence that every component is linked into a binary,
nor an inventory of OS libraries, separately resolved bindings, or downloaded
build-script inputs. Cargo.lock is read without resolving or modifying it.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import tomllib
import uuid
from pathlib import Path
from urllib.parse import quote

CRATES_IO = "registry+https://github.com/rust-lang/crates.io-index"
VERSION = re.compile(r"(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?")
DEPENDENCY = re.compile(r"([A-Za-z0-9_-]+)(?: ([^ ()]+))?(?: \(([^)]+)\))?")


def identity(package: dict) -> tuple[str, str, str]:
    name, version = package.get("name"), package.get("version")
    source = package.get("source", "")
    if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", name):
        raise ValueError("invalid Cargo package name")
    if not isinstance(version, str) or not VERSION.fullmatch(version):
        raise ValueError(f"{name}: expected a resolved semantic version, got {version!r}")
    if not isinstance(source, str) or (source and not source.startswith(("registry+", "sparse+", "git+"))):
        raise ValueError(f"{name}: unsupported Cargo source")
    return name, version, source


def reference(key: tuple[str, str, str]) -> str:
    return "cargo-lock:" + hashlib.sha256("\0".join(key).encode()).hexdigest()


def generate(lock_bytes: bytes, name: str, source_sha: str) -> dict:
    if not name.strip():
        raise ValueError("inventory name must be nonempty")
    if not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", source_sha):
        raise ValueError("source-sha must be an exact lowercase Git commit hash")
    lock = tomllib.loads(lock_bytes.decode("utf-8"))
    if lock.get("version") not in (3, 4):
        raise ValueError("only Cargo.lock format 3 or 4 is supported")
    packages = lock.get("package")
    if not isinstance(packages, list) or not packages:
        raise ValueError("Cargo.lock has no packages")
    indexed: dict[tuple[str, str, str], dict] = {}
    for package in packages:
        key = identity(package)
        if key in indexed:
            raise ValueError(f"duplicate Cargo package identity: {key[0]} {key[1]}")
        indexed[key] = package
    if not any(key[2] for key in indexed):
        raise ValueError("Cargo.lock contains no third-party package sources")

    components, dependencies = [], []
    for key, package in sorted(indexed.items()):
        package_name, version, source = key
        component = {
            "type": "library", "bom-ref": reference(key),
            "name": package_name, "version": version,
            "properties": [
                {"name": "cargo:source", "value": source or "local-workspace-or-path"},
                {"name": "cargo:resolution", "value": "Cargo.lock"},
            ],
        }
        # No registry identity is asserted for path or Git dependencies. Their
        # exact source remains inventoried, but vulnerability matching is limited.
        if source.startswith(("registry+", "sparse+")):
            component["purl"] = f"pkg:cargo/{quote(package_name, safe='')}@{quote(version, safe='')}"
            if source != CRATES_IO:
                component["purl"] += "?repository_url=" + quote(source.split("+", 1)[1], safe="")
            checksum = package.get("checksum")
            if not isinstance(checksum, str) or not re.fullmatch(r"[0-9a-f]{64}", checksum):
                raise ValueError(f"{package_name}: registry package lacks its SHA-256 checksum")
            component["hashes"] = [{"alg": "SHA-256", "content": checksum}]
        components.append(component)
        declared = package.get("dependencies", [])
        if not isinstance(declared, list):
            raise ValueError(f"{package_name}: dependencies must be an array")
        resolved = set()
        for dep in declared:
            parsed = DEPENDENCY.fullmatch(dep) if isinstance(dep, str) else None
            if parsed is None:
                raise ValueError(f"{package_name}: invalid locked dependency {dep!r}")
            dep_name, dep_version, dep_source = parsed.groups()
            candidates = [candidate for candidate in indexed if
                          candidate[0] == dep_name and
                          (dep_version is None or candidate[1] == dep_version) and
                          (dep_source is None or candidate[2] == dep_source)]
            if len(candidates) != 1:
                raise ValueError(f"{package_name}: dependency {dep!r} resolves to {len(candidates)} locked packages")
            resolved.add(reference(candidates[0]))
        dependencies.append({"ref": reference(key), "dependsOn": sorted(resolved)})

    lock_hash = hashlib.sha256(lock_bytes).hexdigest()
    serial = uuid.uuid5(uuid.NAMESPACE_URL, f"cargo-lock:{name}:{source_sha}:{lock_hash}")
    return {
        "$schema": "http://cyclonedx.org/schema/bom-1.6.schema.json",
        "bomFormat": "CycloneDX", "specVersion": "1.6", "version": 1,
        "serialNumber": f"urn:uuid:{serial}",
        "metadata": {
            "component": {"type": "application", "name": name, "version": source_sha},
            "properties": [
                {"name": "repository-standards:source-sha", "value": source_sha},
                {"name": "repository-standards:lockfile-sha256", "value": lock_hash},
                {"name": "repository-standards:inventory-scope", "value": "all Cargo.lock packages; includes dev, build, optional and target-specific resolution"},
                {"name": "repository-standards:claim-boundary", "value": "source resolution, not binary composition; excludes OS libraries and independently resolved bindings/build-script downloads; Git/path vulnerability matching is limited"},
            ],
        },
        "components": components,
        "dependencies": dependencies,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lockfile", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--source-sha", required=True)
    args = parser.parse_args()
    try:
        if args.lockfile.resolve() == args.output.resolve():
            raise ValueError("output must not overwrite the lockfile")
        document = generate(args.lockfile.read_bytes(), args.name, args.source_sha)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except (OSError, UnicodeError, ValueError) as error:
        print(f"Cargo inventory failed: {error}", file=sys.stderr)
        return 1
    print(f"Inventoried {len(document['components'])} locked packages in {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
