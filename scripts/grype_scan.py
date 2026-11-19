#!/usr/bin/env python3
"""Scan immutable images or resolved SBOMs; preserve evidence before enforcing policy.

The action uses checksum-pinned upstream binaries and an explicit configuration.
It does not interpret repository .grype/.syft files or suppress findings. A
nonempty inventory proves identifiable packages, not completeness or reachability.
"""
from __future__ import annotations

import argparse
import collections
import datetime as dt
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
from pathlib import Path
from urllib.parse import unquote

TOOLS = {
    "grype": {"version": "0.122.1", "amd64": "f1ba7e2917ee1395618de20a98da0aa7c0fb1788927797651047c50502a37538",
              "arm64": "819e5be3d9516432fedb7b6b56df7306c3a16607606dfc05826eefbb00e471da"},
    "syft": {"version": "1.57.2", "amd64": "ad92bd3ec1b94a3df01d4d0aec199afa9c42b72e86da436ff5f837914d32706b",
             "arm64": "8efe605309c98798e1ee0cffdcf8c05ca26819b4cd44c0b03650f1e963e9bdb6"},
}
SEVERITIES = ("unknown", "negligible", "low", "medium", "high", "critical")
MAX_DB_AGE_HOURS = 120


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def prepare_directory(output: Path) -> None:
    if output.is_symlink() or (output.exists() and (not output.is_dir() or any(output.iterdir()))):
        raise ValueError("evidence directory must be new or empty; stale evidence is not reusable")
    output.mkdir(parents=True, exist_ok=True)


def image_reference(value: str) -> str:
    error = "image must be a registry reference at an immutable sha256 digest, without scheme or credentials"
    # Parse bounded segments rather than a nested repetition over untrusted input.
    if len(value) > 1024 or value.count("@") != 1:
        raise ValueError(error)
    repository, digest = value.split("@")
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", digest):
        raise ValueError(error)
    segments = repository.split("/")
    if len(segments) < 2:
        raise ValueError(error)
    host, separator, port = segments[0].partition(":")
    if not re.fullmatch(r"[a-z0-9][a-z0-9.-]{0,252}", host):
        raise ValueError(error)
    if separator and (not port.isascii() or not port.isdigit() or not 1 <= int(port) <= 65535):
        raise ValueError(error)
    if any(not re.fullmatch(r"[a-z0-9][a-z0-9._-]{0,127}", segment) for segment in segments[1:]):
        raise ValueError(error)
    return value


def resolved_version(value: object, ecosystem: str = "") -> bool:
    if not isinstance(value, str) or not value.strip() or value.lower() in {
        "noassertion", "unknown", "none", "latest"
    } or re.search(r"[\s<>=*|,\[\]()]", value):
        return False
    # Debian's pre-release/backport separator and RPM's snapshot separators are
    # parts of exact installed versions. Leading semver ~ and ^ are ranges.
    if value.startswith(("~", "^")):
        return False
    if "~" in value and ecosystem not in ("deb", "rpm"):
        return False
    if "^" in value and ecosystem != "rpm":
        return False
    return True


