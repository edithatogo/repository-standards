"""Scan every supported source in the checked-out parent Git index, without egress."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
import stat
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor

# Only the read-only policy mount can supply the Git isolation helper.
POLICY = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(POLICY / "scripts"))
import secrets_scan  # noqa: E402

ROOT = Path("/work")
RULES = POLICY / "security/offline-ai/.opengrep/rules.yaml"
SOURCE_LANGUAGES = {
    ".py": "python", ".pyi": "python", ".rs": "rust",
    ".js": "javascript", ".jsx": "javascript", ".mjs": "javascript", ".cjs": "javascript",
    ".ts": "typescript", ".tsx": "typescript", ".mts": "typescript", ".cts": "typescript",
}
SOURCE_SUFFIXES = frozenset(SOURCE_LANGUAGES)
ESBUILD_LOADERS = {
    ".js": "js", ".mjs": "js", ".cjs": "js", ".jsx": "jsx",
    ".ts": "ts", ".mts": "ts", ".cts": "ts", ".tsx": "tsx",
}
ESBUILD = "/opt/promptfoo/node_modules/@esbuild/linux-x64/bin/esbuild"
MAX_REPORT_BYTES = 64 * 1024 * 1024
MAX_BATCH_BYTES = 64 * 1024
TIMEOUT_SECONDS = 1500


class ScanError(Exception):
    """Do not expose repository paths, source or scanner diagnostics."""


@dataclass(frozen=True)
class ScanOutcome:
    tracked: int
    scanned: int
    findings: int
    errors: int
    parse_failures: int
    failures: int
    uninitialized_submodules: int

    @property
    def status(self) -> int:
        return 2 if (self.failures or self.findings or self.errors or self.parse_failures
                     or self.scanned != self.tracked) else 0


def tracked_sources(root: Path, *, offline_container: bool) -> tuple[list[str], int]:
    """Enumerate source files in the parent index; reject unscannable material."""
    root = root.resolve(strict=True)
    env = secrets_scan.clean_environment(offline_container=offline_container)
    with tempfile.TemporaryFile() as output, tempfile.TemporaryFile() as errors:
        result = subprocess.run(
            ["git", "-C", str(root), "ls-files", "--stage", "-z"],
            env=env, stdin=subprocess.DEVNULL, stdout=output, stderr=errors,
            check=False, timeout=30,
        )
        if result.returncode or errors.tell() or output.tell() > MAX_REPORT_BYTES:
            raise ScanError("index unavailable")
        output.seek(0)
        raw = output.read()
    if raw and not raw.endswith(b"\0"):
        raise ScanError("invalid index")
    selected: list[str] = []
    submodules = 0
    for entry in raw.split(b"\0"):
        if not entry:
            continue
        header, separator, name = entry.partition(b"\t")
        parts = header.split(b" ")
        if not separator or len(parts) != 3 or parts[2] != b"0":
            raise ScanError("invalid index")
        mode = parts[0]
        relative = os.fsdecode(name)
        posix = PurePosixPath(relative)
        if not relative or posix.is_absolute() or str(posix) != relative or ".." in posix.parts:
            raise ScanError("invalid index path")
        path = root / relative
        if mode == b"160000":
            submodules += 1
            # A populated submodule is code outside the parent index; refusing it
            # prevents an apparently complete scan of only the parent sources.
            if (path.resolve() != path
                    or (path.exists() and (not path.is_dir() or any(path.iterdir())))):
                raise ScanError("materialized submodule")
            continue
        # PurePath.suffix is empty for a bare filename such as `.py`, which
        # Opengrep itself recognizes as source. Include those dotfiles too.
        if not relative.lower().endswith(tuple(SOURCE_SUFFIXES)):
            continue
        if mode not in {b"100644", b"100755"}:
            raise ScanError("unsupported source mode")
        if path.resolve(strict=True) != path or not stat.S_ISREG(path.lstat().st_mode):
            raise ScanError("source is not a regular contained file")
        selected.append(str(path))
    if not selected or len(set(selected)) != len(selected):
        raise ScanError("empty or duplicate source inventory")
    return selected, submodules


def batches(paths: list[str]):
    current: list[str] = []
    size = 0
    for path in paths:
        length = len(os.fsencode(path)) + 1
        if length > MAX_BATCH_BYTES:
            raise ScanError("source path too long")
        if current and size + length > MAX_BATCH_BYTES:
            yield current
            current, size = [], 0
        current.append(path)
        size += length
    if current:
        yield current


def parse_sources(paths: list[str], executable: str, esbuild: str, root: Path, env: dict[str, str]) -> int:
    """Require the rule engine's own strict parser to accept each selected file."""
    def parse(path: str) -> bool:
        with open(path, "rb") as source:
            if source.readline(1024).rstrip(b"\r\n") == b"version https://git-lfs.github.com/spec/v1":
                raise ScanError("unresolved LFS pointer")
        lower = path.lower()
        language = next(language for suffix, language in SOURCE_LANGUAGES.items() if lower.endswith(suffix))
        if language == "python":
            # Opengrep's parser can accept malformed Python without reporting
            # an error. Compile for syntax only; never execute consumer code.
            checked = subprocess.run(
                [sys.executable, "-I", "-W", "error::SyntaxWarning", "-c",
                 "import pathlib,sys; compile(pathlib.Path(sys.argv[1]).read_bytes(), '<source>', 'exec', dont_inherit=True)",
                 path], cwd=root, env=env, stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False, timeout=120,
            )
            if checked.returncode:
                return True
        elif language in {"javascript", "typescript"}:
            loader = next(loader for suffix, loader in ESBUILD_LOADERS.items() if lower.endswith(suffix))
            # This is the already inventoried and hash-verified Promptfoo esbuild
            # binary. It parses input only; transformed output is discarded.
            with open(path, "rb") as source:
                checked = subprocess.run(
                    [esbuild, "--loader=" + loader, "--log-level=silent"],
                    cwd=root, env=env, stdin=source, stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL, check=False, timeout=120,
                )
            if checked.returncode:
                return True
        result = subprocess.run(
            [executable, "scan", "--dump-ast", "--lang", language, "--strict", "--json", "--", path],
            cwd=root, env=env, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL, check=False, timeout=120,
        )
        return result.returncode != 0

    # The parser emits source-derived ASTs; discard both streams and retain only
    # status counts. Bound concurrency to the hosted container's CPU budget.
    with ThreadPoolExecutor(max_workers=4) as executor:
        return sum(executor.map(parse, paths))


