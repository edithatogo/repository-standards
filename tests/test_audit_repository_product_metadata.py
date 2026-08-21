import unittest
from scripts import audit_repository_product_metadata as audit

class TestAuditProductMetadata(unittest.TestCase):
    def test_archetype_typesetting(self):
        self.assertEqual(audit.archetype({'typst.toml'}, ""), "typesetting")
        self.assertEqual(audit.archetype({'document.tex'}, ""), "typesetting")

    def test_archetype_documentation(self):
        self.assertEqual(audit.archetype({'docs/index.md'}, ""), "documentation")
        self.assertEqual(audit.archetype({'mkdocs.yml'}, ""), "documentation")
        self.assertEqual(audit.archetype({'README.md'}, ""), "documentation")

    def test_archetype_data(self):
        self.assertEqual(audit.archetype({'data/raw.csv'}, "A corpus of data"), "data")
        self.assertEqual(audit.archetype({'data/processed.json'}, "This dataset contains ..."), "data")

    def test_archetype_software(self):
        self.assertEqual(audit.archetype({'pyproject.toml'}, ""), "software")
        self.assertEqual(audit.archetype({'package.json'}, ""), "software")
        self.assertEqual(audit.archetype({'go.mod'}, ""), "software")

    def test_badge_state(self):
        readme = "![badge](https://example.com/badge) actions/workflows codecov license- citation.cff version-"
        state = audit.badge_state(readme)
        self.assertEqual(state["count"], 1)
        self.assertTrue(state["ci"])
        self.assertTrue(state["coverage"])
        self.assertTrue(state["license"])
        self.assertTrue(state["citation"])
        self.assertTrue(state["version"])

    def test_badge_state_empty(self):
        state = audit.badge_state("")
        self.assertEqual(state["count"], 0)
        self.assertFalse(state["ci"])
        self.assertFalse(state["coverage"])
        self.assertFalse(state["license"])
        self.assertFalse(state["citation"])
        self.assertFalse(state["version"])

    def test_version_state_pyproject(self):
        files = {"pyproject.toml": 'version = "1.2.3"'}
        state = audit.version_state(files, "software")
        self.assertEqual(state["source"], "pyproject_manifest")
        self.assertEqual(state["manifest_version"], "1.2.3")
        self.assertFalse(state["dynamic"])

    def test_version_state_pyproject_dynamic(self):
        files = {"pyproject.toml": 'dynamic = ["version"]\nrequires = ["hatch-vcs"]'}
        state = audit.version_state(files, "software")
        self.assertEqual(state["source"], "git_tags_dynamic")
        self.assertIsNone(state["manifest_version"])
        self.assertTrue(state["dynamic"])

    def test_version_state_cargo(self):
        files = {"cargo.toml": 'version = "0.1.0"'}
        state = audit.version_state(files, "software")
        self.assertEqual(state["source"], "cargo_manifest")
        self.assertEqual(state["manifest_version"], "0.1.0")

    def test_version_state_package_json(self):
        files = {"package.json": '{"version": "2.0.0"}'}
        state = audit.version_state(files, "software")
        self.assertEqual(state["source"], "package_manifest")
        self.assertEqual(state["manifest_version"], "2.0.0")

    def test_version_state_typst(self):
        files = {"typst.toml": 'version = "1.0.0"'}
        state = audit.version_state(files, "typesetting")
        self.assertEqual(state["source"], "typst_manifest")
        self.assertEqual(state["manifest_version"], "1.0.0")

    def test_version_state_fallback(self):
        files = {}
        state = audit.version_state(files, "documentation")
        self.assertEqual(state["source"], "release_tags_or_doi")

        state = audit.version_state(files, "software")
        self.assertEqual(state["source"], "not_applicable")

    def test_version_state_citation_and_drift(self):
        files = {
            "pyproject.toml": 'version = "1.0.0"',
            "citation.cff": 'version: "1.0.0"'
        }
        state = audit.version_state(files, "software")
        self.assertEqual(state["citation_version"], "1.0.0")
        self.assertFalse(state["drift"])

        files["citation.cff"] = 'version: "1.0.1"'
        state = audit.version_state(files, "software")
        self.assertTrue(state["drift"])

    def test_markdown(self):
        rows = [
            {
                "repository": "owner/repo",
                "url": "https://github.com/owner/repo",
                "archetype": "software",
                "readme": {"path": "README.md"},
                "description": "desc",
                "topics": ["topic"],
                "license": {"present": True},
                "citation": {"warranted": True, "present": False},
                "versioning": {"drift": True},
                "logging": {"warranted": True, "detected": False},
                "gaps": ["gap1", "gap2"]
            }
        ]
        result = audit.markdown(rows, "test-scope")
        self.assertIn("# Repository product-metadata audit", result)
        self.assertIn("Scope: **test-scope**", result)
        self.assertIn("Active, non-fork, non-archived repositories: **1**", result)
        self.assertIn("- Citation warranted but absent: **1**", result)
        self.assertIn("- Version drift detected: **1**", result)
        self.assertIn("- Logging warranted but not detected: **1**", result)
        self.assertIn("| [owner/repo](https://github.com/owner/repo) | software | 2 |", result)

if __name__ == '__main__':
    unittest.main()
