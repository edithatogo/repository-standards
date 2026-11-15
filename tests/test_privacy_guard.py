"""The event boundary must fail closed, and downloaded archives must be authentic."""

import hashlib
import io
import tarfile
import unittest

from install_gitleaks import extract_verified
from privacy_guard import select_range


class EventRangeTests(unittest.TestCase):
    def test_pr_uses_base(self):
        base = "a" * 40
        self.assertEqual(
            select_range(
                {"pull_request": {"base": {"sha": base}}}, "pull_request", "auto"
            ),
            (base, "HEAD"),
        )

    def test_push_does_not_fall_back_when_base_absent(self):
        with self.assertRaises(KeyError):
            select_range({}, "push", "auto")

    def test_invalid_reference_rejected(self):
        with self.assertRaises(ValueError):
            select_range({"before": "--all"}, "push", "auto")

    def test_new_branch_and_manual_are_full(self):
        self.assertEqual(
            select_range({"before": "0" * 40}, "push", "auto"), (None, "HEAD")
        )
        self.assertEqual(select_range({}, "workflow_dispatch", "auto"), (None, "HEAD"))

    def test_unknown_event_rejected(self):
        with self.assertRaises(ValueError):
            select_range({}, "pull_request_target", "auto")


class InstallerTests(unittest.TestCase):
    def test_checksum_failure_precedes_archive_parsing(self):
        with self.assertRaisesRegex(ValueError, "checksum"):
            extract_verified(b"untrusted bytes", "linux_x64.tar.gz", "0" * 64)

    def test_extracts_only_named_regular_binary(self):
        payload = io.BytesIO()
        with tarfile.open(fileobj=payload, mode="w:gz") as archive:
            data = b"test executable"
            info = tarfile.TarInfo("gitleaks")
            info.size = len(data)
            archive.addfile(info, io.BytesIO(data))
            other = tarfile.TarInfo("../../unexpected")
            other.size = 3
            archive.addfile(other, io.BytesIO(b"bad"))
        raw = payload.getvalue()
        self.assertEqual(
            extract_verified(raw, "linux_x64.tar.gz", hashlib.sha256(raw).hexdigest()),
            b"test executable",
        )
