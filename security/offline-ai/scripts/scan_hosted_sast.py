"""Apply both hosted SAST engines to the validated parent-index inventory."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import stat
import subprocess
import sys

SCRIPTS = Path(__file__).resolve().parent
sys.path[:0] = [str(SCRIPTS), str(SCRIPTS.parent / "provision")]
import scan_opengrep  # noqa: E402
from hosted_sast_assets import load_lock, verify_bundle  # noqa: E402
import probe_semgrep_rust as semgrep  # noqa: E402

ASSETS = Path("/hosted-sast")
RUSTFMT = Path("/rust-toolchain/bin/rustfmt")


def verify_linkage(binary: Path, lock: dict, env: dict[str, str]) -> None:
    result = subprocess.run(
        [str(binary)], env={**env, "LD_TRACE_LOADED_OBJECTS": "1"},
        stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        check=True, text=True, timeout=30,
    )
    loaded = {}
    for line in result.stdout.splitlines():
        name, separator, target = line.strip().partition(" => ")
        if separator:
            loaded[name] = target.split(" ", 1)[0]
    for package in lock["packages"]:
        for library in package["libraries"]:
            name = library["name"]
            if loaded.get(name) != str(binary.parent / "libs" / name):
                raise ValueError("Hosted SAST linkage")
    if "not found" in result.stdout:
        raise ValueError("Hosted SAST linkage")


def scan(root: Path, binary: Path, rustfmt: Path, env: dict[str, str],
         *, mark=lambda _stage: None) -> int:
    mark("parent-index")
    paths, submodules = scan_opengrep.tracked_sources(root, offline_container=True)
    rust = [name for name in paths if name.lower().endswith(".rs")]
    non_rust = [name for name in paths if not name.lower().endswith(".rs")]
    mark("opengrep-coverage")
    opengrep = scan_opengrep.scan_paths(root, scan_opengrep.RULES, non_rust, submodules)
    mark("rust-fixtures")
    semgrep.verify_rust_fixtures(binary, env)
    rust_findings = 0
    if rust:
        mark("rust-syntax")
        syntax_env = {key: value for key, value in env.items() if key != "LD_LIBRARY_PATH"}
        semgrep.verify_syntax(rustfmt, root, rust, syntax_env)
        mark("semgrep-coverage")
        rust_findings = len(semgrep.scan(binary, root, rust, env))
    print(f"Hosted SAST parent-index sources {len(paths)}. "
          f"Opengrep scanned {opengrep.scanned}/{len(non_rust)}, findings {opengrep.findings}, "
          f"scanner errors {opengrep.errors}, parser failures {opengrep.parse_failures}. "
          f"Semgrep scanned {len(rust)}/{len(rust)}, findings {rust_findings}. "
          f"Uninitialized submodules outside scope {submodules}.")
    if opengrep.status:
        if opengrep.parse_failures:
            mark("opengrep-parser")
        elif opengrep.errors or (opengrep.failures and not opengrep.findings):
            mark("opengrep-errors")
        else:
            mark("opengrep-findings" if opengrep.findings else "opengrep-coverage")
        return 2
    if rust_findings:
        mark("semgrep-findings")
        return 2
    mark("passed")
    return 0


def main(receipt: Path) -> int:
    def mark(value):
        receipt.write_text(value + "\n", encoding="ascii")

    try:
        mark("asset-verification")
        lock = load_lock()
        if any(not os.statvfs(path).f_flag & os.ST_RDONLY
               for path in (ASSETS, RUSTFMT.parent.parent)):
            raise ValueError("Hosted SAST mounts are writable")
        verify_bundle(ASSETS, lock)
        if not stat.S_ISREG(RUSTFMT.lstat().st_mode):
            raise ValueError("Rustfmt identity")
        with RUSTFMT.open("rb") as stream:
            if hashlib.file_digest(stream, "sha256").hexdigest() != lock["rustfmt_sha256"]:
                raise ValueError("Rustfmt identity")
        env = scan_opengrep.secrets_scan.clean_environment(offline_container=True)
        for name in tuple(env):
            if name.startswith(("SEMGREP_", "OPENGREP_", "LD_")):
                env.pop(name)
        env["SEMGREP_SEND_METRICS"] = "off"
        env["LD_LIBRARY_PATH"] = str(ASSETS / "libs")
        binary = ASSETS / semgrep.CORE
        mark("runtime-linkage")
        verify_linkage(binary, lock, env)
        # Scope the signed AlmaLinux libraries to Semgrep. Rustfmt uses the
        # runner image's normal linkage, as do the Git and Opengrep commands.
        return scan(scan_opengrep.ROOT, binary, RUSTFMT, env, mark=mark)
    except (scan_opengrep.ScanError, scan_opengrep.secrets_scan.ScanError,
            OSError, ValueError, TypeError, KeyError, RuntimeError, subprocess.SubprocessError):
        print("Hosted SAST failed closed", file=sys.stderr)
        return 2


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(2)
    raise SystemExit(main(Path(sys.argv[1])))
