"""Negative controls for release vulnerability evidence (no network required)."""
import copy
import datetime as dt
import json
import tempfile
import unittest
from pathlib import Path

import grype_scan as scan


def bom(version="2.14.1"):
    return {"bomFormat": "CycloneDX", "specVersion": "1.6", "version": 1,
            "components": [{"type": "library", "name": "log4j-core", "version": version,
                            "purl": f"pkg:maven/org.apache.logging.log4j/log4j-core@{version}"}]}


def report(severity=None):
    return {"matches": [] if severity is None else [{"vulnerability": {"id": "CVE-fixture", "severity": severity},
                                                    "artifact": {"name": "example", "version": "1.0"}}],
            "ignoredMatches": [], "descriptor": {"name": "grype", "version": scan.TOOLS["grype"]["version"]}}


class InventoryTests(unittest.TestCase):
    def test_resolved_inventory_and_metadata_only_rejection(self):
        self.assertEqual(scan.inventory_count(bom()), 1)
        with self.assertRaises(ValueError):
            scan.inventory_count({"bomFormat": "CycloneDX", "metadata": {"component": {"name": "project"}}})

    def test_range_and_placeholder_versions_are_rejected(self):
        for value in ("^2.14", ">=2.14", "2.*", "[2,3)", "NOASSERTION", "unknown", ""):
            with self.subTest(version=value), self.assertRaises(ValueError):
                scan.inventory_count(bom(value))

    def test_missing_package_identity_is_not_counted(self):
        value = bom()
        del value["components"][0]["purl"]
        with self.assertRaises(ValueError):
            scan.inventory_count(value)

    def test_spdx_byte_inventory_is_not_dependency_inventory(self):
        value = {"spdxVersion": "SPDX-2.3", "packages": [{"name": "archive.zip", "versionInfo": "1.0"}]}
        with self.assertRaises(ValueError):
            scan.inventory_count(value)
        value["packages"][0]["externalRefs"] = [{"referenceType": "purl", "referenceLocator": "pkg:pypi/example@1.0"}]
        self.assertEqual(scan.inventory_count(value), 1)

    def test_syft_inventory_empty_and_valid(self):
        with self.assertRaises(ValueError):
            scan.inventory_count({"artifacts": [], "schema": {"version": "16.0.0"}})
        self.assertEqual(scan.inventory_count({"artifacts": bom()["components"], "schema": {"version": "16.0.0"}}), 1)


class PolicyTests(unittest.TestCase):
    def test_clean_and_nonblocking_severity(self):
        self.assertEqual(scan.evaluate(report(), 0, "critical", "enforce")["outcome"], "pass")
        self.assertEqual(scan.evaluate(report("High"), 0, "critical", "enforce")["outcome"], "findings")

    def test_critical_is_blocked_or_advisory_but_not_clean(self):
        self.assertEqual(scan.evaluate(report("Critical"), 2, "critical", "enforce")["outcome"], "blocked")
        self.assertEqual(scan.evaluate(report("Critical"), 2, "critical", "advisory")["outcome"], "findings")

    def test_operational_error_is_not_advisory_success(self):
        for mode in ("advisory", "enforce"):
            with self.subTest(mode=mode), self.assertRaises(ValueError):
                scan.evaluate(report(), 1, "critical", mode)

    def test_inconsistent_exit_or_missing_matches_fail(self):
        for value, exit_code in ((report(), 2), (report("Critical"), 0), ({}, 0)):
            with self.subTest(value=value), self.assertRaises(ValueError):
                scan.evaluate(value, exit_code, "critical", "advisory")

    def test_suppressions_cannot_silently_bypass_gate(self):
        value = report()
        value["ignoredMatches"] = report("Critical")["matches"]
        with self.assertRaises(ValueError):
            scan.evaluate(value, 0, "critical", "enforce")

    def test_unknown_severity_is_retained(self):
        result = scan.evaluate(report("Unknown"), 0, "critical", "advisory")
        self.assertEqual(result["severities"]["unknown"], 1)
        self.assertEqual(result["outcome"], "findings")


class BoundaryTests(unittest.TestCase):
    def test_only_digest_image_references(self):
        self.assertEqual(scan.image_reference("ghcr.io/example/tool@sha256:" + "a" * 64), "ghcr.io/example/tool@sha256:" + "a" * 64)
        for ref in ("ghcr.io/example/tool:latest", "registry:ghcr.io/example/tool@sha256:" + "a" * 64, "https://user:pass@registry/x"):
            with self.subTest(ref=ref), self.assertRaises(ValueError):
                scan.image_reference(ref)

    def test_stale_future_and_invalid_databases(self):
        now = dt.datetime(2026, 11, 20, tzinfo=dt.timezone.utc)
        self.assertEqual(scan.validate_database({"built": "2026-11-19T00:00:00Z", "valid": True}, now), 24.0)
        for value in ({"built": "2026-11-01T00:00:00Z", "valid": True},
                      {"built": "2026-11-21T00:00:00Z", "valid": True},
                      {"built": "2026-11-19T00:00:00Z", "valid": False}, {}):
            with self.subTest(value=value), self.assertRaises(ValueError):
                scan.validate_database(value, now)

    def test_existing_evidence_cannot_be_reused(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "scan"
            scan.prepare_directory(output)
            (output / "report.json").write_text("old report")
            with self.assertRaises(ValueError):
                scan.prepare_directory(output)

    def test_repository_scanner_environment_does_not_override_policy(self):
        env = scan.scanner_environment({"PATH": "/bin", "HOME": "/home/runner", "DOCKER_CONFIG": "/auth",
                                        "GRYPE_ONLY_FIXED": "true", "SYFT_EXCLUDE": "**", "GRYPE_DB_VALIDATE_AGE": "false"})
        self.assertEqual(env["DOCKER_CONFIG"], "/auth")
        self.assertNotIn("GRYPE_ONLY_FIXED", env)
        self.assertNotIn("SYFT_EXCLUDE", env)


if __name__ == "__main__":
    unittest.main()
