"""Collect advisory evidence for an exact local image; never approve release."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import tarfile
import urllib.request


VERSION = "0.121.3"
SOURCE_COMMIT = "cd1f23eb50dfb52647090158f453c7359172591f"
ARCHIVE_URL = (
    "https://github.com/anchore/grype/releases/download/v0.121.3/"
    "grype_0.121.3_linux_amd64.tar.gz"
)
ARCHIVE_SIZE = 32643999
ARCHIVE_SHA256 = "e9da18cc1429e786722e32161288103600efffd8e483c90761f90485bd1bec85"
CONFIG = Path(__file__).with_name("grype.yaml")
IMAGE = re.compile(r"localhost/offline-ai-security@sha256:[0-9a-f]{64}")
FAILURE = "Image vulnerability evidence collection failed"


class EvidenceError(RuntimeError):
    """A fixed diagnostic without scanner output or caller-provided values."""


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def download_tool(work):
    archive = work / "grype.tar.gz"
    size = 0
    with urllib.request.urlopen(ARCHIVE_URL, timeout=60) as response:
        with archive.open("xb") as output:
            while block := response.read(1024 * 1024):
                size += len(block)
                if size > ARCHIVE_SIZE:
                    raise EvidenceError(FAILURE)
                output.write(block)
    if size != ARCHIVE_SIZE or digest(archive) != ARCHIVE_SHA256:
        raise EvidenceError(FAILURE)
    binary = work / "grype"
    with tarfile.open(archive, "r:gz") as bundle:
        member = bundle.getmember("grype")
        if not member.isfile():
            raise EvidenceError(FAILURE)
        with bundle.extractfile(member) as source, binary.open("xb") as output:
            shutil.copyfileobj(source, output)
    binary.chmod(0o700)
    return binary


def command(arguments, environment, timeout=60):
    # Raw findings and tool diagnostics never enter workflow logs. The receipt
    # identifies the failed stage; the complete JSON report remains an artifact.
    return subprocess.run(
        [str(arg) for arg in arguments], check=True, env=environment,
        stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL, timeout=timeout,
    ).stdout


def save_json(path, contents):
    data = json.loads(contents)
    with path.open("xb") as output:
        output.write(contents)
    return data


def collect(image, evidence, work):
    evidence = evidence / "vulnerability"
    evidence.mkdir(parents=True, exist_ok=False)
    receipt = {
        "schema_version": 1,
        "kind": "offline-image-vulnerability-evidence",
        "status": "failed",
        "last_stage": "preflight",
        "review_pending": True,
        "vulnerability_review_qualified": False,
        "release_qualified": False,
        "scope": "all-layers",
        "scanner": {
            "name": "grype", "version": VERSION,
            "source_commit": SOURCE_COMMIT, "archive_url": ARCHIVE_URL,
            "archive_size": ARCHIVE_SIZE, "archive_sha256": ARCHIVE_SHA256,
        },
    }
    try:
        if not IMAGE.fullmatch(image):
            raise EvidenceError(FAILURE)
        if platform.system() != "Linux" or platform.machine() != "x86_64":
            raise EvidenceError(FAILURE)
        work.mkdir(parents=True, exist_ok=False)
        work = work.resolve(strict=True)
        # The explicit policy file and an isolated DB cache are authoritative;
        # inherited Grype/Syft settings cannot add hidden ignores or exclusions.
        environment = {key: value for key, value in os.environ.items()
                       if not key.startswith(("GRYPE_", "SYFT_"))}
        environment["GRYPE_DB_CACHE_DIR"] = str(work / "db")
        config = evidence / "grype.yaml"
        config.write_bytes(CONFIG.read_bytes())
        receipt["image"] = image
        receipt["last_stage"] = "image-identity"
        inspected = json.loads(command(["docker", "image", "inspect", image], environment))
        if (not isinstance(inspected, list) or len(inspected) != 1
                or image not in inspected[0].get("RepoDigests", [])
                or inspected[0].get("Os") != "linux"
                or inspected[0].get("Architecture") != "amd64"
                or not re.fullmatch(r"sha256:[0-9a-f]{64}", inspected[0].get("Id", ""))):
            raise EvidenceError(FAILURE)
        receipt["image_id"] = inspected[0]["Id"]
        receipt["last_stage"] = "tool-download"
        binary = download_tool(work)
        arguments = [binary, "--config", config]
        receipt["last_stage"] = "tool-version"
        version = save_json(evidence / "grype-version.json", command(
            arguments + ["version", "--output", "json"], environment))
        if version.get("version", "").removeprefix("v") != VERSION:
            raise EvidenceError(FAILURE)
        receipt["last_stage"] = "scan"
        report_path = evidence / "grype.json"
        command(arguments + ["docker:" + image, "--scope", "all-layers",
                             "--output", "json", "--file", report_path],
                environment, timeout=1200)
        report = json.loads(report_path.read_bytes())
        if (not isinstance(report.get("matches"), list)
                or not isinstance(report.get("ignoredMatches", []), list)
                or report.get("source", {}).get("type") != "image"
                or report["source"].get("target", {}).get("imageID") != receipt["image_id"]
                or report.get("descriptor", {}).get("name") != "grype"
                or report["descriptor"].get("version", "").removeprefix("v") != VERSION):
            raise EvidenceError(FAILURE)
        receipt["last_stage"] = "database-provenance"
        database = save_json(evidence / "grype-db-status.json", command(
            arguments + ["db", "status", "--output", "json"], environment))
        if (database.get("valid") is not True or database.get("error")
                or not database.get("built") or not database.get("schemaVersion")
                or not database.get("from")):
            raise EvidenceError(FAILURE)
        database_path = Path(database["path"]).resolve(strict=True)
        if not database_path.is_relative_to(work / "db"):
            raise EvidenceError(FAILURE)
        receipt["database_sha256"] = digest(database_path)
        receipt["evidence_sha256"] = {
            name: digest(evidence / name) for name in (
                "grype.json", "grype-version.json", "grype-db-status.json", "grype.yaml")
        }
        receipt["matches"] = len(report["matches"])
        receipt["ignored_matches"] = len(report.get("ignoredMatches", []))
        receipt["collected_at"] = datetime.now(timezone.utc).isoformat()
        receipt["last_stage"] = "complete"
        receipt["status"] = "review_pending"
    except Exception:
        # Preserve a fixed failure receipt even for download, parser, DB, timeout,
        # or process errors. No exception text or raw package data is published.
        raise EvidenceError(FAILURE) from None
    finally:
        with (evidence / "receipt.json").open("x", encoding="utf-8") as output:
            json.dump(receipt, output, indent=2, sort_keys=True)
            output.write("\n")


def main(argv=None):
    try:
        arguments = sys.argv[1:] if argv is None else argv
        if len(arguments) != 3:
            raise EvidenceError(FAILURE)
        collect(arguments[0], Path(arguments[1]), Path(arguments[2]))
    except Exception:
        print(FAILURE, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
