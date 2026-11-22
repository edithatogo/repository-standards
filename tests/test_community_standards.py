"""Narrow gate, inherited content and live-observation provenance counterexamples."""

import contextlib
import io
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock

import audit_community_bootstrap as bootstrap
import check_community_standards as gate
from estate_evidence import Reply
import test_community_bootstrap as fixtures


class CommunityStandardsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "project"
        self.defaults = Path(self.temp.name) / "community-defaults"
        self.root.mkdir()
        self.defaults.mkdir()
        self.write(self.root, "README.md", fixtures.GUIDES["README.md"])
        self.write(self.root, "LICENSE", "Existing project licence text.\n")
        for path in ("CONTRIBUTING.md", "CODE_OF_CONDUCT.md", "SECURITY.md", ".github/pull_request_template.md"):
            self.write(self.defaults, path, fixtures.GUIDES[path])
        self.write(self.defaults, ".github/ISSUE_TEMPLATE/one.yml", fixtures.FORM)
        self.metadata = {"defaults_visibility": "public"}

    @staticmethod
    def write(root, path, content):
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)

    def audit(self):
        return gate.audit_native_repository(self.root, defaults_dir=self.defaults, metadata=self.metadata)

    def test_one_valid_inherited_form_and_local_licence_pass_without_bootstrap_requirements(self):
        self.write(self.root, "setup.py", "raise RuntimeError('consumer code must not execute')\n")
        result = self.audit()
        self.assertTrue(result["conformant"])
        self.assertEqual(set(result["checks"]), set(bootstrap.NATIVE_COMMUNITY_CONTROLS) | {"license"})
        self.assertEqual(result["checks"]["issue_templates"]["source"], "inherited")
        self.assertEqual(result["checks"]["license"]["source"], "local")

    def test_missing_empty_and_symlink_licence_do_not_inherit_or_pass(self):
        self.write(self.defaults, "LICENSE", "A defaults licence does not license consumers.\n")
        (self.root / "LICENSE").unlink()
        self.assertIn("license", self.audit()["failures"])
        self.write(self.root, "LICENSE.md", " \n")
        self.assertIn("license", self.audit()["failures"])
        self.write(self.root, "LICENSE.md", "TODO: owner must supply licence terms.\n")
        self.assertIn("license", self.audit()["failures"])
        (self.root / "LICENSE.md").unlink()
        (self.root / "LICENSE").symlink_to(self.defaults / "LICENSE")
        self.assertEqual(self.audit()["checks"]["license"]["status"], "unknown")

    def test_multiple_local_licences_record_presence_without_selecting_terms(self):
        self.write(self.root, "LICENSE.md", "Existing additional licence notice.\n")
        result = self.audit()["checks"]["license"]
        self.assertEqual(result["status"], "pass")
        self.assertEqual(result["paths"], ["LICENSE", "LICENSE.md"])

    def test_native_markdown_accepts_plain_prose_and_nested_sections_but_not_placeholders(self):
        documents = {
            "readme": "# Project\n## Getting started\n### Example\nRun the documented example.\n",
            "contributing": "Start with the development guide; run the checks before submitting a PR.\n",
            "code_of_conduct": "## Enforcement\nReport concerns privately; the existing response policy applies.\n",
            "security": "The main branch is supported. Report vulnerabilities privately. No response SLA is promised.\n",
        }
        for control, content in documents.items():
            with self.subTest(control=control):
                self.assertEqual(bootstrap.guidance_errors(content, control, native=True), [])
                self.assertTrue(bootstrap.guidance_errors(content, control))
        self.write(self.root, "README.md", documents["readme"])
        self.write(self.defaults, "CONTRIBUTING.md", documents["contributing"])
        self.assertTrue(self.audit()["conformant"])
        for content in ("", "# Title only\n", "# Example\nTODO\n", "<!-- unfinished -->\n# Title\n"):
            with self.subTest(content=content):
                self.write(self.root, "README.md", content)
                self.assertIn("readme", self.audit()["failures"])

    def test_one_valid_form_is_native_sufficient_but_full_bootstrap_rejects_extras(self):
        full = {**bootstrap.DEFAULT_POLICY, "issue_form_kinds": {"one": ["one"]}}
        before = bootstrap.audit_repository(self.root, defaults_dir=self.defaults, metadata=self.metadata, policy=full)
        self.assertEqual(before["checks"]["issue_templates"]["status"], "pass")
        self.write(self.defaults, ".github/ISSUE_TEMPLATE/legacy.md", "# Old incomplete issue template\n")
        native = self.audit()
        self.assertTrue(native["conformant"])
        self.assertTrue(native["checks"]["issue_templates"]["details"])
        after = bootstrap.audit_repository(self.root, defaults_dir=self.defaults, metadata=self.metadata, policy=full)
        self.assertEqual(after["checks"]["issue_templates"]["status"], "fail")

    def test_empty_legacy_issue_metadata_is_native_only(self):
        (self.defaults / ".github/ISSUE_TEMPLATE/one.yml").unlink()
        self.write(self.defaults, ".github/ISSUE_TEMPLATE/one.md", "---\nname: Issue report\nabout: Describe a problem\nlabels: ''\nassignees: ''\n---\n## Problem\nDescribe what happened.\n")
        self.assertTrue(self.audit()["conformant"])
        self.assertTrue(bootstrap.template_errors(bootstrap.Tree(self.defaults), ".github/ISSUE_TEMPLATE/one.md"))

    def test_invalid_local_override_is_not_replaced_by_good_defaults(self):
        self.write(self.root, "CONTRIBUTING.md", "# Contributing\nTODO\n")
        self.assertIn("contributing", self.audit()["failures"])
        self.write(self.root, ".github/ISSUE_TEMPLATE/config.yml", "blank_issues_enabled: true\n")
        self.assertIn("issue_templates", self.audit()["failures"])

    def test_zero_or_invalid_effective_forms_never_pass_empty_role_profile(self):
        form = self.defaults / ".github/ISSUE_TEMPLATE/one.yml"
        form.unlink()
        self.assertIn("issue_templates", self.audit()["failures"])
        self.write(self.defaults, ".github/ISSUE_TEMPLATE/one.yml", "name: Empty form\ndescription: Empty\nbody: []\n")
        self.assertIn("issue_templates", self.audit()["failures"])

    def test_private_or_unknown_defaults_cannot_supply_community_files(self):
        for visibility in ("private", "unknown", "absent"):
            with self.subTest(visibility=visibility):
                self.metadata["defaults_visibility"] = visibility
                self.assertFalse(self.audit()["conformant"])

    def observations(self):
        return {
            "/repos/example/project": {"full_name": "example/project", "has_discussions": False, "is_template": False},
            "/repos/example/.github": {"full_name": "example/.github", "private": False, "visibility": "public", "default_branch": "main"},
            "/repos/example/.github/git/ref/heads/main": {"ref": "refs/heads/main", "object": {"type": "commit", "sha": "b" * 40}},
        }

    def test_live_observation_binds_public_owner_defaults_and_immutable_revision(self):
        observations = self.observations()
        api = Mock()
        api.get.side_effect = lambda path: Reply(200, observations[path])
        result = gate.observe_defaults(api, "example/project", "a" * 40)
        self.assertEqual(result["defaults_repository"], "example/.github")
        self.assertEqual(result["defaults_revision"], "b" * 40)
        self.assertEqual(result["defaults_visibility"], "public")
        self.assertEqual(api.get.call_count, 3)

    def test_private_foreign_unknown_or_unresolved_defaults_fail_observation(self):
        invalid_changes = [
            ("/repos/example/.github", "private", True),
            ("/repos/example/.github", "visibility", "unknown"),
            ("/repos/example/.github", "full_name", "other/.github"),
            ("/repos/example/.github/git/ref/heads/main", "object", {"type": "commit", "sha": "main"}),
        ]
        for path, key, value in invalid_changes:
            with self.subTest(key=key):
                observations = self.observations()
                observations[path][key] = value
                api = Mock()
                api.get.side_effect = lambda path: Reply(200, observations[path])
                with self.assertRaises(ValueError):
                    gate.observe_defaults(api, "example/project", "a" * 40)
        with self.assertRaises(ValueError):
            gate.observe_defaults(Mock(get=Mock(return_value=Reply(403, None))), "example/project", "a" * 40)

    def test_clean_git_provenance_rejects_wrong_sha_origin_and_dirty_content(self):
        def git(*args):
            return subprocess.check_output(["git", "-C", str(self.root), *args], stderr=subprocess.DEVNULL, text=True).strip()
        git("init", "-q")
        git("add", ".")
        git("-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "-c", "commit.gpgsign=false", "-c", "core.hooksPath=/dev/null", "commit", "-qm", "Fixture")
        git("remote", "add", "origin", "https://github.com/example/project.git")
        revision = git("rev-parse", "HEAD")
        gate.verify_checkout(self.root, "example/project", revision)
        with self.assertRaises(ValueError):
            gate.verify_checkout(self.root, "example/project", "a" * 40)
        with self.assertRaises(ValueError):
            gate.verify_checkout(self.root, "other/project", revision)
        self.write(self.root, "README.md", "Changed after checkout\n")
        with self.assertRaises(ValueError):
            gate.verify_checkout(self.root, "example/project", revision)

    def test_cli_invalid_metadata_returns_bounded_failure(self):
        path = Path(self.temp.name) / "metadata.json"
        path.write_text('{"defaults_visibility":"public","repository":"example/project","defaults_repository":"other/.github"}')
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = gate.main(["audit", "--repository-dir", str(self.root), "--defaults-dir", str(self.defaults), "--metadata", str(path)])
        self.assertEqual(result, 2)
        self.assertEqual(json.loads(output.getvalue())["error"], "community_standards_invalid_input")

    def test_isolated_cli_does_not_import_consumer_python(self):
        self.write(self.root, "audit_community_bootstrap.py", "raise RuntimeError('consumer import')\n")
        completed = subprocess.run(
            [sys.executable, "-I", str(gate.ROOT / "scripts/check_community_standards.py"),
             "observe", "--repository", "invalid", "--revision", "not-a-sha"],
            cwd=self.root, capture_output=True, text=True, check=False,
        )
        self.assertEqual(completed.returncode, 2)
        self.assertEqual(json.loads(completed.stdout)["error"], "community_standards_invalid_input")

    def test_action_uses_trusted_code_pinned_actions_and_sibling_checkouts(self):
        action = bootstrap.yaml_value((gate.ROOT / ".github/actions/community-standards/action.yml").read_text())
        steps = action["runs"]["steps"]
        for step in steps:
            if "uses" in step:
                self.assertRegex(step["uses"], r"@[0-9a-f]{40}$")
        checkouts = [step for step in steps if step.get("uses", "").startswith("actions/checkout@")]
        self.assertEqual([step["with"]["path"] for step in checkouts], ["project", "community-defaults"])
        self.assertTrue(all(step["with"]["persist-credentials"] is False for step in checkouts))
        self.assertEqual(checkouts[1]["with"]["ref"], "${{ steps.defaults.outputs.defaults-revision }}")
        for step in steps:
            if "run" in step:
                self.assertEqual(step["env"]["POLICY_ROOT"], "${{ github.action_path }}/../../..")
                self.assertNotIn("pull_request_target", step["run"])
        docs = (gate.ROOT / "docs/community-bootstrap-standard.md").read_text()
        workflow = bootstrap.yaml_value(re.search(r"```yaml\n(.*?)\n```", docs, re.S).group(1))
        self.assertEqual(workflow["permissions"], {"contents": "read"})
        self.assertEqual(set(workflow["jobs"]), {"community-standards"})
        self.assertIn("pull_request", workflow["on"])
        self.assertIn("merge_group", workflow["on"])
        self.assertNotIn("paths", str(workflow["on"]))
        self.assertNotIn("pull_request_target", workflow["on"])
        canary = bootstrap.yaml_value((gate.ROOT / ".github/workflows/policy-gate.yml").read_text())
        self.assertEqual(canary["permissions"], {"contents": "read"})
        self.assertNotIn("paths", str(canary["on"]))
        self.assertEqual(canary["jobs"]["community-standards"]["steps"][-1]["uses"], "./.github/actions/community-standards")


if __name__ == "__main__":
    unittest.main()
