#!/usr/bin/env python3
"""Read-only inventory of selected declared Cargo dependencies (not a resolved graph)."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import tomllib

CANDIDATES = frozenset({
    "serde", "tokio", "clap", "rayon", "polars", "thiserror", "anyhow",
    "tracing", "regex", "reqwest", "sqlx", "crossbeam", "ratatui",
    "itertools", "proptest", "criterion", "insta", "pyo3", "bytes",
    "syn", "quote",
})
# The review names 21 crates; retain this exact set rather than inventing a 22nd.
SKIP_DIRS = frozenset({".git", ".venv", "node_modules", "target", "vendor", "dist", "build"})
NOTE = "Manifest declarations are not a resolved Cargo dependency graph."


def _candidate_declarations(package: str, path: str, section: str, deps: object) -> list[dict]:
    if not isinstance(deps, dict):
        return []
    declarations = []
    for alias, specification in sorted(deps.items()):
        if isinstance(specification, str):
            details = {"version": specification}
        elif isinstance(specification, dict):
            details = specification
        else:
            continue
        name = details.get("package", alias)
        if name not in CANDIDATES:
            continue
        features = details.get("features", [])
        declarations.append({
            "path": path,
            "crate": package,
            "section": section,
            "name": name,
            "alias": alias,
            "version": details.get("version"),
            "workspace_inherited": details.get("workspace") is True,
            "optional": details.get("optional") is True,
            "default_features": details.get("default-features"),
            "features": sorted(features) if isinstance(features, list) else [],
        })
    return declarations


def _manifests(root: Path):
    for directory, subdirs, files in os.walk(root, followlinks=False):
        subdirs[:] = sorted(d for d in subdirs if d not in SKIP_DIRS and not (Path(directory) / d).is_symlink())
        if "Cargo.toml" in files:
            path = Path(directory) / "Cargo.toml"
            if not path.is_symlink():
                yield path


def inventory(root: Path) -> dict:
    """Return deterministic, path-only error reporting without modifying the input tree."""
    root = root.resolve()
    declarations: list[dict] = []
    errors: list[dict] = []
    count = 0
    for manifest in _manifests(root):
        count += 1
        relative = manifest.relative_to(root).as_posix()
        try:
            with manifest.open("rb") as handle:
                config = tomllib.load(handle)
        except (OSError, tomllib.TOMLDecodeError):
            errors.append({"path": relative, "error": "unreadable_or_invalid_toml"})
            continue
        if not isinstance(config, dict):
            continue
        package_config = config.get("package", {})
        package = package_config.get("name", "<workspace>") if isinstance(package_config, dict) else "<workspace>"
        if not isinstance(package, str):
            package = "<unknown>"
        for section in ("dependencies", "dev-dependencies", "build-dependencies"):
            declarations.extend(_candidate_declarations(package, relative, section, config.get(section)))
        targets = config.get("target", {})
        if isinstance(targets, dict):
            for target, target_config in sorted(targets.items()):
                if isinstance(target_config, dict):
                    for section in ("dependencies", "dev-dependencies", "build-dependencies"):
                        declarations.extend(_candidate_declarations(
                            package, relative, f"target.{target}.{section}", target_config.get(section)
                        ))
    return {
        "schema_version": "1.0.0",
        "manifest_count": count,
        "declarations": sorted(declarations, key=lambda item: (
            item["path"], item["section"], item["name"], item["alias"]
        )),
        "errors": sorted(errors, key=lambda item: item["path"]),
        "notes": [NOTE, "Workspace-inherited features and transitive versions require Cargo resolution."],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path, help="local repository or checkout directory")
    args = parser.parse_args()
    if not args.root.is_dir():
        parser.error("root must be an existing directory")
    report = inventory(args.root)
    print(json.dumps(report, sort_keys=True, indent=2))
    return 2 if report["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
