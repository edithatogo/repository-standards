"""Bind the reviewed Wolfi advisory dispositions to one verified hosted scan."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

CATALOG = Path(__file__).with_name("wolfi-image-review.json")
CPYTHON = Path(__file__).with_name("cpython-backports.json")
GLIBC = Path(__file__).with_name("glibc-backports.json")
IMAGE = re.compile(r"localhost/offline-ai-security@sha256:[0-9a-f]{64}\Z")
GLIBC_ICONV_ADVISORY = "CVE-2026-124024"
GLIBC_ICONV_PROBE = """\
import os

try:
    with os.scandir("/usr/lib/gconv") as entries:
        for entry in entries:
            if entry.name.lower().startswith(("ibm1390.so", "ibm1399.so")):
                print(entry.name)
except FileNotFoundError:
    pass
"""


def verify_image_identity(image: str, evidence: Path) -> None:
    receipt = json.loads((evidence / "vulnerability" / "receipt.json").read_bytes())
    image_id = subprocess.check_output(
        ["docker", "image", "inspect", "--format", "{{.Id}}", image],
        timeout=45,
        stderr=subprocess.DEVNULL,
        text=True,
    ).strip()
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", image_id) or receipt["image_id"] != image_id:
        raise ValueError("The scan receipt belongs to a different installed image")


def verify_glibc_iconv_absence(runner: list[str], image: str) -> bool:
    packages = subprocess.check_output(
        runner + ["--entrypoint", "sh", image, "-eu", "-c",
                  "apk --repositories-file /dev/null info -v"],
        timeout=45,
        stderr=subprocess.DEVNULL,
        text=True,
    ).splitlines()
    modules = subprocess.check_output(
        runner + ["--entrypoint", "python", image, "-I", "-B", "-c", GLIBC_ICONV_PROBE],
        timeout=45,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    has_glibc = any(package.startswith("glibc-2.44-2.44-r") for package in packages)
    has_iconv = any(package.startswith(("glibc-2.44-iconv-", "glibc-iconv-")) for package in packages)
    return has_glibc and not has_iconv and not modules


def verify_image_backports(image: str) -> dict:
    catalog = json.loads(CPYTHON.read_bytes())
    runner = [
        "docker", "run", "--rm", "--pull=never", "--network", "none", "--read-only",
        "--cap-drop", "ALL", "--security-opt", "no-new-privileges", "--user", "65534:65534",
    ]
    contents = subprocess.check_output(
        runner + [
            "--mount", f"type=bind,src={CPYTHON.parent.resolve()},dst=/review,readonly",
            "--entrypoint", "python", image, "-I", "-B", "/review/cpython_backports.py",
            "/review/cpython-backports.json",
        ],
        timeout=45,
        stderr=subprocess.DEVNULL,
    )
    if json.loads(contents) != sorted(catalog["findings"]):
        raise ValueError("CPython backport verification is incomplete")
    glibc = json.loads(GLIBC.read_bytes())
    checksums = subprocess.check_output(
        runner + ["--entrypoint", "sha256sum", image, "--", *glibc["files"]],
        timeout=45,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    expected = "".join(f"{digest}  {name}\n" for name, digest in glibc["files"].items())
    if checksums != expected:
        raise ValueError("The glibc library or package SBOM differs from the reviewed bytes")
    glibc["iconv_absent"] = verify_glibc_iconv_absence(runner, image)
    return {"python-3.15": catalog, glibc["package"]: glibc}


def review_image(image: str, evidence: Path, *, backports: dict | None = None) -> dict:
    folder = evidence / "vulnerability"
    receipt = json.loads((folder / "receipt.json").read_bytes())
    contents = (folder / "grype.json").read_bytes()
    report = json.loads(contents)
    advisories = report["matches"]
    ignored = report.get("ignoredMatches", [])
    review_bytes = CATALOG.read_bytes()
    catalog = json.loads(review_bytes)
    report_digest = hashlib.sha256(contents).hexdigest()
    if (
        not IMAGE.fullmatch(image)
        or receipt["image"] != image
        or receipt["kind"] != "offline-image-vulnerability-evidence"
        or receipt["schema_version"] != 1
        or receipt["status"] != "review_pending"
        or receipt["scope"] != "all-layers"
        or receipt["last_stage"] != "complete"
        or receipt["evidence_sha256"]["grype.json"] != report_digest
        or receipt["image_id"] != report["source"]["target"]["imageID"]
        or report["distro"]["name"] != "wolfi"
        or not isinstance(advisories, list)
        or not isinstance(ignored, list)
        or receipt["matches"] != len(advisories)
        or receipt["ignored_matches"] != len(ignored)
        or catalog["schema_version"] != 1
        or catalog["kind"] != "offline-wolfi-advisory-review"
    ):
        raise ValueError("Image review inputs do not agree")

    findings = []
    for match in advisories:
        advisory, package = match["vulnerability"], match["artifact"]
        identity = {
            "advisory": advisory["id"],
            "package": package["name"],
            "version": package["version"],
            "severity": advisory["severity"],
        }
        expected = catalog["findings"].get(identity["advisory"])
        disposition = "unreviewed"
        if expected and all(expected[key] == identity[key] for key in ("package", "version", "severity")):
            disposition = expected["disposition"]
        proof = (backports or {}).get(identity["package"])
        if (
            proof is not None
            and identity["version"] == proof["package_version"]
            and disposition != "unreviewed"
        ):
            if disposition == "component_absence_unverified":
                if (
                    identity["advisory"] == GLIBC_ICONV_ADVISORY
                    and identity["package"] == "glibc-2.44"
                    and proof.get("iconv_absent") is True
                ):
                    disposition = "verified_component_absent"
            elif identity["advisory"] in proof["findings"]:
                disposition = "verified_backport"
        findings.append({**identity, "disposition": disposition})
    verified = {"verified_backport", "verified_component_absent"}
    blocked = any(match["disposition"] not in verified for match in findings)
    return {
        "schema_version": 1,
        "kind": catalog["kind"],
        "status": "blocked" if blocked or ignored else "passed",
        "image": image,
        "report_sha256": report_digest,
        "review_catalog_sha256": hashlib.sha256(review_bytes).hexdigest(),
        "database_sha256": receipt["database_sha256"],
        "ignored_matches": len(ignored),
        "backport_catalog_sha256": {
            name: hashlib.sha256(file.read_bytes()).hexdigest()
            for name, file in (("python-3.15", CPYTHON), ("glibc-2.44", GLIBC))
            if name in (backports or {})
        },
        "findings": findings,
    }


def main() -> int:
    try:
        _, image, location = sys.argv
        if not IMAGE.fullmatch(image):
            raise ValueError("Invalid image identity")
        evidence = Path(location)
        verify_image_identity(image, evidence)
        review = review_image(image, evidence, backports=verify_image_backports(image))
        with (evidence / "wolfi-image-disposition.json").open("x", encoding="utf-8") as stream:
            json.dump(review, stream, indent=2, sort_keys=True)
            stream.write("\n")
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError):
        print("Wolfi image review could not verify the scan receipt", file=sys.stderr)
        return 2
    if review["status"] != "passed":
        print("Wolfi image review found unresolved or ignored advisories", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
