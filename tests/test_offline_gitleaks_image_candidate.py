"""Evidence-only Gitleaks staging controls; no candidate is release qualified."""
from __future__ import annotations

import copy
import hashlib
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "security/offline-ai/provision/prepare_vendor.py"
SPEC = importlib.util.spec_from_file_location("candidate_vendor", PATH)
PREP = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PREP)


def sha(data):
    return hashlib.sha256(data).hexdigest()


class GitleaksImageCandidateTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.binary = self.root / "candidate"
        self.binary.write_bytes(b"synthetic local executable")
        self.target = self.root / "bin/gitleaks"
        self.target.parent.mkdir()
        self.payloads = {name: name.encode() for name in (
            "go.mod", "go.sum", "modules.json", "module-closure.json", "gitleaks-LICENSE.txt")}
        self.lock = {
            "schema_version": 1,
            "kind": "unreviewed-gitleaks-image-candidate",
            "reviewed": False,
            "source_commit": "a" * 40,
            "catalog_sha256": "b" * 64,
            "binary": {"sha256": sha(self.binary.read_bytes()), "size_bytes": self.binary.stat().st_size},
            "metadata_sha256": {name: sha(data) for name, data in self.payloads.items()},
        }
        self.receipt = {
            "source": {"commit": "a" * 40},
            "catalog_sha256": "b" * 64,
            "module_closure_verified": True,
            "fixture": {"status": "passed", "kind": "existing-clean-and-canary-git"},
            "report_permissions": {"status": "passed", "mode": "0600",
                                   "paths": ["new", "existing"]},
            "build": {"binary_sha256": sha(self.binary.read_bytes())},
            "status": "candidate_complete",
            "last_stage": "complete",
            "reviewed": False,
            "image_qualified": False,
        }

    def stage(self, *, lock=None, receipt=None, payloads=None):
        PREP.stage_gitleaks_candidate(
            self.binary, self.target, payloads or self.payloads, receipt or self.receipt, lock or self.lock)

    def test_exact_verified_local_binary_is_staged_once(self):
        self.stage()
        self.assertEqual(self.target.read_bytes(), self.binary.read_bytes())
        self.assertTrue(self.target.stat().st_mode & 0o111)
        with self.assertRaises(PREP.PreparationError):
            self.stage()
        self.assertEqual(self.target.read_bytes(), self.binary.read_bytes())

    def test_changed_binary_metadata_or_build_identity_is_rejected(self):
        variations = []
        for name in self.payloads:
            payloads = dict(self.payloads)
            payloads[name] += b"tampered"
            variations.append((self.lock, self.receipt, payloads))
        for field, value in (("catalog_sha256", "0" * 64), ("module_closure_verified", False),
                             ("fixture", {"status": "failed"}), ("report_permissions", None),
                             ("reviewed", True)):
            receipt = copy.deepcopy(self.receipt)
            receipt[field] = value
            variations.append((self.lock, receipt, self.payloads))
        altered = copy.deepcopy(self.lock)
        altered["binary"]["sha256"] = "0" * 64
        variations.append((altered, self.receipt, self.payloads))
        for index, (lock, receipt, payloads) in enumerate(variations):
            with self.subTest(index=index), self.assertRaises(PREP.PreparationError):
                self.stage(lock=lock, receipt=receipt, payloads=payloads)
            self.assertFalse(self.target.exists())

    def test_symlinked_source_or_existing_target_is_rejected(self):
        real = self.root / "real"
        self.binary.rename(real)
        self.binary.symlink_to(real)
        with self.assertRaises(PREP.PreparationError):
            self.stage()
        self.assertFalse(self.target.exists())
        self.binary.unlink()
        real.rename(self.binary)
        self.target.symlink_to(self.binary)
        with self.assertRaises(PREP.PreparationError):
            self.stage()
        self.assertTrue(self.target.is_symlink())

    def test_default_binary_path_does_not_invoke_candidate_builder(self):
        vendor = self.root / "vendor"
        vendor.mkdir()
        spec, module = mock.MagicMock(), mock.MagicMock()
        module.extract_verified.return_value = b"pinned-release"
        def download(_source, path):
            path.write_bytes(b"downloaded")
        with mock.patch.object(PREP, "download", side_effect=download), \
                mock.patch.object(PREP.importlib.util, "spec_from_file_location", return_value=spec), \
                mock.patch.object(PREP.importlib.util, "module_from_spec", return_value=module):
            PREP.binaries(vendor, self.root, {"downloads": {"gitleaks": {"sha256": "x"}, "opengrep": {}}})
        self.assertEqual((vendor / "bin/gitleaks").read_bytes(), b"pinned-release")
        module.candidate.assert_not_called()

    def test_failed_candidate_after_staging_does_not_leave_installable_binary(self):
        vendor = self.root / "vendor"
        vendor.mkdir()
        spec, module = mock.MagicMock(), mock.MagicMock()
        def candidate(_destination, *, local_binary):
            local_binary(self.binary, self.payloads, self.receipt)
            raise RuntimeError("synthetic failure")
        module.candidate.side_effect = candidate
        with mock.patch.object(PREP.importlib.util, "spec_from_file_location", return_value=spec), \
                mock.patch.object(PREP.importlib.util, "module_from_spec", return_value=module):
            with self.assertRaises(RuntimeError):
                PREP.binaries(vendor, self.root, {}, candidate_lock=self.lock)
        self.assertFalse((vendor / "bin/gitleaks").exists())

    def test_evidence_mode_installs_only_the_locked_candidate(self):
        vendor = self.root / "vendor"
        vendor.mkdir()
        spec, module = mock.MagicMock(), mock.MagicMock()
        module.candidate.side_effect = lambda _destination, *, local_binary: local_binary(
            self.binary, self.payloads, self.receipt)
        def download(_source, path):
            path.write_bytes(b"opengrep")
        with mock.patch.object(PREP, "download", side_effect=download), \
                mock.patch.object(PREP.importlib.util, "spec_from_file_location", return_value=spec), \
                mock.patch.object(PREP.importlib.util, "module_from_spec", return_value=module):
            PREP.binaries(vendor, self.root, {"downloads": {"opengrep": {}}}, candidate_lock=self.lock)
        self.assertEqual((vendor / "bin/gitleaks").read_bytes(), self.binary.read_bytes())
        self.assertEqual((vendor / "bin/opengrep").read_bytes(), b"opengrep")

    def test_committed_lock_is_unreviewed_and_binds_the_source_catalog(self):
        lock = PREP.load_gitleaks_image_candidate()
        self.assertIs(lock["reviewed"], False)
        for field, value in (("reviewed", True), ("catalog_sha256", "0" * 64), ("source_commit", "bad")):
            with self.subTest(field=field):
                invalid = copy.deepcopy(lock)
                invalid[field] = value
                with mock.patch.object(PREP, "read_json", return_value=invalid):
                    with self.assertRaises(PREP.PreparationError):
                        PREP.load_gitleaks_image_candidate()


if __name__ == "__main__":
    unittest.main()
