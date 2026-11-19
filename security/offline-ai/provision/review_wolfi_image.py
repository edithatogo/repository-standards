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
IMAGE = re.compile(r"localhost/offline-ai-security@sha256:[0-9a-f]{64}\Z")


def verify_image_backports(image: str) -> dict:
    catalog = json.loads(CPYTHON.read_bytes())
    contents = subprocess.check_output(
        [
            "docker", "run", "--rm", "--pull=never", "--network", "none", "--read-only",
            "--cap-drop", "ALL", "--security-opt", "no-new-privileges", "--user", "65534:65534",
            "--mount", f"type=bind,src={CPYTHON.parent.resolve()},dst=/review,readonly",
            "--entrypoint", "python", image, "-I", "-B", "/review/cpython_backports.py",
            "/review/cpython-backports.json",
        ],
        timeout=45,
        stderr=subprocess.DEVNULL,
    )
    if json.loads(contents) != sorted(catalog["findings"]):
        raise ValueError("CPython backport verification is incomplete")
    return catalog


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
        if (
            backports is not None
            and identity["package"] == "python-3.15"
            and identity["version"] == backports["package_version"]
            and identity["advisory"] in backports["findings"]
            and disposition != "unreviewed"
        ):
            disposition = "verified_backport"
        findings.append({**identity, "disposition": disposition})
    blocked = any(match["disposition"] != "verified_backport" for match in findings)
    return {
        "schema_version": 1,
        "kind": catalog["kind"],
        "status": "blocked" if blocked or ignored else "passed",
        "image": image,
        "report_sha256": report_digest,
        "review_catalog_sha256": hashlib.sha256(review_bytes).hexdigest(),
        "database_sha256": receipt["database_sha256"],
        "ignored_matches": len(ignored),
        "cpython_backport_catalog_sha256": hashlib.sha256(CPYTHON.read_bytes()).hexdigest() if backports else None,
        "findings": findings,
    }


def main() -> int:
    try:
        _, image, location = sys.argv
        if not IMAGE.fullmatch(image):
            raise ValueError("Invalid image identity")
        evidence = Path(location)
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
