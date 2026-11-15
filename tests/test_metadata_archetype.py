"""Archetype coverage reconciled from PRs #79 and #83 without replacing badge tests."""
from __future__ import annotations

import unittest

import audit_repository_product_metadata as audit


class ArchetypeTests(unittest.TestCase):
    def test_typesetting_typst(self) -> None:
        self.assertEqual(audit.archetype({"typst.toml"}, ""), "typesetting")
        self.assertEqual(audit.archetype({"document.typ"}, ""), "typesetting")

    def test_typesetting_tex(self) -> None:
        self.assertEqual(audit.archetype({"main.tex"}, ""), "typesetting")

    def test_documentation_mkdocs_or_docs(self) -> None:
        for paths in (
            {"mkdocs.yml"},
            {"docs/index.md"},
            {"mkdocs.yml", "README.md"},
            {"docs/index.md", "README.md"},
        ):
            with self.subTest(paths=paths):
                self.assertEqual(audit.archetype(paths, ""), "documentation")

    def test_software_overrides_documentation(self) -> None:
        self.assertEqual(
            audit.archetype({"mkdocs.yml", "package.json"}, ""), "software"
        )
        self.assertEqual(
            audit.archetype({"docs/index.md", "pyproject.toml"}, ""), "software"
        )

    def test_data(self) -> None:
        for description in (
            "a large dataset", "text corpus for nlp", "A dataset of things", "Text corpus"
        ):
            with self.subTest(description=description):
                self.assertEqual(
                    audit.archetype({"data/records.csv"}, description), "data"
                )

    def test_data_requires_keywords(self) -> None:
        self.assertEqual(
            audit.archetype({"data/records.csv"}, "just some stuff"), "documentation"
        )
        self.assertEqual(
            audit.archetype({"data/config.json"}, "Just some configuration files"),
            "documentation",
        )
        self.assertEqual(
            audit.archetype(
                {"data/config.json", "setup.py"}, "Just some configuration files"
            ),
            "software",
        )

    def test_data_without_data_folder_but_with_keywords(self) -> None:
        self.assertEqual(
            audit.archetype({"src/main.py"}, "dataset processing"), "documentation"
        )

    def test_software_executable_markers(self) -> None:
        self.assertEqual(audit.archetype({"pyproject.toml"}, ""), "software")
        self.assertEqual(audit.archetype({"cargo.toml"}, ""), "software")
        self.assertEqual(
            audit.archetype({"pyproject.toml", "src/main.py"}, "A python tool"),
            "software",
        )

    def test_fallback_documentation(self) -> None:
        self.assertEqual(audit.archetype({"random.txt"}, ""), "documentation")
        self.assertEqual(audit.archetype(set(), ""), "documentation")
        self.assertEqual(
            audit.archetype({"README.md", "LICENSE", "scripts/script.sh"}, "A simple script"),
            "documentation",
        )


if __name__ == "__main__":
    unittest.main()
