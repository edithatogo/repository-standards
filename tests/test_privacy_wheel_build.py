"""Exact compatibility metadata and runtime selection for source-built wheels."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import tempfile
import tomllib
import unittest
from unittest import mock


SOURCE = Path(__file__).resolve().parents[1] / "scripts/build_privacy_wheels.py"
SPEC = importlib.util.spec_from_file_location("privacy_wheel_builder", SOURCE)
BUILDER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BUILDER)

PROJECT = '''[project]
name = "synthetic-presidio"
version = "2.2.366"
requires-python = ">=3.11,<3.15"
dependencies = ["numpy (>=1.19.0,<2.5.0)", "preshed (<3.0.14)"]
'''


class PrivacyWheelBuildTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="privacy-wheel-metadata-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def source(self, name, directory=None):
        source = (directory or self.root) / name
        source.mkdir()
        (source / "pyproject.toml").write_text(PROJECT)
        return source

    def metadata(self, source):
        return tomllib.loads((source / "pyproject.toml").read_text())["project"]

    def test_default_preserves_the_shared_privacy_build_metadata(self):
        source = self.source("presidio_analyzer-2.2.366")
        BUILDER.patch_presidio(source)
        metadata = self.metadata(source)
        self.assertEqual(metadata["version"], "2.2.366+python315.1")
        self.assertEqual(metadata["requires-python"], "==3.15.1")
        self.assertEqual(metadata["dependencies"], ["numpy (==2.5.4)", "preshed (==3.0.15)"])

    def test_explicit_patch_has_distinct_version_and_exact_python_metadata(self):
        for name in ("presidio_analyzer-2.2.366", "presidio_anonymizer-2.2.366"):
            with self.subTest(name=name):
                source = self.source(name)
                BUILDER.patch_presidio(source, (3, 15, 2))
                metadata = self.metadata(source)
                self.assertEqual(metadata["version"], "2.2.366+python315.2")
                self.assertEqual(metadata["requires-python"], "==3.15.2")

    def test_unsupported_patch_cannot_change_source_metadata(self):
        source = self.source("presidio_analyzer-2.2.366")
        with self.assertRaisesRegex(ValueError, "Unsupported privacy wheel Python version"):
            BUILDER.patch_presidio(source, (3, 15, 3))
        self.assertEqual((source / "pyproject.toml").read_text(), PROJECT)

    def test_build_requires_the_selected_interpreter_before_tools_or_downloads(self):
        for requested, actual in (((3, 15, 1), (3, 15, 2)),
                                  ((3, 15, 2), (3, 15, 1)),
                                  ((3, 15, 2), (3, 15, 3))):
            with self.subTest(requested=requested, actual=actual), mock.patch.object(
                    BUILDER.sys, "version_info", actual), mock.patch.object(BUILDER.shutil, "which") as which:
                with self.assertRaisesRegex(RuntimeError, "requires Python"):
                    BUILDER.build(self.root / "wheels", requested)
                which.assert_not_called()
        self.assertFalse((self.root / "wheels").exists())

    def test_build_applies_selected_metadata_to_both_presidio_wheels(self):
        metadata = []
        def build_command(command, **kwargs):
            source = Path(command[-1])
            if source.name.startswith("presidio_"):
                metadata.append(self.metadata(source))
            self.assertIn("--offline", command)
            self.assertIn("--no-index", command)
            self.assertTrue(kwargs["check"])
        with mock.patch.object(BUILDER.sys, "version_info", (3, 15, 2)), \
                mock.patch.object(BUILDER.shutil, "which", return_value="uv"), \
                mock.patch.object(BUILDER, "verified_source", side_effect=self.source), \
                mock.patch.object(BUILDER.subprocess, "run", side_effect=build_command) as command:
            BUILDER.build(self.root / "wheels", (3, 15, 2))
        self.assertEqual(command.call_count, 3)
        self.assertEqual(len(metadata), 2)
        self.assertTrue(all(item["version"] == "2.2.366+python315.2" for item in metadata))
        self.assertTrue(all(item["requires-python"] == "==3.15.2" for item in metadata))

    def test_cli_preserves_default_and_passes_explicit_patch_selection(self):
        for extra, expected in (([], (3, 15, 1)), (["--python-version", "3.15.2"], (3, 15, 2))):
            with self.subTest(extra=extra), mock.patch.object(
                    BUILDER.sys, "argv", [str(SOURCE), "--destination", str(self.root / "wheels"), *extra]), \
                    mock.patch.object(BUILDER, "build") as build:
                BUILDER.main()
                build.assert_called_once_with((self.root / "wheels").resolve(), expected)


if __name__ == "__main__":
    unittest.main()
