"""Keep the source-built privacy guard bound to its qualified Python patch."""

import json
import os
import tempfile
import tomllib
import unittest
from pathlib import Path
from unittest.mock import patch
from zipfile import ZipFile

import build_privacy_wheels as wheels

ROOT = Path(__file__).resolve().parents[1]


class PrivacyRuntimeTests(unittest.TestCase):
    def test_analyzer_metadata_uses_qualified_patch_and_exact_dependencies(self):
        source = """[project]
version = "2.2.366"
requires-python = ">=3.11,<3.15"
dependencies = ["numpy (>=1.19.0,<2.5.0)", "preshed (<3.0.14)"]
"""
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary) / "presidio_analyzer-2.2.366"
            project.mkdir()
            (project / "pyproject.toml").write_text(source, encoding="utf-8")
            wheels.patch_presidio(project)
            self.assertEqual(
                (project / "LICENSE").read_bytes(),
                (ROOT / "privacy/licenses/presidio-MIT.txt").read_bytes(),
            )
            metadata = tomllib.loads((project / "pyproject.toml").read_text())[
                "project"
            ]
        self.assertEqual(wheels.PYTHON_VERSION, (3, 15, 2))
        self.assertEqual(metadata["version"], "2.2.366+python315.2")
        self.assertEqual(metadata["requires-python"], "==3.15.2")
        self.assertEqual(
            metadata["dependencies"], ["numpy (==2.5.4)", "preshed (==3.0.15)"]
        )

    def test_unexpected_upstream_metadata_fails_without_rewriting_it(self):
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary) / "presidio_analyzer-2.2.366"
            project.mkdir()
            manifest = project / "pyproject.toml"
            manifest.write_text('version = "unexpected"\n', encoding="utf-8")
            before = manifest.read_bytes()
            with self.assertRaisesRegex(ValueError, "Unexpected upstream metadata"):
                wheels.patch_presidio(project)
            self.assertEqual(manifest.read_bytes(), before)

    def test_build_rejects_an_unqualified_interpreter_before_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary) / "wheels"
            with (
                patch.object(wheels, "PYTHON_VERSION", (3, 15, 3)),
                self.assertRaisesRegex(RuntimeError, "requires Python 3.15.2"),
            ):
                wheels.build(destination)
            self.assertFalse(destination.exists())

    def test_built_wheel_must_retain_the_upstream_mit_notice(self):
        notice = (ROOT / "privacy/licenses/presidio-MIT.txt").read_bytes()
        with tempfile.TemporaryDirectory() as temporary:
            wheel = Path(temporary) / "presidio.whl"
            with ZipFile(wheel, "w") as archive:
                archive.writestr("presidio.dist-info/licenses/LICENSE", notice)
            wheels.verify_presidio_notice(wheel)
            with ZipFile(wheel, "w") as archive:
                archive.writestr("presidio.dist-info/licenses/LICENSE", b"modified")
            with self.assertRaisesRegex(ValueError, "MIT notice"):
                wheels.verify_presidio_notice(wheel)

    def test_build_environment_is_stable_and_preserves_existing_flags(self):
        with patch.dict(os.environ, {"CFLAGS": "-O2"}):
            environment = wheels.build_environment()
            self.assertEqual(
                environment["SOURCE_DATE_EPOCH"], str(wheels.SOURCE_DATE_EPOCH)
            )
            self.assertIn("-O2", environment["CFLAGS"])
            if os.name != "nt":
                self.assertIn("-g0", environment["CFLAGS"])
            self.assertEqual(os.environ["CFLAGS"], "-O2")

    def test_active_installer_and_action_select_the_same_patch(self):
        action = (ROOT / ".github/actions/privacy-secrets/action.yml").read_text()
        installer = (ROOT / "privacy/install.sh").read_text()
        requirements = (ROOT / "privacy/requirements.in").read_text()
        self.assertIn("python-version: '3.15.2'", action)
        self.assertIn("sys.version_info[:3] == (3, 15, 2)", installer)
        for component in ("analyzer", "anonymizer"):
            self.assertIn(f"presidio-{component}==2.2.366+python315.2", requirements)
            self.assertIn(f"presidio_{component}-2.2.366+python315.2-", installer)
        self.assertIn("--require-hashes --only-binary=:all:", installer)

    def test_self_scan_pins_the_qualified_action_commit(self):
        workflow = (ROOT / ".github/workflows/privacy-secrets.yml").read_text()
        template = (ROOT / "managed-files/templates/privacy-secrets.yml").read_text()
        manifest = json.loads((ROOT / "managed-files/manifest.json").read_text())
        pin = "b30b07bcdaa6aebad2c6a57a4d0adc3616dabfe4"
        self.assertIn(
            "uses: edithatogo/repository-standards/.github/actions/"
            f"privacy-secrets@{pin}",
            workflow,
        )
        self.assertIn("Python 3.15.2", workflow)
        self.assertEqual(workflow, template)
        entries = [
            item
            for item in manifest["files"]
            if item["path"] == ".github/workflows/privacy-secrets.yml"
        ]
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["upstream_commit"], pin)


if __name__ == "__main__":
    unittest.main()
