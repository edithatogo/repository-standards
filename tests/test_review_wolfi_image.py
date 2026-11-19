"""Check that reviewed identities never suppress image scanner findings."""

import hashlib
from importlib.util import module_from_spec, spec_from_file_location
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = spec_from_file_location("wolfi_review", ROOT / "security/offline-ai/provision/review_wolfi_image.py")
REVIEW = module_from_spec(SPEC)
SPEC.loader.exec_module(REVIEW)
IMAGE = "localhost/offline-ai-security@sha256:" + "a" * 64
IMAGE_ID = "sha256:" + "b" * 64


class WolfiReviewTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.evidence = Path(temporary.name)
        self.vulnerability = self.evidence / "vulnerability"
        self.vulnerability.mkdir()

    def write_scan(self, advisories, *, ignored=()):
        report = json.dumps(
            {
                "matches": advisories,
                "ignoredMatches": list(ignored),
                "source": {"target": {"imageID": IMAGE_ID}},
                "distro": {"name": "wolfi"},
            }
        ).encode()
        (self.vulnerability / "grype.json").write_bytes(report)
        (self.vulnerability / "receipt.json").write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "kind": "offline-image-vulnerability-evidence",
                    "status": "review_pending",
                    "image": IMAGE,
                    "image_id": IMAGE_ID,
                    "scope": "all-layers",
                    "last_stage": "complete",
                    "matches": len(advisories),
                    "ignored_matches": len(ignored),
                    "evidence_sha256": {"grype.json": hashlib.sha256(report).hexdigest()},
                    "database_sha256": "c" * 64,
                }
            )
        )

    def test_verified_empty_image_scan_passes(self):
        self.write_scan([])
        self.assertEqual(REVIEW.review_image(IMAGE, self.evidence)["status"], "passed")

    def test_known_and_unknown_versions_remain_blocking(self):
        for version, disposition in (("2.44-r23", "vendor_backport_unverified"), ("2.44-r24", "unreviewed")):
            with self.subTest(version=version):
                self.write_scan([{
                    "vulnerability": {"id": "CVE-2026-100290", "severity": "Low"},
                    "artifact": {"name": "glibc-2.44", "version": version},
                }])
                review = REVIEW.review_image(IMAGE, self.evidence)
                self.assertEqual(review["status"], "blocked")
                self.assertEqual(review["findings"][0]["disposition"], disposition)

    def test_ignored_match_blocks_even_if_matches_is_empty(self):
        self.write_scan([], ignored=[{}])
        self.assertEqual(REVIEW.review_image(IMAGE, self.evidence)["status"], "blocked")

    def test_changed_report_or_image_is_rejected(self):
        self.write_scan([])
        with self.assertRaises(ValueError):
            REVIEW.review_image(IMAGE[:-1] + "b", self.evidence)
        contents = self.vulnerability / "grype.json"
        contents.write_bytes(contents.read_bytes() + b" ")
        with self.assertRaises(ValueError):
            REVIEW.review_image(IMAGE, self.evidence)