def inventory_count(document: dict) -> int:
    """Require versioned, purl-identifiable packages; reject version requirements."""
    if not isinstance(document, dict):
        raise ValueError("SBOM must be a JSON object")
    if document.get("bomFormat") == "CycloneDX":
        pending = list(document.get("components", []))
        packages = []
        while pending:
            component = pending.pop()
            if not isinstance(component, dict):
                raise ValueError("invalid CycloneDX component")
            pending.extend(component.get("components", []))
            if component.get("type") in ("file", "data"):
                continue
            packages.append((component.get("name"), component.get("version"), component.get("purl")))
    elif str(document.get("spdxVersion", "")).startswith("SPDX-"):
        packages = []
        for package in document.get("packages", []):
            purls = [ref.get("referenceLocator") for ref in package.get("externalRefs", [])
                     if ref.get("referenceType") == "purl"]
            packages.append((package.get("name"), package.get("versionInfo"), purls[0] if purls else None))
    elif isinstance(document.get("schema"), dict) and "artifacts" in document:
        packages = [(p.get("name"), p.get("version"), p.get("purl")) for p in document["artifacts"]]
    else:
        raise ValueError("expected CycloneDX, SPDX or Syft JSON, not generic package metadata")
    count = 0
    for name, version, purl in packages:
        # Unidentified local/workspace components remain inventoried; they do not
        # satisfy the requirement for at least one matchable dependency.
        if not purl:
            if version and not resolved_version(version):
                raise ValueError("inventory contains unresolved package versions")
            continue
        if not isinstance(purl, str) or not purl.startswith("pkg:"):
            raise ValueError("inventory contains an invalid purl")
        ecosystem = purl[4:].split("/", 1)[0]
        if not name or not resolved_version(version, ecosystem):
            raise ValueError("inventory contains invalid package identities or unresolved versions")
        identity = purl.split("?", 1)[0].split("#", 1)[0]
        if "@" not in identity or not resolved_version(unquote(identity.rsplit("@", 1)[1]), ecosystem):
            raise ValueError("purl must identify a resolved package version")
        if unquote(identity.rsplit("@", 1)[1]) != version:
            raise ValueError("package version and purl version disagree")
        count += 1
    if count == 0:
        raise ValueError("SBOM has no versioned package identities; metadata or byte inventories are insufficient")
    return count


def validate_database(status: dict, now: dt.datetime | None = None) -> float:
    if status.get("valid") is not True or status.get("error"):
        raise ValueError("vulnerability database is not valid")
    try:
        built = dt.datetime.fromisoformat(status["built"].replace("Z", "+00:00"))
        if built.tzinfo is None:
            raise ValueError("database build time has no timezone")
        age = ((now or dt.datetime.now(dt.timezone.utc)) - built).total_seconds() / 3600
    except (KeyError, TypeError) as error:
        raise ValueError("database build time is unavailable") from error
    if age < -1 or age > MAX_DB_AGE_HOURS:
        raise ValueError("vulnerability database is stale or has an invalid future timestamp")
    return round(age, 3)


def evaluate(report: dict, exit_code: int, cutoff: str, mode: str) -> dict:
    if exit_code not in (0, 2):
        raise ValueError(f"Grype operational failure (exit {exit_code})")
    if not isinstance(report.get("matches"), list):
        raise ValueError("Grype report has no matches array")
    if report.get("ignoredMatches"):
        raise ValueError("suppressed matches require a separately reviewed exception policy")
    counts = collections.Counter({severity: 0 for severity in SEVERITIES})
    for match in report["matches"]:
        severity = match.get("vulnerability", {}).get("severity", "").lower()
        if severity not in SEVERITIES:
            raise ValueError("Grype report contains an invalid severity")
        counts[severity] += 1
    blocked = sum(counts[s] for s in SEVERITIES[SEVERITIES.index(cutoff):])
    if (exit_code == 2) != (blocked > 0):
        raise ValueError("Grype exit code and report policy outcome disagree")
    return {"outcome": "blocked" if blocked and mode == "enforce" else "findings" if report["matches"] else "pass",
            "blocking_matches": blocked, "severities": dict(counts), "matches": len(report["matches"])}


def scanner_environment(environment: dict) -> dict:
    # Keep standard Docker credential discovery; remove scanner policy overrides.
    return {key: value for key, value in environment.items() if not key.startswith(("GRYPE_", "SYFT_"))}


def download_tool(name: str, directory: Path) -> tuple[Path, dict]:
    arch = {"x86_64": "amd64", "aarch64": "arm64"}.get(platform.machine())
    if platform.system() != "Linux" or arch is None:
        raise ValueError("shared scanner requires Linux amd64 or arm64")
    pin = TOOLS[name]
    filename = f"{name}_{pin['version']}_linux_{arch}.tar.gz"
    url = f"https://github.com/anchore/{name}/releases/download/v{pin['version']}/{filename}"
    archive = directory / filename
    with urllib.request.urlopen(url, timeout=60) as response, archive.open("wb") as target:
        shutil.copyfileobj(response, target)
    if sha256(archive) != pin[arch]:
        raise ValueError(f"{name} release archive checksum mismatch")
    binary = directory / name
    with tarfile.open(archive, "r:gz") as bundle:
        member = bundle.getmember(name)
        if not member.isfile():
            raise ValueError("tool archive does not contain a regular binary")
        with bundle.extractfile(member) as source, binary.open("wb") as target:
            shutil.copyfileobj(source, target)
    binary.chmod(0o755)
    return binary, {"version": pin["version"], "archive_sha256": pin[arch], "binary_sha256": sha256(binary), "url": url}


