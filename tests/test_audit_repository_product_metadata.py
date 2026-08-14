import unittest
import sys
from pathlib import Path

# Need to add scripts dir to path, since it's not a module
sys.path.append(str(Path(__file__).parent.parent / "scripts"))
import audit_repository_product_metadata as audit

class ArchetypeTests(unittest.TestCase):
    def test_typesetting_typst(self):
        self.assertEqual(audit.archetype({"typst.toml"}, ""), "typesetting")
        self.assertEqual(audit.archetype({"document.typ"}, ""), "typesetting")

    def test_typesetting_tex(self):
        self.assertEqual(audit.archetype({"main.tex"}, ""), "typesetting")

    def test_documentation_mkdocs_or_docs(self):
        self.assertEqual(audit.archetype({"mkdocs.yml"}, ""), "documentation")
        self.assertEqual(audit.archetype({"docs/index.md"}, ""), "documentation")

    def test_software_overrides_documentation(self):
        self.assertEqual(audit.archetype({"mkdocs.yml", "package.json"}, ""), "software")

    def test_data(self):
        self.assertEqual(audit.archetype({"data/records.csv"}, "a large dataset"), "data")
        self.assertEqual(audit.archetype({"data/records.csv"}, "text corpus for nlp"), "data")

    def test_data_requires_keywords(self):
        self.assertEqual(audit.archetype({"data/records.csv"}, "just some stuff"), "documentation")

    def test_data_without_data_folder_but_with_keywords(self):
        self.assertEqual(audit.archetype({"src/main.py"}, "dataset processing"), "documentation")

    def test_software_executable_markers(self):
        self.assertEqual(audit.archetype({"pyproject.toml"}, ""), "software")
        self.assertEqual(audit.archetype({"cargo.toml"}, ""), "software")

    def test_fallback_documentation(self):
        self.assertEqual(audit.archetype({"random.txt"}, ""), "documentation")
        self.assertEqual(audit.archetype(set(), ""), "documentation")

if __name__ == '__main__':
    unittest.main()
