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

    def test_presidio_metadata_matches_the_required_runtime(self):
        for name in ("presidio_analyzer-2.2.366", "presidio_anonymizer-2.2.366"):
            with self.subTest(name=name):
                source = self.source(name)
                BUILDER.patch_presidio(source)
                metadata = self.metadata(source)
                self.assertEqual(metadata["version"], "2.2.366+python315.2")
                self.assertEqual(metadata["requires-python"], "==3.15.2")
                self.assertEqual(
                    (source / "LICENSE").read_bytes(), BUILDER.PRESIDIO_NOTICE.read_bytes()
                )
                if name.startswith("presidio_analyzer"):
                    self.assertEqual(
                        metadata["dependencies"],
                        ["numpy (==2.5.4)", "preshed (==3.0.15)"],
                    )

    def test_build_rejects_wrong_patch_before_tools_or_downloads(self):
        for actual in ((3, 15, 1), (3, 15, 3)):
            with (
                self.subTest(actual=actual),
                mock.patch.object(BUILDER.sys, "version_info", actual),
                mock.patch.object(BUILDER.shutil, "which") as which,
            ):
                with self.assertRaisesRegex(RuntimeError, "requires Python 3.15.2"):
                    BUILDER.build(self.root / "wheels")
                which.assert_not_called()
        self.assertFalse((self.root / "wheels").exists())


if __name__ == "__main__":
    unittest.main()
