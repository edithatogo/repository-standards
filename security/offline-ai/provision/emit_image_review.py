#!/usr/bin/env python3
"""Emit a bounded, hash-bound projection of public image review evidence.

This index preserves every active/ignored match occurrence and every final SPDX
package. It is not the complete reports, a vulnerability acceptance, a fresh
database hash check, or a verification of the downloaded artifact ZIP.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
from urllib.parse import urlsplit

FAILURE = "Image review index emission failed"
OUTPUT = "image-review-index.json"
MAX_INDEX_BYTES = 2 * 1024 * 1024
MAX_REPORT_BYTES = 64 * 1024 * 1024
MAX_RECEIPT_BYTES = 4 * 1024 * 1024
CHUNK_CHARACTERS = 2048
SHA256 = re.compile(r"[0-9a-f]{64}")
DIGEST = re.compile(r"sha256:[0-9a-f]{64}")
POLICY = re.compile(r"[0-9a-f]{40}")
IMAGE = re.compile(r"localhost/offline-ai-security@sha256:[0-9a-f]{64}")
STAGES = (
    "runtime", "network-preflight", "manifest-binding", "asset-preflight",
    "gitleaks-fixtures", "sast-fixtures", "dlp-model", "promptfoo-mock",
)
FILES = (
    "qualification.json", "hosted-execution.json", "preparation.json",
    "preparation-model.json", "os-packages.json", "asset-manifest.json",
    "sbom/receipt.json", "sbom/sbom.spdx.json", "sbom/syft-version.json",
    "sbom/syft.yaml", "vulnerability/receipt.json", "vulnerability/grype.json",
    "vulnerability/grype-version.json", "vulnerability/grype-db-status.json",
    "vulnerability/grype.yaml",
)
SCANNERS = {
    "syft": {
        "name": "syft", "version": "1.57.1",
        "source_commit": "a0c0d3890a9d79421c403e8fcadec50a2e55bf21",
        "archive_url": "https://github.com/anchore/syft/releases/download/v1.57.1/syft_1.57.1_linux_amd64.tar.gz",
        "archive_size": 31432061,
        "archive_sha256": "bf52519eb57f675d47c07d43213cb6dff6449f3d6d1147ff6701ed91f44eef0c",
    },
    "grype": {
        "name": "grype", "version": "0.121.3",
        "source_commit": "cd1f23eb50dfb52647090158f453c7359172591f",
        "archive_url": "https://github.com/anchore/grype/releases/download/v0.121.3/grype_0.121.3_linux_amd64.tar.gz",
        "archive_size": 32643999,
        "archive_sha256": "e9da18cc1429e786722e32161288103600efffd8e483c90761f90485bd1bec85",
    },
}
SYFT_CONFIG = b"check-for-app-update: false\nscope: squashed\nexclude: []\n"
GRYPE_CONFIG = (
    b"# Evidence collection only: findings require a separate vulnerability review.\n"
    b"check-for-app-update: false\nfail-on-severity: \"\"\nonly-fixed: false\n"
    b"only-notfixed: false\nignore: []\nexclude: []\nvex-documents: []\n"
    b"include-matcher-suppressions: true\ndb:\n  auto-update: true\n"
    b"  require-update-check: true\n  validate-age: true\n"
    b"  max-allowed-built-age: 120h\n  validate-by-hash-on-start: true\n"
)


class EvidenceError(ValueError):
    """No source values or scanner output in diagnostics."""


def require(condition):
    if not condition:
        raise EvidenceError(FAILURE)


def object_value(value):
    require(type(value) is dict)
    return value


def array(value, *, nullable=False):
    if value is None and nullable:
        return []
    require(type(value) is list)
    return value


def text(value, *, empty=False):
    require(type(value) is str and len(value) <= 16384)
    require((empty or bool(value)) and not any(ord(c) < 32 or ord(c) == 127 for c in value))
    return value


def hash_text(value):
    require(type(value) is str and SHA256.fullmatch(value) is not None)
    return value


def url(value):
    value = text(value)
    parsed = urlsplit(value)
    require(parsed.scheme in ("http", "https") and bool(parsed.hostname))
    require(parsed.username is None and parsed.password is None)
    return value


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def sha256(payload):
    return hashlib.sha256(payload).hexdigest()


def pairs(items):
    result = {}
    for key, value in items:
        require(key not in result)
        result[key] = value
    return result


def invalid_constant(_value):
    raise EvidenceError(FAILURE)


def read_json(payload):
    return object_value(json.loads(payload.decode("utf-8"), object_pairs_hook=pairs,
                                   parse_constant=invalid_constant))


class Inputs:
    """Only fixed paths, opened relative to a retained directory descriptor."""

    def __init__(self, directory):
        self.fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        self.payloads = {}
        self.records = []

    def close(self):
        os.close(self.fd)

    def read_all(self):
        for relative in FILES:
            parent = os.dup(self.fd)
            try:
                parts = relative.split("/")
                for part in parts[:-1]:
                    child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                                    dir_fd=parent)
                    os.close(parent)
                    parent = child
                fd = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW, dir_fd=parent)
                with os.fdopen(fd, "rb") as stream:
                    info = os.fstat(stream.fileno())
                    limit = MAX_REPORT_BYTES if relative in (
                        "asset-manifest.json", "sbom/sbom.spdx.json",
                        "vulnerability/grype.json") else MAX_RECEIPT_BYTES
                    require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1)
                    require(0 < info.st_size <= limit)
                    payload = stream.read(limit + 1)
                    require(len(payload) == info.st_size and len(payload) <= limit)
            finally:
                os.close(parent)
            self.payloads[relative] = payload
            self.records.append({"path": relative, "size_bytes": len(payload),
                                 "sha256": sha256(payload)})

    def json(self, relative):
        require(relative in FILES)
        return read_json(self.payloads[relative])


def receipt(inputs, relative, kind, status, false_flags=()):
    data = inputs.json(relative)
    require(type(data.get("schema_version")) is int and data["schema_version"] == 1)
    require(data.get("status") == status)
    if kind is not None:
        require(data.get("kind") == kind)
    for flag in false_flags:
        require(data.get(flag) is False)
    return data


def collector(inputs, directory, scanner, status, scope, evidence_names):
    data = receipt(inputs, directory + "/receipt.json",
                   "offline-image-" + ("sbom" if scanner == "syft" else "vulnerability")
                   + "-evidence", status, ("release_qualified",))
    require(data.get("last_stage") == "complete" and data.get("scope") == scope)
    require(data.get("scanner") == SCANNERS[scanner])
    hashes = object_value(data.get("evidence_sha256"))
    require(set(hashes) == set(evidence_names))
    for name in evidence_names:
        require(hash_text(hashes[name]) == sha256(inputs.payloads[directory + "/" + name]))
    version = inputs.json(directory + "/" + scanner + "-version.json")
    require(text(version.get("version")).removeprefix("v") == SCANNERS[scanner]["version"])
    return data


def verify(inputs, image, policy):
    require(IMAGE.fullmatch(image) is not None and POLICY.fullmatch(policy) is not None)
    q = receipt(inputs, "qualification.json", "offline-image-qualification", "passed",
                ("application_adapters_qualified", "runner_registration_qualified"))
    require(q.get("policy_commit") == policy and q.get("image") == image)
    require(q.get("cleanup_status") == "not-needed")
    stages = array(q.get("stages"))
    require(len(stages) == len(STAGES))
    for item, name in zip(stages, STAGES, strict=True):
        require(object_value(item).get("name") == name and item.get("status") == "passed")
    hosted = receipt(inputs, "hosted-execution.json", "offline-image-hosted-execution",
                     "passed", ("scanner_network_access", "runner_registration_qualified",
                                "application_adapters_qualified", "image_exported",
                                "image_redistribution_qualified", "release_qualified"))
    require(hosted.get("policy_commit") == policy and hosted.get("last_stage") == "complete")
    require(hosted.get("preparation_network_access") is True)
    prep = receipt(inputs, "preparation.json", "offline-vendor-preparation", "prepared",
                   ("image_qualified", "runner_registered"))
    require(prep.get("stages") == dict.fromkeys(("binaries", "python", "promptfoo", "model"), "passed"))
    manifest_hash = sha256(inputs.payloads["asset-manifest.json"])
    require(hash_text(q.get("asset_manifest_sha256")) == manifest_hash)
    require(hash_text(prep.get("manifest_sha256")) == manifest_hash)
    require(hash_text(prep.get("model_provenance_sha256"))
            == sha256(inputs.payloads["preparation-model.json"]))
    model = receipt(inputs, "preparation-model.json", None, "prepared",
                    ("model_execution_qualified", "image_qualified", "runner_registration_qualified"))
    os_packages = receipt(inputs, "os-packages.json", "offline-os-packages", "prepared",
                          ("release_qualified", "runner_registration_qualified"))
    require(os_packages.get("last_stage") == "complete")
    sbom = collector(inputs, "sbom", "syft", "collected", "squashed",
                     ("sbom.spdx.json", "syft-version.json", "syft.yaml"))
    grype = collector(inputs, "vulnerability", "grype", "review_pending", "all-layers",
                      ("grype.json", "grype-version.json", "grype-db-status.json", "grype.yaml"))
    require(grype.get("review_pending") is True and grype.get("vulnerability_review_qualified") is False)
    require(sbom.get("image") == image == grype.get("image"))
    require(sbom.get("image_digest") == image.split("@")[1])
    image_id = text(sbom.get("image_id"))
    require(DIGEST.fullmatch(image_id) is not None and image_id == grype.get("image_id"))
    require(inputs.payloads["sbom/syft.yaml"] == SYFT_CONFIG)
    require(inputs.payloads["vulnerability/grype.yaml"] == GRYPE_CONFIG)
    report = inputs.json("vulnerability/grype.json")
    descriptor = object_value(report.get("descriptor"))
    require(descriptor.get("name") == "grype"
            and text(descriptor.get("version")).removeprefix("v") == SCANNERS["grype"]["version"])
    source = object_value(report.get("source"))
    target = object_value(source.get("target"))
    require(source.get("type") == "image" and target.get("imageID") == image_id)
    require(target.get("userInput") == image and image in array(target.get("repoDigests")))
    manifest_digest = text(target.get("manifestDigest"))
    require(DIGEST.fullmatch(manifest_digest) is not None)
    for field, expected in (("config", image_id), ("manifest", manifest_digest)):
        raw = target.get(field)
        require(type(raw) is str and 0 < len(raw) <= MAX_RECEIPT_BYTES)
        decoded = base64.b64decode(raw, validate=True)
        require("sha256:" + sha256(decoded) == expected)
        if field == "manifest":
            require(object_value(read_json(decoded).get("config")).get("digest") == image_id)
    database = inputs.json("vulnerability/grype-db-status.json")
    require(database.get("valid") is True and not database.get("error"))
    database_record = {
        "schema_version": text(database.get("schemaVersion")),
        "built": text(database.get("built")), "source": url(database.get("from")),
        "sha256_reported_by_collector": hash_text(grype.get("database_sha256")),
        "database_rehashed_by_index": False,
    }
    provenance = {
        "vendor_catalog_sha256_reported": hash_text(prep.get("sources_catalog_sha256")),
        "model_catalog_sha256_reported": hash_text(model.get("source_catalog_sha256")),
        "os_catalog_sha256_reported": hash_text(os_packages.get("catalog_sha256")),
        "os_base_status_sha256_reported": hash_text(os_packages.get("base_status_sha256")),
        "os_base_image_reported": text(os_packages.get("base_image")),
    }
    identity = {"image": image, "registry_digest": image.split("@")[1],
                "image_id": image_id, "embedded_manifest_digest": manifest_digest,
                "policy_commit": policy, "asset_manifest_sha256": manifest_hash}
    return identity, provenance, database_record, sbom, grype, report


def optional_fields(source, names):
    source = object_value(source)
    return {name: text(source[name], empty=True) for name in names if name in source}


def package_record(raw):
    raw = object_value(raw)
    record = {key: text(raw.get(key), empty=key in ("version", "type"))
              for key in ("id", "name", "version", "type")}
    record.update(optional_fields(raw, ("purl", "language")))
    record["locations"] = []
    for location in array(raw.get("locations"), nullable=True):
        location = object_value(location)
        require("path" in location)
        record["locations"].append(optional_fields(location, ("path", "layerID", "accessPath")))
    record["upstreams"] = [optional_fields(value, ("name", "version"))
                           for value in array(raw.get("upstreams"), nullable=True)]
    return record


def advisory_record(raw):
    raw = object_value(raw)
    record = {"id": text(raw.get("id")), "dataSource": url(raw["dataSource"])
              if raw.get("dataSource") else ""}
    record.update(optional_fields(raw, ("namespace", "severity")))
    record["urls"] = [url(value) for value in array(raw.get("urls"), nullable=True)]
    record["knownExploited"] = []
    for value in array(raw.get("knownExploited"), nullable=True):
        value = object_value(value)
        item = {"cve": text(value.get("cve"))}
        item.update(optional_fields(value, ("dateAdded", "dueDate")))
        record["knownExploited"].append(item)
    if "fix" in raw:
        fix = object_value(raw["fix"])
        record["fix"] = {"state": text(fix.get("state"), empty=True),
                         "versions": [text(value) for value in array(fix.get("versions"), nullable=True)]}
    if "advisories" in raw:
        record["advisories"] = [
            {"id": text(object_value(value).get("id")), "link": url(value.get("link"))}
            for value in array(raw["advisories"], nullable=True)]
    return record


def match_detail(raw):
    raw = object_value(raw)
    record = {key: text(raw.get(key)) for key in ("type", "matcher")}
    for key, names in (("searchedBy", ("namespace",)), ("found", ("namespace", "vulnerabilityID", "versionConstraint"))):
        value = raw.get(key)
        require(value is None or type(value) is dict)
        if value is not None:
            record[key] = optional_fields(value, names)
    if raw.get("fix") is not None:
        record["fix"] = optional_fields(raw["fix"], ("suggestedVersion",))
    return record


def suppression_rule(raw):
    raw = object_value(raw)
    # Grype 0.121.3's presenter has no rule ID. Hash the entire original rule;
    # retain selectors, but never print its free-form reason.
    record = {"original_rule_sha256": sha256(canonical(raw))}
    record.update(optional_fields(raw, (
        "namespace", "vulnerability", "fix-state", "vex-status", "vex-justification", "match-type")))
    if raw.get("package") is not None:
        record["package"] = optional_fields(raw["package"], (
            "name", "version", "language", "type", "location", "upstream-name"))
    if "reason" in raw:
        require(type(raw["reason"]) is str)
        record["reason_sha256"] = sha256(raw["reason"].encode("utf-8"))
    return record


class Table:
    def __init__(self):
        self.values = []
        self.keys = {}

    def add(self, value):
        key = canonical(value)
        if key not in self.keys:
            self.keys[key] = len(self.values)
            self.values.append(value)
        return self.keys[key]


def project_findings(report):
    packages, advisories, details, rules = Table(), Table(), Table(), Table()
    groups = {}
    for key in ("matches", "ignoredMatches"):
        entries = array(report.get(key, []))
        rows = []
        for raw in entries:
            raw = object_value(raw)
            row = {
                "package": packages.add(package_record(raw.get("artifact"))),
                "advisory": advisories.add(advisory_record(raw.get("vulnerability"))),
                "related_advisories": [advisories.add(advisory_record(value)) for value in
                                       array(raw.get("relatedVulnerabilities"), nullable=True)],
                "match_details": [details.add(match_detail(value)) for value in array(raw.get("matchDetails"))],
            }
            if key == "ignoredMatches":
                applied = array(raw.get("appliedIgnoreRules"))
                row["suppression_rules"] = [rules.add(suppression_rule(value)) for value in applied]
            else:
                require(not raw.get("appliedIgnoreRules"))
            rows.append(row)
        groups["active_matches" if key == "matches" else "ignored_matches"] = rows
    return dict(groups, packages=packages.values, advisories=advisories.values,
                match_details=details.values, suppression_rules=rules.values)


def project_spdx(report, image):
    require(report.get("spdxVersion") == "SPDX-2.3" and report.get("SPDXID") == "SPDXRef-DOCUMENT")
    creators = array(object_value(report.get("creationInfo")).get("creators"))
    version = SCANNERS["syft"]["version"]
    require("Tool: syft-" + version in creators or "Tool: syft-v" + version in creators)
    described = {
        object_value(value).get("relatedSpdxElement")
        for value in array(report.get("relationships"))
        if object_value(value).get("spdxElementId") == "SPDXRef-DOCUMENT"
        and value.get("relationshipType") == "DESCRIBES"
    }
    rows, roots, seen = [], [], set()
    for raw in array(report.get("packages")):
        raw = object_value(raw)
        spdx_id = text(raw.get("SPDXID"))
        require(spdx_id not in seen)
        seen.add(spdx_id)
        if spdx_id in described:
            roots.append(raw)
        record = {"SPDXID": spdx_id, "name": text(raw.get("name")), "purls": []}
        record.update(optional_fields(raw, ("versionInfo", "primaryPackagePurpose")))
        for ref in array(raw.get("externalRefs", [])):
            ref = object_value(ref)
            if ref.get("referenceType") == "purl":
                purl = text(ref.get("referenceLocator"))
                require(purl.startswith("pkg:"))
                record["purls"].append(purl)
        rows.append(record)
    require(len(roots) == 1 and described == {roots[0]["SPDXID"]})
    require(roots[0].get("primaryPackagePurpose") == "CONTAINER"
            and roots[0].get("name") == image.split("@")[0]
            and roots[0].get("versionInfo") == image.split("@")[1])
    return rows


def build_index(inputs, image, policy):
    identity, provenance, database, sbom, grype, report = verify(inputs, image, policy)
    findings = project_findings(report)
    spdx = project_spdx(inputs.json("sbom/sbom.spdx.json"), image)
    counts = {"active_matches": len(findings["active_matches"]),
              "ignored_matches": len(findings["ignored_matches"]), "spdx_packages": len(spdx)}
    for actual, expected in ((counts["active_matches"], grype.get("matches")),
                             (counts["ignored_matches"], grype.get("ignored_matches")),
                             (counts["spdx_packages"], sbom.get("package_count"))):
        require(type(expected) is int and actual == expected)
    require(type(report.get("matches")) is list)
    return {
        "schema_version": 1, "kind": "offline-image-review-index", "status": "review_pending",
        "projection": {
            "full_report": False, "all_match_occurrences_preserved": True,
            "table_references": "zero-based indexes; occurrence order follows each source array",
            "preserved": {
                "packages": ["id", "name", "version", "type", "purl", "language",
                             "locations.path", "locations.layerID", "locations.accessPath",
                             "upstreams.name", "upstreams.version"],
                "advisories": ["id", "dataSource", "namespace", "severity", "urls",
                               "fix.state", "fix.versions", "advisories.id", "advisories.link",
                               "knownExploited.cve", "knownExploited.dateAdded", "knownExploited.dueDate"],
                "matches": ["artifact reference", "vulnerability reference", "relatedVulnerabilities references",
                            "matchDetails.type", "matchDetails.matcher", "matchDetails.searchedBy.namespace",
                            "matchDetails.found.namespace", "matchDetails.found.vulnerabilityID",
                            "matchDetails.found.versionConstraint", "matchDetails.fix.suggestedVersion",
                            "appliedIgnoreRules references"],
                "suppression_rules": ["canonical full-rule SHA256", "reason SHA256", "namespace",
                                      "vulnerability", "fix-state", "vex-status", "vex-justification",
                                      "match-type", "package.name", "package.version", "package.language",
                                      "package.type", "package.location", "package.upstream-name"],
                "spdx_packages": ["SPDXID", "name", "versionInfo", "primaryPackagePurpose",
                                  "externalRefs with referenceType purl"],
            },
            "excluded": ["descriptions", "CVSS", "EPSS", "risk", "CWE metadata",
                         "arbitrary package/vendor metadata", "CPE lists", "matched symbols",
                         "package alerts", "free-form suppression reasons", "raw image config/manifest",
                         "detector/model output", "unselected report and receipt fields"],
            "authority": "original complete source reports, identified by sources[].sha256",
        },
        "identity": identity, "sources": inputs.records, "preparation_provenance": provenance,
        "scanners": SCANNERS, "scopes": {"spdx": "squashed", "vulnerabilities": "all-layers"},
        "database": database, "totals": counts, "findings": findings, "spdx_packages": spdx,
        "qualification": {
            "actual_image_controls": list(STAGES), "actual_image_controls_status": "passed",
            "vulnerability_review_qualified": False, "runner_registration_qualified": False,
            "application_adapters_qualified": False, "image_redistribution_qualified": False,
            "release_qualified": False, "artifact_archive_verified_by_index": False,
        },
    }


def emit(image, directory, policy):
    inputs = Inputs(directory)
    try:
        inputs.read_all()
        payload = canonical(build_index(inputs, image, policy)) + b"\n"
        require(len(payload) <= MAX_INDEX_BYTES)
        contents = payload.decode("utf-8")
        chunks = (len(contents) + CHUNK_CHARACTERS - 1) // CHUNK_CHARACTERS
        record = {
            "path": OUTPUT, "encoding": "utf-8", "size_bytes": len(payload),
            "sha256": sha256(payload),
            "git_blob_sha": hashlib.sha1(
                f"blob {len(payload)}\0".encode("ascii") + payload, usedforsecurity=False).hexdigest(),
            "chunks": chunks, "complete": True,
        }
        fd = os.open(OUTPUT, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                     0o600, dir_fd=inputs.fd)
        try:
            with os.fdopen(fd, "wb") as output:
                output.write(payload)
        except BaseException:
            os.unlink(OUTPUT, dir_fd=inputs.fd)
            raise
        # JSON-escaped, prefixed lines cannot become workflow command lines.
        # No chunks are printed until every input and the whole size pass.
        for index in range(chunks):
            print("OFFLINE_IMAGE_REVIEW_CHUNK " + json.dumps(
                {"path": OUTPUT, "index": index, "total": chunks,
                 "data": contents[index * CHUNK_CHARACTERS:(index + 1) * CHUNK_CHARACTERS]},
                ensure_ascii=True, separators=(",", ":")))
        print("OFFLINE_IMAGE_REVIEW_COMPLETE " + json.dumps(record, sort_keys=True, separators=(",", ":")))
        return record
    finally:
        inputs.close()


def main(argv=None):
    try:
        args = sys.argv[1:] if argv is None else argv
        require(len(args) == 3)
        emit(args[0], Path(args[1]), args[2])
    except (Exception, KeyboardInterrupt):
        print(FAILURE, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
