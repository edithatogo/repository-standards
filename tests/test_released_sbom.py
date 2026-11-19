import copy
import unittest

from released_sbom import select_asset


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
