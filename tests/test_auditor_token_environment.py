"""Fail-closed regression tests for consumed auditor credential variables."""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import audit_estate_conformance as estate
import audit_repository_product_metadata as products


class _OfflineGitHub:
    """A synthetic client that never contacts GitHub."""

    def __init__(self, token):
        self.token = token
        self.scope = "synthetic unit-test fixture"
        self.metrics = {"requests": 0, "retries": 0, "tolerated_errors": 0}

    def active_repositories(self, owner):
        return []


class ConsumedCredentialEnvironmentTests(unittest.TestCase):
    def test_product_auditor_removes_both_token_names_and_keeps_precedence(self):
        cases = (
            ({"GITHUB_TOKEN": "synthetic-primary", "GH_TOKEN": "synthetic-fallback"},
             "synthetic-primary"),
            ({"GITHUB_TOKEN": "", "GH_TOKEN": "synthetic-fallback"},
             "synthetic-fallback"),
        )
        for environment, expected in cases:
            with self.subTest(environment=environment), tempfile.TemporaryDirectory() as root:
                clients = []

                def create_client(token):
                    client = _OfflineGitHub(token)
                    clients.append(client)
                    return client

                argv = ["audit_repository_product_metadata.py", "--owner", "example",
                        "--output-dir", root]
                with (patch.dict(os.environ, {**environment, "UNRELATED_SETTING": "preserve"},
                                 clear=True),
                      patch.object(sys, "argv", argv),
                      patch.object(products, "GitHub", side_effect=create_client)):
                    self.assertEqual(products.main(), 0)
                    self.assertEqual([client.token for client in clients], [expected])
                    self.assertNotIn("GITHUB_TOKEN", os.environ)
                    self.assertNotIn("GH_TOKEN", os.environ)
                    self.assertEqual(os.environ["UNRELATED_SETTING"], "preserve")
                    report = json.loads(
                        (Path(root) / "repository-product-metadata-audit.json").read_text()
                    )
                    self.assertEqual(report["repositories"], [])

    def test_estate_auditor_removes_both_audit_tokens_and_issue_token(self):
        with tempfile.TemporaryDirectory() as root:
            root_path = Path(root)
            for name, payload in (
                ("registry.json", {"repositories": [], "scope": "synthetic"}),
                ("profiles.json", {}),
                ("managed.json", {}),
            ):
                (root_path / name).write_text(json.dumps(payload), encoding="utf-8")

            clients = []

            def create_client(token):
                client = _OfflineGitHub(token)
                clients.append(client)
                return client

            argv = [
                "audit_estate_conformance.py", "--registry", str(root_path / "registry.json"),
                "--profiles", str(root_path / "profiles.json"),
                "--managed-files", str(root_path / "managed.json"),
                "--output-dir", str(root_path / "output"),
                "--issue-repository", "example/synthetic", "--issue-number", "7",
            ]
            environment = {
                "ESTATE_AUDIT_TOKEN": "synthetic-estate",
                "GITHUB_TOKEN": "synthetic-github",
                "ISSUE_TOKEN": "synthetic-issue",
                "UNRELATED_SETTING": "preserve",
            }
            with (patch.dict(os.environ, environment, clear=True),
                  patch.object(sys, "argv", argv),
                  patch.object(estate, "GitHub", side_effect=create_client),
                  patch.object(estate, "reconcile_issue",
                               return_value="https://example.invalid/issue/7") as reconcile):
                self.assertEqual(estate.main(), 0)
                self.assertEqual([client.token for client in clients],
                                 ["synthetic-estate", "synthetic-issue"])
                reconcile.assert_called_once()
                for name in ("ESTATE_AUDIT_TOKEN", "GITHUB_TOKEN", "ISSUE_TOKEN"):
                    self.assertNotIn(name, os.environ)
                self.assertEqual(os.environ["UNRELATED_SETTING"], "preserve")

    def test_estate_auditor_uses_fallback_when_primary_is_empty(self):
        with tempfile.TemporaryDirectory() as root:
            root_path = Path(root)
            for name, payload in (
                ("registry.json", {"repositories": []}),
                ("profiles.json", {}),
                ("managed.json", {}),
            ):
                (root_path / name).write_text(json.dumps(payload), encoding="utf-8")
            argv = [
                "audit_estate_conformance.py", "--registry", str(root_path / "registry.json"),
                "--profiles", str(root_path / "profiles.json"),
                "--managed-files", str(root_path / "managed.json"),
                "--output-dir", str(root_path / "output"),
            ]
            clients = []
            def create_client(token):
                client = _OfflineGitHub(token)
                clients.append(client)
                return client

            with (patch.dict(os.environ, {"ESTATE_AUDIT_TOKEN": "",
                                          "GITHUB_TOKEN": "synthetic-fallback"}, clear=True),
                  patch.object(sys, "argv", argv),
                  patch.object(estate, "GitHub", side_effect=create_client)):
                self.assertEqual(estate.main(), 0)
                self.assertEqual([client.token for client in clients], ["synthetic-fallback"])
                self.assertNotIn("ESTATE_AUDIT_TOKEN", os.environ)
                self.assertNotIn("GITHUB_TOKEN", os.environ)


if __name__ == "__main__":
    unittest.main()
