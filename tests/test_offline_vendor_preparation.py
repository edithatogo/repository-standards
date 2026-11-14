"""Source/provenance and failure regressions; no scanner/model qualification."""
from __future__ import annotations

import base64
from contextlib import redirect_stdout
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / "security/offline-ai/provision"


def load(name):
    spec = importlib.util.spec_from_file_location(name, HERE / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


PREP = load("prepare_vendor")
CANDIDATE = load("resolve_candidate")


class VendorPreparationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def test_unreviewed_catalog_fails_before_using_candidate_files(self):
        (self.root / "sources.json").write_text(json.dumps({
            "schema_version": 1, "lock_status": "candidate_required",
            "target": {"os": "linux", "architecture": "x86_64", "python": "3.15.1"}}))
        with mock.patch.object(PREP, "HERE", self.root):
            with self.assertRaisesRegex(PREP.PreparationError, "lock-readiness"):
                PREP.load_catalog()

    def test_exact_pins_and_hashes_are_required(self):
        path = self.root / "requirements.lock"
        for value in ("example>=1.0", "example==1.0", "example==1.0 --hash=sha256:no",
                      "https://example.invalid/pkg.whl --hash=sha256:" + "0" * 64,
                      "--extra-index-url https://example.invalid"):
            with self.subTest(value=value):
                path.write_text(value + "\n")
                with self.assertRaises(PREP.PreparationError):
                    PREP.read_lock(path)

    def test_conflicting_pinned_versions_are_rejected(self):
        first, second = self.root / "one.lock", self.root / "two.lock"
        first.write_text("example==1.0 --hash=sha256:" + "0" * 64 + "\n")
        second.write_text("example==2.0 --hash=sha256:" + "1" * 64 + "\n")
        with self.assertRaises(PREP.PreparationError):
            PREP.merge_locks(first, second)

    def test_verified_stream_is_published_only_after_hash_and_size_checks(self):
        content = b"synthetic upstream bytes"
        source = {"url": "https://github.com/example/release", "size_bytes": len(content),
                  "maximum_bytes": len(content), "sha256": hashlib.sha256(content).hexdigest()}
        destination = self.root / "binary"
        response = io.BytesIO(content)
        response.url = source["url"]
        with mock.patch.object(PREP.urllib.request, "urlopen", return_value=response):
            PREP.download(source, destination)
        self.assertEqual(destination.read_bytes(), content)

    def test_changed_or_oversized_upstream_never_leaves_an_installable_file(self):
        for mode in ("hash", "size"):
            with self.subTest(mode=mode):
                destination = self.root / mode
                source = {"url": "https://github.com/example/release", "maximum_bytes": 3,
                          "sha256": hashlib.sha256(b"abc").hexdigest()}
                response = io.BytesIO(b"xyz" if mode == "hash" else b"abcd")
                response.url = source["url"]
                with mock.patch.object(PREP.urllib.request, "urlopen", return_value=response):
                    with self.assertRaises(PREP.PreparationError):
                        PREP.download(source, destination)
                self.assertFalse(destination.exists())

    def test_existing_download_destination_is_preserved(self):
        destination = self.root / "binary"
        destination.write_bytes(b"keep")
        with self.assertRaises(PREP.PreparationError):
            PREP.download({}, destination)
        self.assertEqual(destination.read_bytes(), b"keep")

    def npm_fixture(self):
        package, lock = self.root / "package.json", self.root / "package-lock.json"
        integrity = "sha512-" + base64.b64encode(b"\0" * 64).decode("ascii")
        package.write_text(json.dumps({"private": True, "dependencies": {"promptfoo": "0.125.1"}}))
        data = {"lockfileVersion": 3, "packages": {
            "": {"dependencies": {"promptfoo": "0.125.1"}},
            "node_modules/promptfoo": {"version": "0.125.1",
                "resolved": "https://registry.npmjs.org/promptfoo/-/promptfoo-0.125.1.tgz",
                "integrity": integrity}}}
        lock.write_text(json.dumps(data))
        return package, lock, integrity, data

    def test_npm_registry_integrity_and_exact_version_are_required(self):
        package, lock, integrity, data = self.npm_fixture()
        PREP.validate_npm_lock(package, lock, integrity)
        for key, value in (("version", "^0.125.1"), ("integrity", "sha512-invalid"),
                           ("resolved", "https://example.invalid/archive.tgz")):
            with self.subTest(key=key):
                changed = json.loads(json.dumps(data))
                changed["packages"]["node_modules/promptfoo"][key] = value
                lock.write_text(json.dumps(changed))
                with self.assertRaises(PREP.PreparationError):
                    PREP.validate_npm_lock(package, lock, integrity)

    def test_manifest_cannot_be_generated_with_incomplete_provenance(self):
        (self.root / "sources.json").write_text("{}")
        vendor = self.root / "vendor"
        vendor.mkdir()
        receipt = {"sources_catalog_sha256": PREP.digest(self.root / "sources.json"),
                   "stages": {"binaries": "passed", "python": "failed"}}
        with mock.patch.object(PREP, "HERE", self.root):
            with self.assertRaises(PREP.PreparationError):
                PREP.finalize(vendor, receipt, {})
        self.assertFalse((vendor / "manifest.json").exists())

    def test_failed_stage_retains_explicit_unexecuted_stage_evidence(self):
        (self.root / "sources.json").write_text("{}")
        receipt_path = self.root / "preparation.json"
        catalog = {"policy_inputs": {}, "downloads": {}}
        with mock.patch.object(PREP, "HERE", self.root), \
                mock.patch.object(PREP.sys, "version_info", (3, 15, 1)), \
                mock.patch.object(PREP.platform, "system", return_value="Linux"), \
                mock.patch.object(PREP.platform, "machine", return_value="x86_64"), \
                mock.patch.object(PREP, "load_catalog", return_value=catalog), \
                mock.patch.object(PREP, "binaries", side_effect=PREP.PreparationError("synthetic")):
            with self.assertRaises(PREP.PreparationError):
                PREP.prepare(self.root / "vendor", receipt_path)
        receipt = json.loads(receipt_path.read_text())
        self.assertEqual(receipt["status"], "failed")
        self.assertEqual(receipt["stages"], {
            "binaries": "failed", "python": "not-run", "promptfoo": "not-run", "model": "not-run"})
        self.assertFalse(receipt["image_qualified"])
        self.assertFalse(receipt["runner_registered"])

    def test_public_chunks_reconstruct_exact_bytes_and_reject_other_paths(self):
        records = []
        for relative in CANDIDATE.OUTPUTS:
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            content = ("synthetic public metadata\n" * 100).encode("utf-8")
            path.write_bytes(content)
            records.append({"path": relative, "sha256": hashlib.sha256(content).hexdigest()})
        receipt = {"files": records, "reviewed": False, "qualified": False}
        output = io.StringIO()
        with redirect_stdout(output):
            CANDIDATE.emit_public_locks(self.root, receipt)
        chunks = [json.loads(line.split(" ", 1)[1]) for line in output.getvalue().splitlines()
                  if line.startswith("OFFLINE_LOCK_CHUNK ")]
        for relative in CANDIDATE.OUTPUTS:
            selected = [chunk for chunk in chunks if chunk["path"] == relative]
            self.assertEqual([chunk["index"] for chunk in selected], list(range(len(selected))))
            text = "".join(chunk["data"] for chunk in selected)
            self.assertEqual(text.encode(), (self.root / relative).read_bytes())
        records[0]["path"] = "unrelated.txt"
        with self.assertRaises(ValueError):
            CANDIDATE.emit_public_locks(self.root, receipt)


if __name__ == "__main__":
    unittest.main()