def scan(root: Path, rules: Path, executable: str = "/usr/local/bin/opengrep", *, esbuild: str = ESBUILD,
         offline_container: bool = True) -> ScanOutcome:
    """Require complete scan reporting, zero findings and zero parser errors."""
    paths, submodules = tracked_sources(root, offline_container=offline_container)
    return scan_paths(root, rules, paths, submodules, executable, esbuild=esbuild,
                      offline_container=offline_container)


def scan_paths(root: Path, rules: Path, paths: list[str], submodules: int,
               executable: str = "/usr/local/bin/opengrep", *, esbuild: str = ESBUILD,
               offline_container: bool = True) -> ScanOutcome:
    """Scan a partition of the already validated parent Git index."""
    scanned: set[str] = set()
    findings = errors = failures = 0
    env = secrets_scan.clean_environment(offline_container=offline_container)
    for name in tuple(env):
        if name.startswith(("SEMGREP_", "OPENGREP_")):
            env.pop(name)
    env["SEMGREP_SEND_METRICS"] = "off"
    parse_failures = parse_sources(paths, executable, esbuild, root, env)
    for batch in batches(paths):
        command = [
            executable, "scan", "--no-git-ignore", "--semgrepignore-filename=/dev/null",
            "--max-target-bytes=0", "--strict", "--disable-nosem", "--taint-intrafile",
            # Bound each rule on each target, including on the offline x64 runner.
            "--timeout=30",
            "--config", str(rules), "--error", "--json", "--", *batch,
        ]
        with tempfile.TemporaryFile() as output, tempfile.TemporaryFile() as diagnostics:
            result = subprocess.run(
                command, cwd=root, env=env, stdin=subprocess.DEVNULL, stdout=output, stderr=diagnostics,
                check=False, timeout=TIMEOUT_SECONDS,
            )
            if output.tell() > MAX_REPORT_BYTES or diagnostics.tell() > MAX_REPORT_BYTES:
                raise ScanError("scanner report too large")
            output.seek(0)
            payload = json.load(output, object_pairs_hook=secrets_scan.unique_object)
        if not isinstance(payload, dict) or not isinstance(payload.get("results"), list):
            raise ScanError("invalid scanner report")
        reported = payload.get("paths")
        scan_errors = payload.get("errors")
        if (not isinstance(reported, dict) or not isinstance(reported.get("scanned"), list)
                or not isinstance(scan_errors, list) or reported.get("skipped")):
            raise ScanError("invalid scanner coverage")
        observed = reported["scanned"]
        if (any(not isinstance(path, str) for path in observed)
                or len(set(observed)) != len(observed) or set(observed) != set(batch)
                or scanned.intersection(observed)):
            raise ScanError("incomplete scanner coverage")
        scanned.update(observed)
        findings += len(payload["results"])
        errors += len(scan_errors)
        failures += result.returncode != 0
    return ScanOutcome(len(paths), len(scanned), findings, errors, parse_failures, failures, submodules)


def main() -> int:
    try:
        outcome = scan(ROOT, RULES)
        print(f"SAST parent-index sources: {outcome.tracked}; scanned: {outcome.scanned}; "
              f"findings: {outcome.findings}; scanner errors: {outcome.errors}; "
              f"parser failures: {outcome.parse_failures}; "
              f"uninitialized submodules outside scope: {outcome.uninitialized_submodules}")
        return outcome.status
    except (ScanError, secrets_scan.ScanError, OSError, ValueError, UnicodeError, subprocess.SubprocessError):
        print("SAST tracked-source scan failed closed", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
