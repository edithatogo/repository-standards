"""Exercise standalone Semgrep's Rust coverage in the hosted canary."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from functools import cache
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import tomllib
import urllib.request
from zipfile import ZipFile

POLICY = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(POLICY / "scripts"))
import scan_opengrep  # noqa: E402
from verify_sast_fixtures import FIXTURES, RULES, RUST_CLEAN, RUST_FINDING_LINES, RUST_FINDINGS  # noqa: E402

VERSION = "1.185.0"
WHEEL_URL = (
    "https://files.pythonhosted.org/packages/f2/13/0d4dc8d124794105f300082c46e3d8ad45eac7af63113b57a5966629b5a3/"
    "semgrep-1.185.0-cp310.cp311.cp312.cp313.cp314.py310.py311.py312.py313.py314-none-manylinux_2_34_x86_64.whl"
)
WHEEL_BYTES = 72302138
WHEEL_SHA256 = "0eb6aaadad5b957af96d1300487e10af1dc8016e8ef53072effb48cd4906c02b"
BIN_PREFIX = f"semgrep-{VERSION}.data/purelib/semgrep/bin/"
CORE = "semgrep-core"
CORE_BYTES = 266890296
LIBRARY = re.compile(r"libs/lib[A-Za-z0-9_+-]+\.so(?:\.[0-9]+)+")
LIBRARY_COUNT = 26
MALFORMED_RUST = (
    b"fn broken( { }",
    b"pub struct Broken { value: }",
    b"fn broken() { let value = ; }",
    b"fn broken() { let value: u32 = (10; }",
    b"enum Broken { Option{value: } }",
    b'fn broken() { let value = "unfinished; }',
)


def prepare(destination: Path) -> None:
    """Verify the released Linux wheel and extract its native files only."""
    with urllib.request.urlopen(WHEEL_URL, timeout=120) as response:
        if not response.geturl().startswith("https://files.pythonhosted.org/"):
            raise ValueError("Wheel download origin")
        wheel = response.read(WHEEL_BYTES + 1)
    if len(wheel) != WHEEL_BYTES or hashlib.sha256(wheel).hexdigest() != WHEEL_SHA256:
        raise ValueError("Wheel identity")
    with tempfile.TemporaryFile() as wheel_file:
        wheel_file.write(wheel)
        with ZipFile(wheel_file) as archive:
            entries = {
                member.filename.removeprefix(BIN_PREFIX): member
                for member in archive.infolist()
                if member.filename.startswith(BIN_PREFIX)
                and LIBRARY.fullmatch(member.filename.removeprefix(BIN_PREFIX))
            }
            if len(entries) != LIBRARY_COUNT or any(
                not 0 < member.file_size <= 8 * 1024 * 1024 for member in entries.values()
            ):
                raise ValueError("Library inventory")
            core = archive.getinfo(BIN_PREFIX + CORE)
            if core.file_size != CORE_BYTES:
                raise ValueError("Core size")
            entries[CORE] = core
            destination.mkdir(mode=0o755)
            (destination / "libs").mkdir(mode=0o755)
            for name, member in entries.items():
                target = destination / name
                with archive.open(member) as source, target.open("xb") as output:
                    header = source.read(20)
                    if not header.startswith(b"\x7fELF\x02\x01") or header[18:] != b"\x3e\x00":
                        raise ValueError("Linux x64 executable identity")
                    output.write(header)
                    shutil.copyfileobj(source, output)
                target.chmod(0o755 if name == CORE else 0o644)


def scan(binary: Path, root: Path, paths: list[str], environment: dict[str, str]) -> list[dict]:
    if not paths or len(paths) != len(set(paths)):
        raise ValueError("Missing or duplicate targets")
    matches = []
    for batch in scan_opengrep.batches(paths):
        targets = ["Targets", [
            ["CodeTarget", {
                "path": {"fpath": path, "ppath": "/" + str(Path(path).relative_to(root))},
                "analyzer": "rust",
                "products": ["sast"],
            }] for path in batch
        ]]
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryFile() as output:
            inventory = Path(directory) / "targets.json"
            inventory.write_text(json.dumps(targets), encoding="utf-8")
            subprocess.run(
                [str(binary), "-rules", str(RULES), "-targets", str(inventory), "-json_nodots", "-j", "4"],
                cwd=root, env=environment, stdin=subprocess.DEVNULL, stdout=output,
                stderr=subprocess.DEVNULL, timeout=240, check=True,
            )
            if output.tell() > scan_opengrep.MAX_REPORT_BYTES:
                raise ValueError("Oversized scanner report")
            output.seek(0)
            report = json.load(output, object_pairs_hook=scan_opengrep.secrets_scan.unique_object)
        observed = report["paths"]["scanned"]
        if (not isinstance(observed, list) or len(observed) != len(batch) or set(observed) != set(batch)
                or report["paths"].get("skipped") or report["errors"] != [] or report.get("skipped_rules")
                or not isinstance(report["results"], list)):
            raise ValueError("Scanner coverage or errors")
        matches.extend(report["results"])
    return matches


def verify_syntax(rustfmt: Path, root: Path, sources: list[str], environment: dict[str, str]) -> str:
    """Use Rustfmt's compiler parser independently of the rule scanner."""
    @cache
    def manifest(directory: Path) -> dict:
        path = directory / "Cargo.toml"
        if path.is_symlink():
            raise ValueError("Linked Cargo manifest")
        if not path.exists():
            return {}
        return tomllib.loads(path.read_text(encoding="utf-8"))

    def edition_for(path: Path) -> str:
        for parent in path.parents:
            if not parent.is_relative_to(root):
                break
            package = manifest(parent).get("package")
            if package is None:
                continue
            edition = package.get("edition", "2015")
            if edition == {"workspace": True}:
                if "workspace" in package:
                    workspace = (parent / package["workspace"]).resolve(strict=True)
                    if not workspace.is_relative_to(root):
                        raise ValueError("External Cargo workspace")
                    edition = manifest(workspace)["workspace"]["package"]["edition"]
                else:
                    for directory in (parent, *parent.parents):
                        if not directory.is_relative_to(root):
                            break
                        workspace = manifest(directory).get("workspace")
                        if workspace is not None:
                            edition = workspace["package"]["edition"]
                            break
            if edition not in ("2015", "2018", "2021", "2024"):
                raise ValueError("Unsupported Cargo edition")
            return edition
        # Standalone checked-in examples use the current edition.
        return "2024"

    with tempfile.TemporaryDirectory() as directory:
        def valid(data: bytes, edition: str) -> bool:
            return subprocess.run(
                [str(rustfmt), "--edition", edition, "--emit", "stdout"],
                input=data, cwd=directory, env=environment, stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL, timeout=60, check=False,
            ).returncode == 0

        def file_valid(name: str) -> bool:
            path = Path(name)
            return valid(path.read_bytes(), edition_for(path))

        if not valid(b"fn sample(x: u32) -> u32 { x + 1 }", "2024"):
            raise ValueError("Rust syntax positive control")
        if any(valid(data, "2024") for data in MALFORMED_RUST):
            raise ValueError("Rust syntax negative controls")
        with ThreadPoolExecutor(max_workers=4) as workers:
            outcomes = list(workers.map(file_valid, sources))
        if not all(outcomes):
            raise ValueError("Rust source syntax")
    with rustfmt.open("rb") as binary:
        return hashlib.file_digest(binary, "sha256").hexdigest()