def command(args: list[str], output: Path, error: Path, environment: dict, cwd: Path, timeout: int = 1200) -> int:
    with output.open("wb") as stdout, error.open("wb") as stderr:
        return subprocess.run(args, stdout=stdout, stderr=stderr, env=environment, cwd=cwd, check=False, timeout=timeout).returncode


def checked(args: list[str], output: Path, environment: dict, cwd: Path) -> None:
    exit_code = command(args, output, output.with_suffix(".stderr.log"), environment, cwd)
    if exit_code != 0:
        raise ValueError(f"{Path(args[0]).name} operation failed (exit {exit_code}); see retained {output.name} and stderr")


def scan(args: argparse.Namespace, output: Path, evidence: dict) -> None:
    if not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", args.source_sha):
        raise ValueError("source-sha must be an exact lowercase Git commit hash")
    if args.platform and not re.fullmatch(r"linux/(amd64|arm64)(/v[0-9]+)?", args.platform):
        raise ValueError("unsupported image platform")
    source = output / "input.sbom.json"
    if args.sbom:
        input_path = Path(args.sbom)
        if input_path.is_symlink() or not input_path.is_file():
            raise ValueError("SBOM input must be an existing regular file")
        shutil.copyfile(input_path, source)
        evidence["input"] = {"kind": "sbom", "sha256": sha256(source), "original_filename": input_path.name}
        evidence["identified_packages"] = inventory_count(json.loads(source.read_text(encoding="utf-8")))
    else:
        evidence["input"] = {"kind": "image", "reference": image_reference(args.image), "platform": args.platform}

    environment = scanner_environment(dict(os.environ))
    with tempfile.TemporaryDirectory(prefix="grype-tools-", dir=os.environ.get("RUNNER_TEMP")) as work:
        directory = Path(work)
        grype, evidence["grype"] = download_tool("grype", directory)
        # Explicit config and a neutral working directory prevent ambient
        # repository/home ignore rules from changing the shared policy.
        grype_config = directory / "grype.yaml"
        grype_config.write_text("check-for-app-update: false\nonly-fixed: false\nonly-notfixed: false\nignore: []\n"
                                "db:\n  auto-update: false\n  validate-age: true\n  max-allowed-built-age: 120h\n  require-update-check: true\n", encoding="utf-8")
        environment["GRYPE_DB_CACHE_DIR"] = str(directory / "db")
        checked([str(grype), "version", "-o", "json"], output / "grype-version.json", environment, directory)
        version = json.loads((output / "grype-version.json").read_text())
        if str(version.get("version", "")).lstrip("v") != TOOLS["grype"]["version"]:
            raise ValueError("installed Grype version disagrees with pinned version")
        if args.image:
            syft, evidence["syft"] = download_tool("syft", directory)
            syft_config = directory / "syft.yaml"
            syft_config.write_text("check-for-app-update: false\n", encoding="utf-8")
            checked([str(syft), "version", "-o", "json"], output / "syft-version.json", environment, directory)
            catalog = [str(syft), "scan", "registry:" + args.image, "--config", str(syft_config), "-o", "syft-json"]
            if args.platform:
                catalog.extend(["--platform", args.platform])
            checked(catalog, source, environment, directory)
            document = json.loads(source.read_text(encoding="utf-8"))
            metadata = document.get("source", {}).get("metadata", {})
            if metadata.get("manifestDigest") != args.image.rsplit("@", 1)[1]:
                raise ValueError("catalogued manifest digest differs from requested image; pass a platform manifest digest")
            if args.platform:
                actual = metadata.get("os", "") + "/" + metadata.get("architecture", "")
                if actual != "/".join(args.platform.split("/")[:2]):
                    raise ValueError("catalogued image platform differs from requested platform")
            evidence["identified_packages"] = inventory_count(document)
            evidence["input"]["sbom_sha256"] = sha256(source)
        checked([str(grype), "db", "update", "--config", str(grype_config)], output / "db-update.log", environment, directory)
        checked([str(grype), "db", "status", "-o", "json", "--config", str(grype_config)], output / "db-status.json", environment, directory)
        status = json.loads((output / "db-status.json").read_text())
        evidence["database"] = status
        evidence["database_age_hours"] = validate_database(status)
        database_path = Path(status.get("path", ""))
        if not database_path.is_file() or not database_path.resolve().is_relative_to(directory):
            raise ValueError("database status did not identify the isolated database file")
        evidence["database_sha256"] = sha256(database_path)
        exit_code = command([str(grype), "sbom:" + str(source), "--config", str(grype_config), "--fail-on", args.severity_cutoff,
                             "--output", "json"], output / "report.json", output / "scan.stderr.log", environment, directory)
        evidence["scanner_exit_code"] = exit_code
        if exit_code not in (0, 2):
            raise ValueError(f"Grype operational failure (exit {exit_code})")
        report = json.loads((output / "report.json").read_text(encoding="utf-8"))
        evidence.update(evaluate(report, exit_code, args.severity_cutoff, args.mode))
        evidence["report_sha256"] = sha256(output / "report.json")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--sbom")
    target.add_argument("--image")
    parser.add_argument("--platform", default="")
    parser.add_argument("--mode", choices=("advisory", "enforce"), default="advisory")
    parser.add_argument("--severity-cutoff", choices=SEVERITIES[1:], default="critical")
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--source-role", choices=("build-source", "monitor-workflow", "observed-release-tag"), default="build-source")
    parser.add_argument("--output-directory", type=Path, required=True)
    args = parser.parse_args()
    output = args.output_directory.absolute()
    try:
        prepare_directory(output)
    except (OSError, ValueError) as error:
        print(f"Grype evidence setup failed: {error}", file=sys.stderr)
        return 1
    evidence = {"schema_version": 1, "outcome": "error", "mode": args.mode, "severity_cutoff": args.severity_cutoff,
                "source_sha": args.source_sha, "source_role": args.source_role, "repository": os.environ.get("GITHUB_REPOSITORY", ""),
                "run_id": os.environ.get("GITHUB_RUN_ID", ""), "run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT", ""),
                "started_at": dt.datetime.now(dt.timezone.utc).isoformat(), "coverage_claim": "identified package versions; not completeness, reachability or exploitability"}
    write_json(output / "policy.json", evidence)
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as stream:
            stream.write(f"evidence-directory={output}\n")
    try:
        scan(args, output, evidence)
    except (OSError, ValueError, KeyError, TypeError, tarfile.TarError, subprocess.SubprocessError) as error:
        evidence["outcome"] = "error"
        evidence["error"] = str(error)
    evidence["finished_at"] = dt.datetime.now(dt.timezone.utc).isoformat()
    write_json(output / "policy.json", evidence)
    files = sorted(path for path in output.iterdir() if path.is_file())
    (output / "SHA256SUMS").write_text("".join(f"{sha256(path)}  {path.name}\n" for path in files), encoding="utf-8")
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as stream:
            stream.write(f"evidence-directory={output}\nreport={output / 'report.json'}\npolicy-outcome={evidence['outcome']}\n")
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as stream:
            stream.write(f"### Grype vulnerability policy\n\nOutcome: **{evidence['outcome']}**. Mode: {args.mode}. "
                         f"Threshold: {args.severity_cutoff}. Identified packages: {evidence.get('identified_packages', 0)}. "
                         f"Blocking matches: {evidence.get('blocking_matches', 'unavailable')}. Full evidence is retained separately.\n")
    print(f"Grype policy outcome: {evidence['outcome']}; evidence: {output}")
    return 1 if evidence["outcome"] in ("error", "blocked") else 0


if __name__ == "__main__":
    raise SystemExit(main())
