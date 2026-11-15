"""Inventory an exact local image using checksum-pinned Syft release bytes."""
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
import urllib.parse
import urllib.request


VERSION = "1.57.1"
SOURCE_COMMIT = "a0c0d3890a9d79421c403e8fcadec50a2e55bf21"
ARCHIVE_URL = (
    "https://github.com/anchore/syft/releases/download/v1.57.1/"
    "syft_1.57.1_linux_amd64.tar.gz"
)
ARCHIVE_SIZE = 31432061
ARCHIVE_SHA256 = "bf52519eb57f675d47c07d43213cb6dff6449f3d6d1147ff6701ed91f44eef0c"
CONFIG = b"check-for-app-update: false\nscope: squashed\nexclude: []\n"
IMAGE = re.compile(r"localhost/offline-ai-security@sha256:[0-9a-f]{64}")
FAILURE = "Image SBOM evidence collection failed"


class EvidenceError(RuntimeError):
    """A fixed diagnostic without source, tool output or supplied arguments."""


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def download_tool(work):
    archive = work / "syft.tar.gz"
    size = 0
    with urllib.request.urlopen(ARCHIVE_URL, timeout=60) as response:
        if urllib.parse.urlsplit(response.geturl()).scheme != "https":
            raise EvidenceError(FAILURE)
        with archive.open("xb") as output:
            while block := response.read(1024 * 1024):
                size += len(block)
                if size > ARCHIVE_SIZE:
                    raise EvidenceError(FAILURE)
                output.write(block)
    if size != ARCHIVE_SIZE or digest(archive) != ARCHIVE_SHA256:
        raise EvidenceError(FAILURE)
    binary = work / "syft"
    with tarfile.open(archive, "r:gz") as bundle:
        member = bundle.getmember("syft")
        if not member.isfile():
            raise EvidenceError(FAILURE)
        with bundle.extractfile(member) as source, binary.open("xb") as output:
            shutil.copyfileobj(source, output)
    binary.chmod(0o700)
    return binary


def command(arguments, environment, timeout=60, output=None):
    return subprocess.run(
        [str(arg) for arg in arguments], check=True, env=environment,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE if output is None else output,
        stderr=subprocess.DEVNULL, timeout=timeout,
    ).stdout


def verify_spdx(report, image):
    """Check Syft 1.57.1's SPDX 2.3 document/root-image identity fields."""
    name, image_digest = image.split("@")
    if (report.get("spdxVersion") != "SPDX-2.3"
            or report.get("SPDXID") != "SPDXRef-DOCUMENT"
            or not isinstance(report.get("packages"), list)
            or not isinstance(report.get("relationships"), list)):
        raise EvidenceError(FAILURE)
    creators = report.get("creationInfo", {}).get("creators", [])
    if not {"Tool: syft-" + VERSION, "Tool: syft-v" + VERSION}.intersection(creators):
        raise EvidenceError(FAILURE)
    described = {item.get("relatedSpdxElement") for item in report["relationships"]
                 if item.get("spdxElementId") == "SPDXRef-DOCUMENT"
                 and item.get("relationshipType") == "DESCRIBES"}
    roots = [item for item in report["packages"] if item.get("SPDXID") in described]
    if (len(roots) != 1 or roots[0].get("primaryPackagePurpose") != "CONTAINER"
            or roots[0].get("name") != name
            or roots[0].get("versionInfo") != image_digest):
        raise EvidenceError(FAILURE)


def collect(image, evidence, work):
    previous_mask = os.umask(0o077)
    try:
        return _collect(image, evidence, work)
    finally:
        os.umask(previous_mask)


def _collect(image, evidence, work):
    evidence = evidence / "sbom"
    evidence.mkdir(mode=0o700, parents=True, exist_ok=False)
    receipt = {
        "schema_version": 1, "kind": "offline-image-sbom-evidence",
        "status": "failed", "last_stage": "preflight",
        "release_qualified": False, "scope": "squashed",
        "scanner": {
            "name": "syft", "version": VERSION, "source_commit": SOURCE_COMMIT,
            "archive_url": ARCHIVE_URL, "archive_size": ARCHIVE_SIZE,
            "archive_sha256": ARCHIVE_SHA256,
        },
    }
    try:
        if not IMAGE.fullmatch(image):
            raise EvidenceError(FAILURE)
        if platform.system() != "Linux" or platform.machine() != "x86_64":
            raise EvidenceError(FAILURE)
        work.mkdir(mode=0o700, parents=True, exist_ok=False)
        work = work.resolve(strict=True)
        # Explicit policy prevents config discovery; inherited options cannot
        # change the target, catalogers, exclusions, format or network behavior.
        environment = {key: value for key, value in os.environ.items()
                       if not key.startswith("SYFT_")}
        config = evidence / "syft.yaml"
        config.write_bytes(CONFIG)
        receipt["image"] = image
        receipt["image_digest"] = image.split("@")[1]
        receipt["last_stage"] = "docker-context"
        endpoint = environment.get("DOCKER_HOST") or command(
            ["docker", "context", "inspect", "--format", "{{.Endpoints.docker.Host}}"],
            environment).decode().strip()
        if not endpoint.startswith("unix:///") or any(char.isspace() for char in endpoint):
            raise EvidenceError(FAILURE)
        environment["DOCKER_HOST"] = endpoint
        environment.pop("DOCKER_CONTEXT", None)
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
        version_bytes = command(arguments + ["version", "--output", "json"], environment)
        version = json.loads(version_bytes)
        (evidence / "syft-version.json").write_bytes(version_bytes)
        if version.get("version", "").removeprefix("v") != VERSION:
            raise EvidenceError(FAILURE)
        receipt["last_stage"] = "sbom-scan"
        report_path = evidence / "sbom.spdx.json"
        with report_path.open("xb") as output:
            command(arguments + ["scan", "docker:" + image, "--scope", "squashed",
                                 "--output", "spdx-json"], environment,
                    timeout=1200, output=output)
        receipt["last_stage"] = "sbom-identity"
        report = json.loads(report_path.read_bytes())
        verify_spdx(report, image)
        receipt["evidence_sha256"] = {
            name: digest(evidence / name)
            for name in ("sbom.spdx.json", "syft-version.json", "syft.yaml")
        }
        receipt["package_count"] = len(report["packages"])
        receipt["collected_at"] = datetime.now(timezone.utc).isoformat()
        receipt["last_stage"] = "complete"
        receipt["status"] = "collected"
    except Exception:
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