def probe(binary: Path, rustfmt: Path, consumer: Path) -> dict[str, int | str]:
    environment = scan_opengrep.secrets_scan.clean_environment(offline_container=True)
    for key in tuple(environment):
        if key.startswith(("SEMGREP_", "OPENGREP_")):
            environment.pop(key)
    environment["SEMGREP_SEND_METRICS"] = "off"

    fixture_names = RUST_FINDINGS | RUST_CLEAN
    fixtures = [str(FIXTURES / name) for name in sorted(fixture_names)]
    findings = scan(binary, FIXTURES, fixtures, environment)
    hit_lines = {(Path(item["path"]).name, item["start"]["line"]) for item in findings}
    if {name for name, _ in hit_lines} != RUST_FINDINGS or not RUST_FINDING_LINES <= hit_lines:
        raise ValueError("Rust fixture parity")

    tracked, _ = scan_opengrep.tracked_sources(consumer, offline_container=True)
    rust = [path for path in tracked if path.lower().endswith(".rs")]
    rustfmt_sha256 = verify_syntax(rustfmt, consumer, rust, environment)
    if scan(binary, consumer, rust, environment):
        raise ValueError("Rust consumer findings")
    return {
        "status": "passed", "semgrep": VERSION, "rust_fixtures": len(fixtures), "rust_sources": len(rust),
        "rust_syntax": "passed", "malformed_controls": len(MALFORMED_RUST), "rustfmt_sha256": rustfmt_sha256,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--prepare", type=Path)
    mode.add_argument("--probe", nargs=3, type=Path, metavar=("BINARY", "RUSTFMT", "CONSUMER"))
    args = parser.parse_args()
    try:
        if args.prepare:
            prepare(args.prepare)
        else:
            binary, rustfmt, consumer = (value.resolve(strict=True) for value in args.probe)
            print(json.dumps(probe(binary, rustfmt, consumer), sort_keys=True))
    except (OSError, KeyError, ValueError, TypeError, RuntimeError, subprocess.SubprocessError, scan_opengrep.ScanError,
            scan_opengrep.secrets_scan.ScanError):
        print('{"status":"failed"}')
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
