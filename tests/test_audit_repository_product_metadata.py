import sys
from pathlib import Path

# Add scripts directory to path to allow importing the module under test
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

import unittest
import audit_repository_product_metadata as audit


class ArchetypeTests(unittest.TestCase):
    def test_typesetting_typst_toml(self) -> None:
        self.assertEqual(audit.archetype({"typst.toml"}, ""), "typesetting")

    def test_typesetting_typ_extension(self) -> None:
        self.assertEqual(audit.archetype({"document.typ"}, ""), "typesetting")

    def test_typesetting_tex_extension(self) -> None:
        self.assertEqual(audit.archetype({"paper.tex"}, ""), "typesetting")

    def test_documentation_mkdocs(self) -> None:
        self.assertEqual(audit.archetype({"mkdocs.yml", "README.md"}, ""), "documentation")

    def test_documentation_docs_folder(self) -> None:
        self.assertEqual(audit.archetype({"docs/index.md", "README.md"}, ""), "documentation")

    def test_documentation_overridden_by_executable(self) -> None:
        self.assertEqual(audit.archetype({"mkdocs.yml", "package.json"}, ""), "software")
        self.assertEqual(audit.archetype({"docs/index.md", "pyproject.toml"}, ""), "software")

    def test_data_dataset_description(self) -> None:
        self.assertEqual(audit.archetype({"data/raw.csv"}, "A dataset of things"), "data")

    def test_data_corpus_description(self) -> None:
        self.assertEqual(audit.archetype({"data/text.txt"}, "Text corpus"), "data")

    def test_data_folder_without_keyword_description(self) -> None:
        self.assertEqual(audit.archetype({"data/config.json"}, "Just some configuration files"), "documentation")
        self.assertEqual(audit.archetype({"data/config.json", "setup.py"}, "Just some configuration files"), "software")

    def test_software_executable_marker(self) -> None:
        self.assertEqual(audit.archetype({"pyproject.toml", "src/main.py"}, "A python tool"), "software")
        self.assertEqual(audit.archetype({"cargo.toml"}, "A rust tool"), "software")

    def test_default_documentation(self) -> None:
        self.assertEqual(audit.archetype({"README.md", "LICENSE", "scripts/script.sh"}, "A simple script"), "documentation")
        self.assertEqual(audit.archetype(set(), ""), "documentation")


if __name__ == "__main__":
    unittest.main()
