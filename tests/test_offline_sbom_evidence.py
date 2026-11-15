"""Fixture-based collector tests; these do not execute Syft or qualify an image."""
from __future__ import annotations

import contextlib
import copy
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "sbom_evidence", ROOT / "security/offline-ai/provision/collect_sbom.py")
COLLECTOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(COLLECTOR)
IMAGE_DIGEST = "sha256:" + "a" * 64
IMAGE = "localhost/offline-ai-security@" + IMAGE_DIGEST
IMAGE_ID = "sha256:" + "b" * 64
PRIVATE = "SYNTHETIC_PRIVATE_DIAGNOSTIC"
REPORT = {
    "spdxVersion": "SPDX-2.3", "SPDXID": "SPDXRef-DOCUMENT",
    "creationInfo": {"creators": ["Tool: syft-1.57.1"]},
    "packages": [
        {"name": "fixture-package", "SPDXID": "SPDXRef-Package", "versionInfo": "1"},
        {"name": "localhost/offline-ai-security", "SPDXID": "SPDXRef-Image",
         "versionInfo": IMAGE_DIGEST, "primaryPackagePurpose": "CONTAINER"},
    ],
    "relationships": [{"spdxElementId": "SPDXRef-DOCUMENT",
                       "relationshipType": "DESCRIBES", "relatedSpdxElement": "SPDXRef-Image"}],
}


class SBOMEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="sbom-evidence-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.report = copy.deepcopy(REPORT)
        self.raw_report = None
        self.version = "1.57.1"
        self.endpoint = "unix:///var/run/docker.sock"
        self.repo_digests = [IMAGE]
        self.fail = None
        self.attempt = 0

    def fake_tool(self, work):
        if self.fail == "tool-download":
            raise OSError(PRIVATE)
        return work / "syft"

    def fake_command(self, arguments, environment, timeout=60, output=None):
        args = [str(arg) for arg in arguments]
        self.assertNotIn("SYFT_EXCLUDE", environment)
        self.assertNotIn("SYFT_CONFIG", environment)
        if args[:2] == ["docker", "context"]:
            stage, value = "docker-context", self.endpoint.encode()
        elif args[0] == "docker":
            stage = "image-identity"
            self.assertEqual(environment["DOCKER_HOST"], self.endpoint)
            self.assertNotIn("DOCKER_CONTEXT", environment)
            value = json.dumps([{"Id": IMAGE_ID, "RepoDigests": self.repo_digests,
                                 "Os": "linux", "Architecture": "amd64"}]).encode()
        elif "version" in args:
            stage, value = "tool-version", json.dumps({"version": self.version}).encode()
        else:
            stage, value = "sbom-scan", None
            self.assertIn("docker:" + IMAGE, args)
            self.assertEqual(args[args.index("--scope") + 1], "squashed")
            self.assertEqual(args[args.index("--output") + 1], "spdx-json")
            self.assertEqual(Path(args[args.index("--config") + 1]).read_bytes(), COLLECTOR.CONFIG)
            output.write(self.raw_report if self.raw_report is not None else json.dumps(self.report).encode())
        if self.fail == stage:
            raise subprocess.CalledProcessError(1, args, output=PRIVATE, stderr=PRIVATE)
        return value

    def run_collection(self, image=IMAGE):
        self.attempt += 1
        evidence = self.root / str(self.attempt) / "evidence"
        work = self.root / str(self.attempt) / "work"
        output, error = io.StringIO(), io.StringIO()
        environment = {key: value for key, value in COLLECTOR.os.environ.items()
                       if key not in ("DOCKER_HOST", "DOCKER_CONTEXT")}
        environment.update({"SYFT_EXCLUDE": "/**", "SYFT_CONFIG": "untrusted.yaml"})
        with (patch.object(COLLECTOR, "download_tool", side_effect=self.fake_tool),
              patch.object(COLLECTOR, "command", side_effect=self.fake_command),
              patch.dict(COLLECTOR.os.environ, environment, clear=True),
              contextlib.redirect_stdout(output), contextlib.redirect_stderr(error)):
            status = COLLECTOR.main([image, str(evidence), str(work)])
        self.assertEqual(output.getvalue(), "")
        self.assertEqual(error.getvalue(), "" if status == 0 else COLLECTOR.FAILURE + "\n")
        receipt = json.loads((evidence / "sbom/receipt.json").read_text())
        self.assertFalse(receipt["release_qualified"])
        return status, receipt, evidence / "sbom", work

    def test_inventory_receipt_binds_image_tool_and_private_evidence(self):
        status, receipt, evidence, work = self.run_collection()
        self.assertEqual(status, 0)
        self.assertEqual(receipt["status"], "collected")
        self.assertEqual(receipt["image"], IMAGE)
        self.assertEqual(receipt["image_digest"], IMAGE_DIGEST)
        self.assertEqual(receipt["image_id"], IMAGE_ID)
        self.assertEqual(receipt["scanner"]["source_commit"], COLLECTOR.SOURCE_COMMIT)
        self.assertEqual(json.loads((evidence / "sbom.spdx.json").read_bytes()), REPORT)
        for name, value in receipt["evidence_sha256"].items():
            self.assertEqual(value, hashlib.sha256((evidence / name).read_bytes()).hexdigest())

    def test_other_image_or_undescribed_root_cannot_supply_the_inventory(self):
        for field, value in (("versionInfo", "sha256:" + "c" * 64),
                             ("name", "localhost/another-image"),
                             ("SPDXID", "SPDXRef-Undescribed")):
            with self.subTest(field=field):
                self.report = copy.deepcopy(REPORT)
                self.report["packages"][1][field] = value
                status, receipt, _, _ = self.run_collection()
                self.assertEqual((status, receipt["last_stage"]), (2, "sbom-identity"))

    def test_nonzero_exit_and_download_errors_leave_fixed_failure_receipts(self):
        for stage in ("docker-context", "image-identity", "tool-download", "tool-version", "sbom-scan"):
            with self.subTest(stage=stage):
                self.fail = stage
                status, receipt, _, _ = self.run_collection()
                self.assertEqual((status, receipt["status"], receipt["last_stage"]), (2, "failed", stage))

    def test_remote_docker_is_rejected(self):
        self.endpoint = "tcp://example.invalid:2375"
        status, receipt, _, _ = self.run_collection()
        self.assertEqual((status, receipt["last_stage"]), (2, "docker-context"))

    def test_missing_digest_and_mutable_image_reference_are_rejected(self):
        self.repo_digests = []
        status, receipt, _, _ = self.run_collection()
        self.assertEqual((status, receipt["last_stage"]), (2, "image-identity"))
        status, receipt, _, _ = self.run_collection("localhost/offline-ai-security:candidate")
        self.assertEqual((status, receipt["last_stage"]), (2, "preflight"))

    def test_tool_version_and_report_creator_must_match_the_pin(self):
        self.version = "0.0.0"
        status, receipt, _, _ = self.run_collection()
        self.assertEqual((status, receipt["last_stage"]), (2, "tool-version"))
        self.version = "1.57.1"
        self.report["creationInfo"]["creators"] = ["Tool: syft-0.0.0"]
        status, receipt, _, _ = self.run_collection()
        self.assertEqual((status, receipt["last_stage"]), (2, "sbom-identity"))

    def test_malformed_or_non_spdx_output_cannot_pass(self):
        for value in (b"{", b"{}", b"null"):
            with self.subTest(value=value):
                self.raw_report = value
                status, receipt, _, _ = self.run_collection()
                self.assertEqual((status, receipt["last_stage"]), (2, "sbom-identity"))

    def test_evidence_permissions_ignore_permissive_caller_mask(self):
        for failure in (None, "sbom-scan"):
            with self.subTest(failure=failure):
                self.fail = failure
                previous = COLLECTOR.os.umask(0)
                try:
                    status, receipt, evidence, work = self.run_collection()
                    restored = COLLECTOR.os.umask(0)
                finally:
                    COLLECTOR.os.umask(previous)
                self.assertEqual(restored, 0)
                self.assertEqual(status, 0 if failure is None else 2)
                self.assertEqual(evidence.stat().st_mode & 0o777, 0o700)
                self.assertEqual(work.stat().st_mode & 0o777, 0o700)
                for path in evidence.iterdir():
                    self.assertEqual(path.stat().st_mode & 0o777, 0o600, path.name)

    def test_process_errors_capture_stdout_and_suppress_stderr(self):
        output, error = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(error):
            with self.assertRaises(subprocess.CalledProcessError) as raised:
                COLLECTOR.command([sys.executable, "-c", "import sys; print('" + PRIVATE
                                   + "'); print('" + PRIVATE + "', file=sys.stderr); sys.exit(1)"],
                                  dict(COLLECTOR.os.environ))
        self.assertIn(PRIVATE.encode(), raised.exception.stdout)
        self.assertIsNone(raised.exception.stderr)
        self.assertEqual(output.getvalue() + error.getvalue(), "")


class SyftDownloadTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="syft-download-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.archive = self.make_archive()

    def make_archive(self, link=False):
        buffer = io.BytesIO()
        with tarfile.open(fileobj=buffer, mode="w:gz") as archive:
            member = tarfile.TarInfo("syft")
            if link:
                member.type, member.linkname = tarfile.SYMTYPE, "/untrusted"
                archive.addfile(member)
            else:
                member.size = len(b"fixture executable")
                archive.addfile(member, io.BytesIO(b"fixture executable"))
            extra = tarfile.TarInfo("not-extracted")
            archive.addfile(extra, io.BytesIO())
        return buffer.getvalue()

    def download(self, payload, url="https://release-assets.githubusercontent.com/fixture"):
        response = io.BytesIO(payload)
        response.geturl = lambda: url
        with (patch.object(COLLECTOR.urllib.request, "urlopen", return_value=response),
              patch.object(COLLECTOR, "ARCHIVE_SIZE", len(self.archive)),
              patch.object(COLLECTOR, "ARCHIVE_SHA256", hashlib.sha256(self.archive).hexdigest())):
            return COLLECTOR.download_tool(self.root)

    def test_verified_archive_extracts_only_the_regular_binary(self):
        binary = self.download(self.archive)
        self.assertEqual(binary.read_bytes(), b"fixture executable")
        self.assertEqual(binary.stat().st_mode & 0o777, 0o700)
        self.assertFalse((self.root / "not-extracted").exists())

    def test_size_and_hash_mismatch_prevent_executable_creation(self):
        for label, payload in (("short", self.archive[:-1]), ("long", self.archive + b"x"),
                               ("hash", b"x" + self.archive[1:])):
            with self.subTest(label=label):
                self.root = Path(self.temporary.name) / label
                self.root.mkdir()
                with self.assertRaises(COLLECTOR.EvidenceError):
                    self.download(payload)
                self.assertFalse((self.root / "syft").exists())

    def test_non_https_redirect_is_rejected_before_writing_bytes(self):
        with self.assertRaises(COLLECTOR.EvidenceError):
            self.download(self.archive, url="http://example.invalid/fixture")
        self.assertFalse((self.root / "syft.tar.gz").exists())

    def test_checksum_verified_link_cannot_become_an_executable(self):
        self.archive = self.make_archive(link=True)
        with self.assertRaises(COLLECTOR.EvidenceError):
            self.download(self.archive)
        self.assertFalse((self.root / "syft").exists())


if __name__ == "__main__":
    unittest.main()
