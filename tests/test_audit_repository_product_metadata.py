#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import unittest
import audit_repository_product_metadata as audit

class TestBadgeState(unittest.TestCase):
    def test_empty_string(self) -> None:
        result = audit.badge_state("")
        self.assertEqual(result["count"], 0)
        self.assertFalse(result["ci"])
        self.assertFalse(result["coverage"])
        self.assertFalse(result["license"])
        self.assertFalse(result["citation"])
        self.assertFalse(result["version"])

    def test_ci_badge(self) -> None:
        readme = "![CI](https://github.com/owner/repo/actions/workflows/main.yml/badge.svg)"
        result = audit.badge_state(readme)
        self.assertEqual(result["count"], 1)
        self.assertTrue(result["ci"])

    def test_coverage_badge(self) -> None:
        readme = "[![codecov](https://codecov.io/gh/owner/repo/branch/main/graph/badge.svg)](https://codecov.io/gh/owner/repo)"
        result = audit.badge_state(readme)
        self.assertEqual(result["count"], 1)
        self.assertTrue(result["coverage"])

    def test_license_badge(self) -> None:
        readme = "![License](https://img.shields.io/badge/license-MIT-blue.svg)"
        result = audit.badge_state(readme)
        self.assertEqual(result["count"], 1)
        self.assertTrue(result["license"])

    def test_citation_badge(self) -> None:
        readme = "[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.1234.svg)](https://doi.org/10.5281/zenodo.1234)"
        result = audit.badge_state(readme)
        self.assertEqual(result["count"], 1)
        self.assertTrue(result["citation"])

    def test_version_badge(self) -> None:
        readme = "![PyPI](https://img.shields.io/pypi/v/release-name.svg)"
        result = audit.badge_state(readme)
        self.assertEqual(result["count"], 1)
        self.assertTrue(result["version"])

    def test_multiple_badges(self) -> None:
        readme = """
        ![CI](https://github.com/owner/repo/actions/workflows/main.yml/badge.svg)
        [![codecov](https://codecov.io/gh/owner/repo/branch/main/graph/badge.svg)](https://codecov.io/gh/owner/repo)
        """
        result = audit.badge_state(readme)
        self.assertEqual(result["count"], 2)
        self.assertTrue(result["ci"])
        self.assertTrue(result["coverage"])
        self.assertFalse(result["license"])

    def test_text_not_badge(self) -> None:
        readme = "This repo uses /actions/workflows/ and /badge.svg and codecov for coverage, /license-mit, citation.cff, and version-1."
        result = audit.badge_state(readme)
        self.assertEqual(result["count"], 0)
        self.assertTrue(result["ci"])
        self.assertTrue(result["coverage"])
        self.assertTrue(result["license"])
        self.assertTrue(result["citation"])
        self.assertTrue(result["version"])

if __name__ == "__main__":
    unittest.main()
