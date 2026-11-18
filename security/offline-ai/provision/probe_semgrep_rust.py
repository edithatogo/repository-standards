"""Exercise standalone Semgrep's Rust coverage in the hosted canary."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
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


def probe(binary: Path, consumer: Path) -> dict[str, int | str]:
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
    if scan(binary, consumer, rust, environment):
        raise ValueError("Rust consumer findings")
    return {"status": "passed", "semgrep": VERSION, "rust_fixtures": len(fixtures), "rust_sources": len(rust)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--prepare", type=Path)
    mode.add_argument("--probe", nargs=2, type=Path, metavar=("BINARY", "CONSUMER"))
    args = parser.parse_args()
    try:
        if args.prepare:
            prepare(args.prepare)
        else:
            binary, consumer = (value.resolve(strict=True) for value in args.probe)
            print(json.dumps(probe(binary, consumer), sort_keys=True))
    except (OSError, KeyError, ValueError, TypeError, RuntimeError, subprocess.SubprocessError, scan_opengrep.ScanError,
            scan_opengrep.secrets_scan.ScanError):
        print('{"status":"failed"}')
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
