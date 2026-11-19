"""Apply pinned upstream security changes to the Wolfi standard library."""

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import sysconfig
import tempfile


def digest(file: Path) -> str:
    return hashlib.sha256(file.read_bytes()).hexdigest()


def apply_backports(catalog: dict, assets: Path, stdlib: Path) -> None:
    replacements = {}
    with tempfile.TemporaryDirectory(prefix="cpython-backports-") as temporary:
        staging = Path(temporary)
        for fix in catalog["findings"].values():
            if "patch_sha256" not in fix:
                continue
            (name, expected), = fix["files"].items()
            patch = assets / (fix["commit"] + ".patch")
            original = stdlib / name
            if digest(patch) != fix["patch_sha256"] or digest(original) != fix["input_sha256"]:
                raise ValueError("CPython backport inputs differ from the reviewed bytes")
            relative = Path("Lib") / name
            candidate = staging / relative
            candidate.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(original, candidate)
            subprocess.run(
                ["git", "apply", "--whitespace=nowarn", "--include=" + relative.as_posix(), str(patch)],
                cwd=staging,
                check=True,
                timeout=30,
            )
            if digest(candidate) != expected:
                raise ValueError("CPython backport output differs from the reviewed bytes")
            replacements[original] = candidate
        for original, candidate in replacements.items():
            shutil.copyfile(candidate, original)
        for fix in catalog["findings"].values():
            for name in fix["files"]:
                original = stdlib / name
                for bytecode in (original.parent / "__pycache__").glob(original.stem + ".cpython-315*.pyc"):
                    bytecode.unlink()


def verify(catalog: dict, stdlib: Path) -> list[str]:
    if sys.version_info[:3] != (3, 15, 2) or not sys._git[-1] or not catalog["source_commit"].startswith(sys._git[-1]):
        raise ValueError("CPython executable differs from the reviewed build")
    # The archive CLI fix also changes the native interpreter. Confirm that
    # the packaged executable exposes the attribute introduced by that fix.
    if not hasattr(sys, "_path0"):
        raise ValueError("CPython archive CLI backport is missing from the native executable")
    for fix in catalog["findings"].values():
        for name, expected in fix["files"].items():
            if digest(stdlib / name) != expected:
                raise ValueError("CPython standard library differs from the reviewed fixes")
    return sorted(catalog["findings"])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("catalog", type=Path)
    parser.add_argument("--patches", type=Path)
    args = parser.parse_args()
    catalog = json.loads(args.catalog.read_bytes())
    stdlib = Path(sysconfig.get_path("stdlib"))
    if args.patches is not None:
        apply_backports(catalog, args.patches.resolve(strict=True), stdlib)
    print(json.dumps(verify(catalog, stdlib)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
