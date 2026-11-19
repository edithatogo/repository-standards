import copy
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from released_sbom import main, select_asset


class ReleaseAssetTests(unittest.TestCase):
    def setUp(self):
        self.release = {"id": 1, "published_at": "2026-11-19T00:00:00Z", "draft": False, "prerelease": False,
                        "assets": [{"id": 42, "name": "runtime.cdx.json", "size": 100, "digest": "sha256:" + "a" * 64}]}

    def test_exact_immutable_asset(self):
        self.assertEqual(select_asset(self.release, "runtime.cdx.json")["id"], 42)

    def test_missing_duplicate_or_unhashed_assets_fail(self):
        candidates = []
        missing = copy.deepcopy(self.release)
        missing["assets"] = []
        candidates.append(missing)
        duplicate = copy.deepcopy(self.release)
        duplicate["assets"] *= 2
        candidates.append(duplicate)
        unhashed = copy.deepcopy(self.release)
        unhashed["assets"][0]["digest"] = None
        candidates.append(unhashed)
        for candidate in candidates:
            with self.subTest(candidate=candidate), self.assertRaises(ValueError):
                select_asset(candidate, "runtime.cdx.json")

    def test_draft_and_path_traversal_fail(self):
        self.release["draft"] = True
        with self.assertRaises(ValueError):
            select_asset(self.release, "runtime.cdx.json")
        self.release["draft"] = False
        with self.assertRaises(ValueError):
            select_asset(self.release, "../runtime.cdx.json")

    def test_missing_asset_retains_failed_selection_evidence(self):
        release = dict(self.release, tag_name="v1.0", assets=[])
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "evidence"
            gh_output = Path(temp) / "outputs"
            with patch.dict(os.environ, {"GITHUB_OUTPUT": str(gh_output)}), patch("released_sbom.api", return_value=release), \
                 patch("sys.argv", ["released_sbom", "--repository", "example/tool", "--asset", "runtime.cdx.json", "--output-directory", str(output)]):
                self.assertEqual(main(), 1)
            receipt = json.loads((output / "release-input.json").read_text())
            self.assertFalse(receipt["input_verified"])
            self.assertEqual(receipt["release_id"], 1)
            self.assertIn("evidence-directory=", gh_output.read_text())
            self.assertNotIn("sbom=", gh_output.read_text())

    def test_substituted_bytes_are_retained_as_unverified_and_never_exposed_to_scan(self):
        release = dict(self.release, tag_name="v1.0")
        def download(*args, **kwargs):
            kwargs["stdout"].write(b"substituted bytes")
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "evidence"
            gh_output = Path(temp) / "outputs"
            with patch.dict(os.environ, {"GITHUB_OUTPUT": str(gh_output)}), \
                 patch("released_sbom.api", side_effect=[release, {"object": {"type": "commit", "sha": "a" * 40}}]), \
                 patch("released_sbom.subprocess.run", side_effect=download), \
                 patch("sys.argv", ["released_sbom", "--repository", "example/tool", "--asset", "runtime.cdx.json", "--output-directory", str(output)]):
                self.assertEqual(main(), 1)
            receipt = json.loads((output / "release-input.json").read_text())
            self.assertFalse(receipt["input_verified"])
            self.assertEqual(receipt["stage"], "verify-download")
            self.assertEqual(receipt["asset_id"], 42)
            self.assertEqual(receipt["observed_size"], len(b"substituted bytes"))
            self.assertNotIn("sbom=", gh_output.read_text())
