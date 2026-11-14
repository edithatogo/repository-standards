from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import rust_dependency_inventory as inventory


class RustDependencyInventoryTests(unittest.TestCase):
    def test_reports_explicit_and_inherited_dependencies_in_nested_workspace(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "rust" / "crates" / "app").mkdir(parents=True)
            (root / "rust" / "Cargo.toml").write_text(
                '[workspace]\nmembers = ["crates/app"]\n'
                '[workspace.dependencies]\nserde = "1"\ntokio = { version = "1", features = ["full"] }\n',
                encoding="utf-8",
            )
            (root / "rust" / "crates" / "app" / "Cargo.toml").write_text(
                '[package]\nname = "app"\nversion = "0.1.0"\n'
                '[dependencies]\nserde.workspace = true\ntokio = { workspace = true }\n'
                '[dev-dependencies]\nproptest = "1"\n', encoding="utf-8",
            )
            report = inventory.inventory(root)
            self.assertEqual(report["manifest_count"], 2)
            items = [item for item in report["declarations"] if item["crate"] == "app"]
            self.assertEqual({item["name"] for item in items}, {"serde", "tokio", "proptest"})
            inherited = next(item for item in items if item["name"] == "serde")
            self.assertTrue(inherited["workspace_inherited"])
            self.assertEqual(inherited["version"], None)
            tokio = next(item for item in items if item["name"] == "tokio")
            self.assertEqual(tokio["features"], [])
            self.assertEqual(report["notes"][0], "Manifest declarations are not a resolved Cargo dependency graph.")

    def test_does_not_mistake_other_dependencies_for_the_21_candidates(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "Cargo.toml").write_text(
                '[package]\nname = "core"\nversion = "0.1.0"\n'
                '[dependencies]\nmail-parser = "1"\nserde = "1"\n', encoding="utf-8",
            )
            report = inventory.inventory(root)
            self.assertEqual([item["name"] for item in report["declarations"]], ["serde"])

    def test_reports_invalid_toml_with_path_not_contents(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "Cargo.toml").write_text('secret="no"\n[invalid\n', encoding="utf-8")
            report = inventory.inventory(root)
            self.assertEqual(len(report["errors"]), 1)
            self.assertEqual(report["errors"][0]["path"], "Cargo.toml")
            self.assertNotIn("secret", str(report))

    def test_is_read_only_and_skips_build_directories(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "target").mkdir()
            (root / "target" / "Cargo.toml").write_text('[package]\nname="noise"\n')
            (root / "Cargo.toml").write_text('[package]\nname="real"\nversion="0.1.0"\n')
            before = (root / "Cargo.toml").read_bytes()
            report = inventory.inventory(root)
            self.assertEqual(report["manifest_count"], 1)
            self.assertEqual(before, (root / "Cargo.toml").read_bytes())


if __name__ == "__main__":
    unittest.main()
