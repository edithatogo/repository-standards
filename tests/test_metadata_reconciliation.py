"""Distinct #102/#107 cases supplement, rather than replace, existing metadata tests."""
from __future__ import annotations

import unittest

import audit_repository_product_metadata as audit


class MetadataReconciliationTests(unittest.TestCase):
    def test_additional_software_markers(self):
        for marker in ("package.json", "go.mod"):
            with self.subTest(marker=marker):
                self.assertEqual(audit.archetype({marker}, ""), "software")

    def test_dynamic_build_system_requirement(self):
        state = audit.version_state(
            {"pyproject.toml": 'dynamic = ["version"]\nrequires = ["hatch-vcs"]'},
            "software",
        )
        self.assertEqual(state["source"], "git_tags_dynamic")
        self.assertIsNone(state["manifest_version"])
        self.assertTrue(state["dynamic"])

    def test_quoted_citation_agreement_and_drift(self):
        for citation, drift in (("1.0.0", False), ("1.0.1", True)):
            with self.subTest(citation=citation):
                state = audit.version_state(
                    {"pyproject.toml": 'version = "1.0.0"',
                     "citation.cff": f'version: "{citation}"'}, "software"
                )
                self.assertEqual(state["citation_version"], citation)
                self.assertEqual(state["drift"], drift)

    def test_realistic_badge_urls(self):
        cases = {
            "ci": "![CI](https://github.com/owner/repo/actions/workflows/main.yml/badge.svg)",
            "coverage": "[![codecov](https://codecov.io/gh/owner/repo/branch/main/graph/badge.svg)](https://codecov.io/gh/owner/repo)",
            "license": "![License](https://img.shields.io/badge/license-MIT-blue.svg)",
            "citation": "[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.1234.svg)](https://doi.org/10.5281/zenodo.1234)",
            "version": "![PyPI](https://img.shields.io/pypi/v/release-name.svg)",
        }
        for kind, readme in cases.items():
            with self.subTest(kind=kind):
                result = audit.badge_state(readme)
                self.assertEqual(result["count"], 1)
                self.assertTrue(result[kind])

    def test_multiple_badges_keep_category_flags(self):
        result = audit.badge_state(
            "![CI](https://github.com/owner/repo/actions/workflows/main.yml/badge.svg)\n"
            "[![codecov](https://codecov.io/gh/owner/repo/branch/main/graph/badge.svg)](https://codecov.io/gh/owner/repo)"
        )
        self.assertEqual(result["count"], 2)
        self.assertTrue(result["ci"])
        self.assertTrue(result["coverage"])
        self.assertFalse(result["license"])

    def test_keywords_without_images_do_not_count_as_badges(self):
        result = audit.badge_state(
            "This repo uses /actions/workflows/ and /badge.svg and codecov for coverage, "
            "/license-mit, citation.cff, and version-1."
        )
        self.assertEqual(result["count"], 0)
        for kind in ("ci", "coverage", "license", "citation", "version"):
            self.assertTrue(result[kind])

    def test_markdown_summary_and_findings(self):
        rows = [{
            "repository": "owner/repo", "url": "https://github.com/owner/repo",
            "archetype": "software", "readme": {"path": "README.md"},
            "description": "desc", "topics": ["topic"], "license": {"present": True},
            "citation": {"warranted": True, "present": False}, "versioning": {"drift": True},
            "logging": {"warranted": True, "detected": False}, "gaps": ["gap1", "gap2"],
        }]
        result = audit.markdown(rows, "test-scope")
        for expected in (
            "# Repository product-metadata audit", "Scope: **test-scope**",
            "Active, non-fork, non-archived repositories: **1**",
            "- Citation warranted but absent: **1**", "- Version drift detected: **1**",
            "- Logging warranted but not detected: **1**",
            "| [owner/repo](https://github.com/owner/repo) | software | 2 |",
        ):
            self.assertIn(expected, result)

    def test_empty_markdown_summary(self):
        result = audit.markdown([], "empty-fixture")
        self.assertIn("Active, non-fork, non-archived repositories: **0**", result)
        self.assertIn("- Version drift detected: **0**", result)
        self.assertIn("| Repository | Archetype | Gaps |", result)


if __name__ == "__main__":
    unittest.main()
