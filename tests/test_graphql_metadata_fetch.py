import io
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

from audit_repository_product_metadata import GitHub, badge_state


ROOT = Path(__file__).resolve().parents[1]


class GraphQLMetadataTests(unittest.TestCase):
    def test_batch_preserves_special_characters_as_variables(self):
        paths = ['docs/quoted"name.md', 'docs/back\\slash.md']
        body = {"data": {"repository": {"f0": {"text": "# First"}, "f1": {"text": ""}}}}
        with patch("urllib.request.urlopen", return_value=io.BytesIO(json.dumps(body).encode())) as send:
            result = GitHub("").texts("owner/repo", paths, 'feature/quoted"branch')

        request = send.call_args.args[0]
        payload = json.loads(request.data)
        self.assertEqual(request.full_url, "https://api.github.com/graphql")
        self.assertEqual(request.method, "POST")
        self.assertEqual(request.get_header("Content-type"), "application/json")
        self.assertEqual(payload["variables"], {
            "owner": "owner",
            "name": "repo",
            "expression0": 'feature/quoted"branch:docs/quoted"name.md',
            "expression1": 'feature/quoted"branch:docs/back\\slash.md',
        })
        self.assertNotIn('quoted"', payload["query"])
        self.assertEqual(result, {paths[0]: "# First", paths[1]: ""})

    def test_empty_batch_does_not_make_a_request(self):
        with patch("urllib.request.urlopen") as send:
            self.assertEqual(GitHub("").texts("owner/repo", [""], "main"), {})
        send.assert_not_called()

    def test_missing_blob_is_omitted(self):
        body = {"data": {"repository": {"f0": None, "f1": {"text": "# README"}}}}
        with patch("urllib.request.urlopen", return_value=io.BytesIO(json.dumps(body).encode())):
            result = GitHub("").texts("owner/repo", ["missing.md", "README.md"], "main")
        self.assertEqual(result, {"readme.md": "# README"})


class BadgeParsingTests(unittest.TestCase):
    def test_badge_count_uses_image_url_and_preserves_case_insensitivity(self):
        readme = """
        ![CI](https://github.com/owner/repo/actions/workflows/ci.yml/badge.svg)
        [![Version](https://img.shields.io/badge/version-1-blue)](https://example.com)
        ![Coverage](https://example.com/BADGE.svg)
        ![badge in label](https://example.com/image.png)
        """
        self.assertEqual(badge_state(readme)["count"], 3)

    def test_malformed_candidates_do_not_hide_later_badges(self):
        readmes = (
            "![broken] text ![valid](https://example.com/badge.svg) ![unterminated",
            "![outer](image/![inner)](actions.svg)",
        )
        for readme in readmes:
            with self.subTest(readme=readme):
                self.assertEqual(badge_state(readme)["count"], 1)

    def test_unterminated_large_readme_finishes_within_three_seconds(self):
        code = (
            'from scripts.audit_repository_product_metadata import badge_state; '
            'assert badge_state("![" * 500000)["count"] == 0'
        )
        completed = subprocess.run(
            [sys.executable, "-c", code], cwd=ROOT, timeout=3, capture_output=True, text=True
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)


if __name__ == "__main__":
    unittest.main()
