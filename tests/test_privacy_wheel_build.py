"""Source-bound wheel metadata, interpreter and offline-build behavior."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import tempfile
import tomllib
import unittest
from unittest import mock
from zipfile import ZipFile

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

    def test_source_metadata_and_notice_are_bound_to_python_3152(self):
        for name in ("presidio_analyzer-2.2.366", "presidio_anonymizer-2.2.366"):
            with self.subTest(name=name):
                source = self.source(name)
                BUILDER.patch_presidio(source)
                metadata = self.metadata(source)
                self.assertEqual(metadata["version"], "2.2.366+python315.2")
                self.assertEqual(metadata["requires-python"], "==3.15.2")
                self.assertEqual((source / "LICENSE").read_bytes(), BUILDER.PRESIDIO_NOTICE.read_bytes())
                if name.startswith("presidio_analyzer"):
                    self.assertEqual(metadata["dependencies"], ["numpy (==2.5.4)", "preshed (==3.0.15)"])

    def test_unexpected_metadata_and_notice_symlink_fail_closed(self):
        source = self.source("presidio_analyzer-2.2.366")
        (source / "pyproject.toml").write_text(PROJECT.replace("2.2.366", "2.2.999"))
        with self.assertRaisesRegex(ValueError, "Unexpected upstream metadata"):
            BUILDER.patch_presidio(source)
        (source / "pyproject.toml").write_text(PROJECT)
        (source / "LICENSE").symlink_to(BUILDER.PRESIDIO_NOTICE)
        with self.assertRaisesRegex(ValueError, "Unexpected Presidio MIT notice"):
            BUILDER.patch_presidio(source)
        self.assertEqual((source / "pyproject.toml").read_text(), PROJECT)

    def test_build_rejects_unqualified_interpreters_before_acquisition(self):
        for version in ((3, 15, 1), (3, 15, 3)):
            with self.subTest(version=version), mock.patch.object(
                BUILDER.sys, "version_info", version
            ), mock.patch.object(BUILDER.shutil, "which") as which:
                with self.assertRaisesRegex(RuntimeError, "requires Python 3.15.2"):
                    BUILDER.build(self.root / "wheels")
                which.assert_not_called()
        self.assertFalse((self.root / "wheels").exists())

    def test_build_uses_offline_tools_and_verifies_both_wheel_notices(self):
        metadata = []
        destination = self.root / "wheels"

        def build_command(command, **kwargs):
            source = Path(command[-1])
            if source.name.startswith("presidio_"):
                metadata.append(self.metadata(source))
                package = source.name.removesuffix("-2.2.366")
                (destination / f"{package}-2.2.366+python315.2-py3-none-any.whl").touch()
            self.assertIn("--offline", command)
            self.assertIn("--no-index", command)
            self.assertTrue(kwargs["check"])

        with mock.patch.object(BUILDER.sys, "version_info", (3, 15, 2)), \
                mock.patch.object(BUILDER.shutil, "which", return_value="uv"), \
                mock.patch.object(BUILDER, "verified_source", side_effect=self.source), \
                mock.patch.object(BUILDER, "verify_presidio_notice") as verify, \
                mock.patch.object(BUILDER.subprocess, "run", side_effect=build_command) as run:
            BUILDER.build(destination)
        self.assertEqual(run.call_count, 3)
        self.assertEqual(verify.call_count, 2)
        self.assertEqual(len(metadata), 2)
        self.assertTrue(all(item["version"] == "2.2.366+python315.2" for item in metadata))
        self.assertTrue(all(item["requires-python"] == "==3.15.2" for item in metadata))

    def test_wheel_notice_must_match_the_upstream_bytes(self):
        wheel = self.root / "synthetic.whl"
        notice_path = "synthetic-1.0.dist-info/licenses/LICENSE"
        with ZipFile(wheel, "w") as archive:
            archive.writestr(notice_path, BUILDER.PRESIDIO_NOTICE.read_bytes())
        BUILDER.verify_presidio_notice(wheel)
        with ZipFile(wheel, "w") as archive:
            archive.writestr(notice_path, b"changed notice")
        with self.assertRaisesRegex(ValueError, "missing the verified MIT notice"):
            BUILDER.verify_presidio_notice(wheel)

    def test_cli_passes_the_selected_destination(self):
        with mock.patch.object(BUILDER.sys, "argv", [str(SOURCE), "--destination", str(self.root / "wheels")]), \
                mock.patch.object(BUILDER, "build") as build:
            BUILDER.main()
        build.assert_called_once_with((self.root / "wheels").resolve())


if __name__ == "__main__":
    unittest.main()
