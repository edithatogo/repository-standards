"""Version-state regression cases, separate from badge and archetype tests."""
from __future__ import annotations

import unittest

import audit_repository_product_metadata as audit


class VersionStateTests(unittest.TestCase):
    def test_version_state_empty(self) -> None:
        result = audit.version_state({}, "software")
        self.assertEqual(result["source"], "not_applicable")
        self.assertFalse(result["dynamic"])
        self.assertIsNone(result["manifest_version"])
        self.assertIsNone(result["citation_version"])
        self.assertFalse(result["drift"])

    def test_version_state_pyproject_static(self) -> None:
        files = {"pyproject.toml": 'version = "1.2.3"'}
        result = audit.version_state(files, "software")
        self.assertEqual(result["source"], "pyproject_manifest")
        self.assertFalse(result["dynamic"])
        self.assertEqual(result["manifest_version"], "1.2.3")
        self.assertIsNone(result["citation_version"])
        self.assertFalse(result["drift"])

    def test_version_state_pyproject_dynamic(self) -> None:
        files = {"pyproject.toml": 'dynamic = ["version"]\nhatch-vcs = {}'}
        result = audit.version_state(files, "software")
        self.assertEqual(result["source"], "git_tags_dynamic")
        self.assertTrue(result["dynamic"])
        self.assertIsNone(result["manifest_version"])

    def test_version_state_cargo(self) -> None:
        result = audit.version_state({"cargo.toml": 'version = "2.0.0"'}, "software")
        self.assertEqual(result["source"], "cargo_manifest")
        self.assertEqual(result["manifest_version"], "2.0.0")

    def test_version_state_package_json(self) -> None:
        result = audit.version_state({"package.json": '{"version": "3.1.4"}'}, "software")
        self.assertEqual(result["source"], "package_manifest")
        self.assertEqual(result["manifest_version"], "3.1.4")

    def test_version_state_package_json_invalid(self) -> None:
        files = {"package.json": '{"version": "3.1.4", invalid json}'}
        result = audit.version_state(files, "software")
        self.assertEqual(result["source"], "package_manifest")
        self.assertIsNone(result["manifest_version"])

    def test_version_state_typst(self) -> None:
        result = audit.version_state({"typst.toml": 'version = "0.1.0"'}, "typesetting")
        self.assertEqual(result["source"], "typst_manifest")
        self.assertEqual(result["manifest_version"], "0.1.0")

    def test_version_state_citation_match(self) -> None:
        files = {
            "pyproject.toml": 'version = "1.0.0"',
            "citation.cff": 'version: 1.0.0',
        }
        result = audit.version_state(files, "software")
        self.assertEqual(result["manifest_version"], "1.0.0")
        self.assertEqual(result["citation_version"], "1.0.0")
        self.assertFalse(result["drift"])

    def test_version_state_citation_drift(self) -> None:
        files = {
            "pyproject.toml": 'version = "1.0.0"',
            "citation.cff": 'version: 2.0.0',
        }
        result = audit.version_state(files, "software")
        self.assertEqual(result["manifest_version"], "1.0.0")
        self.assertEqual(result["citation_version"], "2.0.0")
        self.assertTrue(result["drift"])

    def test_version_state_nonsoftware_fallback(self) -> None:
        for kind in ("documentation", "typesetting", "data"):
            with self.subTest(kind=kind):
                self.assertEqual(
                    audit.version_state({}, kind)["source"], "release_tags_or_doi"
                )


if __name__ == "__main__":
    unittest.main()
