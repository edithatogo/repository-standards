"""Verify the Presidio compatibility wheels preserve their upstream notice."""

import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from zipfile import ZipFile

import build_privacy_wheels as wheels


class PresidioLicenseTests(unittest.TestCase):
    def test_both_packages_receive_the_verified_upstream_notice(self):
        for name in ("presidio_analyzer", "presidio_anonymizer"):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temporary:
                source = Path(temporary) / f"{name}-2.2.366"
                source.mkdir()
                project = 'version = "2.2.366"\nrequires-python = ">=3.11,<3.15"\n'
                if name == "presidio_analyzer":
                    project += 'dependencies = ["numpy (>=1.19.0,<2.5.0)", "preshed (<3.0.14)"]\n'
                (source / "pyproject.toml").write_text(project, encoding="utf-8")
                wheels.patch_presidio(source)
                self.assertEqual(
                    hashlib.sha256((source / "LICENSE").read_bytes()).hexdigest(),
                    wheels.PRESIDIO_NOTICE_SHA256,
                )
                self.assertIn("==3.15.1", (source / "pyproject.toml").read_text())

    def test_altered_notice_fails_before_source_metadata_is_rewritten(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "presidio_anonymizer-2.2.366"
            source.mkdir()
            project = source / "pyproject.toml"
            original = 'version = "2.2.366"\nrequires-python = ">=3.11,<3.15"\n'
            project.write_text(original, encoding="utf-8")
            notice = root / "LICENSE"
            notice.write_text("altered", encoding="utf-8")
            with (
                patch.object(wheels, "PRESIDIO_NOTICE", notice),
                self.assertRaisesRegex(ValueError, "does not match"),
            ):
                wheels.patch_presidio(source)
            self.assertEqual(project.read_text(encoding="utf-8"), original)
            self.assertFalse((source / "LICENSE").exists())

    def test_wheel_notice_is_required_and_must_match(self):
        with tempfile.TemporaryDirectory() as temporary:
            wheel = Path(temporary) / "presidio.whl"
            for content, passes in (
                (None, False),
                (b"altered", False),
                (wheels.PRESIDIO_NOTICE.read_bytes(), True),
            ):
                with self.subTest(passes=passes, content=content is None):
                    with ZipFile(wheel, "w") as archive:
                        if content is not None:
                            archive.writestr(
                                "presidio.dist-info/licenses/LICENSE", content
                            )
                    if passes:
                        wheels.verify_presidio_notice(wheel)
                    else:
                        with self.assertRaisesRegex(ValueError, "MIT notice"):
                            wheels.verify_presidio_notice(wheel)

    def test_build_keeps_other_flags_and_sets_reproducible_inputs(self):
        with patch.dict("os.environ", {"CFLAGS": "-O2"}):
            environment = wheels.build_environment()
        self.assertEqual(
            environment["SOURCE_DATE_EPOCH"], str(wheels.SOURCE_DATE_EPOCH)
        )
        self.assertIn("-O2", environment["CFLAGS"])


if __name__ == "__main__":
    unittest.main()
