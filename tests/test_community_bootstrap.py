"""Behavioral contracts for effective GitHub community/bootstrap coverage."""

import contextlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import audit_community_bootstrap as audit


GUIDES = {
    "README.md": "# Example\nA small useful project.\n## Usage\nRun the documented example.\n## Development\nRun python -m unittest before proposing changes.\n## Security\nRead SECURITY.md for reporting instructions.\n## License\nRead LICENSE for terms.\n",
    "CONTRIBUTING.md": "# Contributing\n## Getting started\nCreate a virtual environment and install the package.\n## Validation\nRun python -m unittest to check your changes.\n## Pull requests\nExplain the changes and attach actual evidence.\n",
    "CODE_OF_CONDUCT.md": "# Code of conduct\n## Expected behaviour\nTreat everyone respectfully and protect personal information.\n## Reporting\nUse the private reporting route documented here.\n## Enforcement\nThe maintainer reviews reports and can restrict participation.\n",
    "SECURITY.md": "# Security\n## Supported versions\nUse the latest maintained release; see release notes.\n## Reporting a vulnerability\nUse the repository Security tab to report privately.\n## Response and disclosure\nCoordinate publication with the maintainer.\n",
    "SUPPORT.md": "# Support\n## Getting help\nRead the usage documentation and search existing issues.\n## What to include\nDescribe the version and a safe minimal example.\n## Availability\nSupport is provided on a best effort basis.\n",
    "AGENTS.md": "# Agent instructions\n## Architecture\nSource lives in src and tests in tests.\n## Validation\nRun python -m unittest before proposing changes.\n",
    ".github/pull_request_template.md": "## Summary\nExplain the purpose.\n## Related work\nLink relevant issues.\n## Validation\nList commands and outcomes.\n## Compatibility and rollout\nDescribe compatibility impacts.\n## Documentation\nDescribe documentation updates.\n",
    ".gitignore": "__pycache__/\n.venv/\n",
    ".editorconfig": "root = true\n[*]\ncharset = utf-8\ninsert_final_newline = true\n",
    "renovate.json": '{"extends": ["github>example/config"]}\n',
    ".github/workflows/ci.yml": "name: CI\non: [push]\njobs:\n  test:\n    runs-on: ubuntu-latest\n    steps:\n      - run: python -m unittest\n",
    ".github/ISSUE_TEMPLATE/config.yml": "blank_issues_enabled: true\n",
}
FORM = """name: Bug report
description: Describe a reproducible problem.
body:
  - type: textarea
    id: reproduction
    attributes:
      label: Reproduction
    validations:
      required: true
"""
DISCUSSION = """body:
  - type: textarea
    id: question
    attributes:
      label: Question
"""


class CommunityBootstrapTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "repository"
        self.defaults = Path(self.temp.name) / "defaults"
        self.root.mkdir()
        self.defaults.mkdir()
        self.policy = {
            "schema_version": 1,
            "required": [
                "readme", "contributing", "code_of_conduct", "security", "support",
                "issue_templates", "issue_chooser", "pull_request_template", "agents",
                "workflows", "dependency_updates", "gitignore", "editorconfig",
                "env_example", "devcontainer", "discussion_templates", "template_repository",
            ],
            "recommended": [],
            "environment_configuration": False,
            "devcontainer": "optional",
            "template_repository": False,
            "issue_form_kinds": {"bug": ["bug", "bug_report"]},
        }
        self.metadata = {"defaults_visibility": "public", "has_discussions": False, "is_template": False}
        for path, content in GUIDES.items():
            self.write(self.root, path, content)
        self.write(self.root, ".github/ISSUE_TEMPLATE/bug.yml", FORM)

    @staticmethod
    def write(root, relative, text):
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")

    def run_audit(self, **kwargs):
        return audit.audit_repository(
            self.root, defaults_dir=self.defaults,
            metadata=kwargs.pop("metadata", self.metadata),
            policy=kwargs.pop("policy", self.policy), **kwargs,
        )

    def check(self, control):
        return self.run_audit()["checks"][control]

    def test_complete_local_repository_passes_without_running_content(self):
        self.assertTrue(self.run_audit()["conformant"])
        self.assertEqual("local", self.check("contributing")["source"])

    def test_valid_inherited_forms_and_guidance_are_identified(self):
        for path in ["CONTRIBUTING.md", ".github/pull_request_template.md", ".github/ISSUE_TEMPLATE/bug.yml", ".github/ISSUE_TEMPLATE/config.yml"]:
            original = self.root / path
            self.write(self.defaults, path, original.read_text())
            original.unlink()
        self.assertTrue(self.run_audit()["conformant"])
        self.assertEqual("inherited", self.check("issue_templates")["source"])
        self.assertEqual("inherited", self.check("pull_request_template")["source"])

    def test_config_only_local_override_removes_all_inherited_issue_forms(self):
        (self.root / ".github/ISSUE_TEMPLATE/bug.yml").unlink()
        self.write(self.defaults, ".github/ISSUE_TEMPLATE/bug.yml", FORM)
        result = self.check("issue_templates")
        self.assertEqual("fail", result["status"])
        self.assertEqual("local", result["source"])

    def test_one_local_form_overrides_inherited_chooser_and_other_forms(self):
        (self.root / ".github/ISSUE_TEMPLATE/config.yml").unlink()
        self.write(self.defaults, ".github/ISSUE_TEMPLATE/config.yml", "blank_issues_enabled: false\n")
        self.write(self.defaults, ".github/ISSUE_TEMPLATE/feature.yml", FORM)
        self.policy["issue_form_kinds"]["feature"] = ["feature"]
        self.assertEqual("fail", self.check("issue_chooser")["status"])
        self.assertEqual("fail", self.check("issue_templates")["status"])

    def test_invalid_local_override_never_silently_passes_from_defaults(self):
        self.write(self.root, ".github/ISSUE_TEMPLATE/config.yml", "[invalid, config]\n")
        (self.root / ".github/ISSUE_TEMPLATE/bug.yml").unlink()
        self.write(self.defaults, ".github/ISSUE_TEMPLATE/bug.yml", FORM)
        self.assertIn(self.check("issue_templates")["status"], {"fail", "unknown"})

    def test_private_or_unavailable_defaults_do_not_count_as_inherited(self):
        (self.root / "SUPPORT.md").unlink()
        self.write(self.defaults, "SUPPORT.md", GUIDES["SUPPORT.md"])
        for visibility in ["private", "unknown", "absent"]:
            with self.subTest(visibility=visibility):
                self.metadata["defaults_visibility"] = visibility
                self.assertNotEqual("pass", self.check("support")["status"])

    def test_local_github_guidance_precedes_root_and_docs(self):
        self.write(self.root, ".github/CONTRIBUTING.md", "# Contributing\nTODO\n")
        self.write(self.root, "docs/CONTRIBUTING.md", GUIDES["CONTRIBUTING.md"])
        self.assertEqual("fail", self.check("contributing")["status"])
        self.assertEqual([".github/CONTRIBUTING.md"], self.check("contributing")["paths"])

    def test_local_specialized_guidance_precedes_account_default(self):
        self.write(self.defaults, "CONTRIBUTING.md", "# Contributing\nTODO\n")
        self.assertEqual("pass", self.check("contributing")["status"])

    def test_markdown_issue_frontmatter_is_supported(self):
        (self.root / ".github/ISSUE_TEMPLATE/bug.yml").unlink()
        self.write(self.root, ".github/ISSUE_TEMPLATE/Bug.MD", "---\nname: Bug report\nabout: Reproducible defects\n---\n## Reproduction\nDescribe what happened.\n")
        self.assertEqual("pass", self.check("issue_templates")["status"])

    def test_form_schema_rejects_wrong_types_unknown_fields_and_markdown_only(self):
        for content in ["[]", "name: Bug\ndescription: Problem\nbody: []", FORM.replace("required: true", 'required: "true"'), FORM.replace("type: textarea", "type: invented"), "name: Bug report\ndescription: Problem\nbody:\n - type: markdown\n   attributes:\n     value: Informational only\n"]:
            with self.subTest(content=content):
                self.write(self.root, ".github/ISSUE_TEMPLATE/bug.yml", content)
                self.assertEqual("fail", self.check("issue_templates")["status"])

    def test_duplicate_yaml_keys_and_unsafe_tags_are_rejected(self):
        for content in [FORM + "name: Duplicate\n", "!!python/object/apply:os.system ['touch unsafe']", "name: [unterminated"]:
            with self.subTest(content=content):
                self.write(self.root, ".github/ISSUE_TEMPLATE/bug.yml", content)
                self.assertEqual("fail", self.check("issue_templates")["status"])
        self.assertFalse((self.root / "unsafe").exists())

    def test_missing_yaml_parser_is_unknown_and_not_conformant(self):
        with patch.object(audit, "yaml", None):
            self.assertEqual("unknown", self.check("issue_templates")["status"])
            self.assertFalse(self.run_audit()["conformant"])

    def test_documented_issue_extension_and_directory_are_required(self):
        (self.root / ".github/ISSUE_TEMPLATE/bug.yml").unlink()
        self.write(self.root, ".github/ISSUE_TEMPLATE/bug.yaml", FORM)
        self.assertNotEqual("pass", self.check("issue_templates")["status"])
        self.write(self.root, ".github/issue_template/bug.yml", FORM)
        self.assertNotEqual("pass", self.check("issue_templates")["status"])

    def test_duplicate_form_ids_fail(self):
        self.write(self.root, ".github/ISSUE_TEMPLATE/bug.yml", FORM + "  - type: input\n    id: reproduction\n    attributes:\n      label: Duplicate\n")
        self.assertEqual("fail", self.check("issue_templates")["status"])

    def test_unknown_attributes_and_invalid_dropdown_defaults_fail(self):
        invalid = [
            {"type": "input", "attributes": {"label": "Example", "unknown-key": "unchecked"}},
            {"type": "dropdown", "attributes": {"label": "Example", "options": ["a", "b"], "default": {"invalid": "type"}}},
            {"type": "dropdown", "attributes": {"label": "Example", "options": ["a", "b"], "default": True}},
            {"type": "dropdown", "attributes": {"label": "Example", "options": ["a", "a"]}},
            {"type": "dropdown", "attributes": {"label": "Example", "options": ["a", "None"], "default": 0}},
        ]
        for field in invalid:
            with self.subTest(field=field):
                self.write(self.root, ".github/ISSUE_TEMPLATE/bug.yml", json.dumps({"name": "Bug report", "description": "A problem", "body": [field]}))
                self.assertEqual("fail", self.check("issue_templates")["status"])

    def test_valid_dropdown_default_passes(self):
        self.write(self.root, ".github/ISSUE_TEMPLATE/bug.yml", json.dumps({"name": "Bug report", "description": "A problem", "body": [{"type": "dropdown", "attributes": {"label": "Version", "options": ["Current", "Previous"], "default": 0}}]}))
        self.assertEqual("pass", self.check("issue_templates")["status"])

    def test_multiple_pr_templates_in_docs_are_supported(self):
        (self.root / ".github/pull_request_template.md").unlink()
        self.write(self.root, "docs/PULL_REQUEST_TEMPLATE/change.MD", GUIDES[".github/pull_request_template.md"])
        self.assertEqual("pass", self.check("pull_request_template")["status"])

    def test_non_inheritable_files_remain_missing_even_if_account_has_them(self):
        for path, control in [("AGENTS.md", "agents"), (".editorconfig", "editorconfig"), ("README.md", "readme"), (".gitignore", "gitignore")]:
            with self.subTest(control=control):
                original = self.root / path
                self.write(self.defaults, path, original.read_text())
                original.unlink()
                self.assertEqual("fail", self.check(control)["status"])

    def test_discussions_disabled_is_not_applicable(self):
        self.assertEqual("not_applicable", self.check("discussion_templates")["status"])

    def test_discussions_enabled_requires_observed_category_slugs(self):
        self.metadata["has_discussions"] = True
        self.write(self.root, ".github/DISCUSSION_TEMPLATE/questions.yml", DISCUSSION)
        self.assertEqual("unknown", self.check("discussion_templates")["status"])
        self.metadata["discussion_categories"] = ["questions"]
        self.assertEqual("pass", self.check("discussion_templates")["status"])
        self.metadata["discussion_categories"] = ["ideas"]
        self.assertEqual("fail", self.check("discussion_templates")["status"])

    def test_template_declaration_does_not_prove_template_setting(self):
        self.policy["template_repository"] = True
        self.metadata.pop("is_template")
        self.assertEqual("unknown", self.check("template_repository")["status"])
        self.metadata["is_template"] = False
        self.assertEqual("fail", self.check("template_repository")["status"])
        self.metadata["is_template"] = True
        self.assertEqual("pass", self.check("template_repository")["status"])

    def test_conditional_env_and_devcontainer_preserve_unknown_and_na(self):
        self.assertEqual("not_applicable", self.check("env_example")["status"])
        self.policy["environment_configuration"] = None
        self.assertEqual("unknown", self.check("env_example")["status"])
        self.policy["environment_configuration"] = True
        self.assertEqual("fail", self.check("env_example")["status"])
        self.write(self.root, ".env.example", "API_URL=https://example.invalid\n")
        self.assertEqual("pass", self.check("env_example")["status"])
        self.policy["devcontainer"] = "required"
        self.assertEqual("fail", self.check("devcontainer")["status"])
        self.write(self.root, ".devcontainer.json", '{"image":"example/dev:qualified"}')
        self.assertEqual("pass", self.check("devcontainer")["status"])

    def test_local_applicability_cannot_disable_controls(self):
        self.write(self.root, ".github/community-bootstrap.json", '{"schema_version":1,"required":[]}')
        with self.assertRaises(ValueError):
            self.run_audit()

    def test_local_applicability_requires_reason_and_preserves_required_checks(self):
        self.write(self.root, ".github/community-bootstrap.json", json.dumps({"schema_version": 1, "environment_configuration": False, "devcontainer": "optional", "template_repository": True, "rationale": {"environment_configuration": "No runtime environment configuration.", "devcontainer": "Existing local commands suffice."}}))
        self.metadata["is_template"] = True
        self.assertTrue(self.run_audit()["conformant"])
        (self.root / "SUPPORT.md").unlink()
        self.assertFalse(self.run_audit()["conformant"])

    def test_local_applicability_cannot_reduce_explicit_central_requirements(self):
        self.policy.update(environment_configuration=True, devcontainer="required", template_repository=True)
        self.write(self.root, ".github/community-bootstrap.json", json.dumps({"schema_version": 1, "environment_configuration": False, "devcontainer": "optional", "template_repository": False, "rationale": {"environment_configuration": "Attempt to remove centrally required configuration.", "devcontainer": "Attempt to remove a required container."}}))
        checks = self.run_audit()["checks"]
        for control in ("env_example", "devcontainer", "template_repository"):
            self.assertEqual("fail", checks[control]["status"])

    def test_symlink_files_and_directories_are_not_followed(self):
        (self.root / "SUPPORT.md").unlink()
        self.write(self.defaults, "SUPPORT.md", GUIDES["SUPPORT.md"])
        (self.root / "SUPPORT.md").symlink_to(self.defaults / "SUPPORT.md")
        self.assertNotEqual("pass", self.check("support")["status"])
        (self.root / "AGENTS.md").unlink()
        (self.root / "AGENTS.md").symlink_to("/etc/passwd")
        self.assertNotEqual("pass", self.check("agents")["status"])

    def test_symlink_template_directory_is_unavailable(self):
        (self.root / ".github/ISSUE_TEMPLATE").rename(self.defaults / "outside")
        (self.root / ".github/ISSUE_TEMPLATE").symlink_to(self.defaults / "outside", target_is_directory=True)
        self.assertEqual("unknown", self.check("issue_templates")["status"])

    def test_root_ancestor_replaced_by_symlink_cannot_escape(self):
        parent = Path(self.temp.name) / "parent"
        inner = parent / "repo"
        inner.mkdir(parents=True)
        self.write(inner, "README.md", "original")
        snapshot = audit.Tree(inner)
        parent.rename(Path(self.temp.name) / "old_parent")
        outside = Path(self.temp.name) / "outside"
        self.write(outside, "repo/README.md", "outside-marker")
        parent.symlink_to(outside, target_is_directory=True)
        with self.assertRaises(audit.EvidenceError):
            snapshot.read("README.md")

    def test_nested_agent_guidance_does_not_cover_repository_root(self):
        (self.root / "AGENTS.md").unlink()
        self.write(self.root, "docs/AGENTS.md", GUIDES["AGENTS.md"])
        self.assertEqual("fail", self.check("agents")["status"])

    def test_wrong_field_type_and_malformed_contact_url_produce_findings(self):
        self.write(self.root, ".github/ISSUE_TEMPLATE/bug.yml", FORM.replace("type: textarea", "type: [textarea]"))
        self.assertEqual("fail", self.check("issue_templates")["status"])
        self.write(self.root, ".github/ISSUE_TEMPLATE/config.yml", 'contact_links:\n - name: Support\n   about: Ask questions\n   url: "https://["\n')
        self.assertEqual("fail", self.check("issue_chooser")["status"])

    def test_alias_cycles_and_excessive_nesting_are_rejected(self):
        for content in ["body: &body [*body]", "[" * 50 + "null" + "]" * 50]:
            with self.subTest(content=content):
                self.write(self.root, ".github/ISSUE_TEMPLATE/bug.yml", content)
                self.assertEqual("fail", self.check("issue_templates")["status"])

    def test_invalid_applicability_types_are_input_errors(self):
        for field, value in [("schema_version", True), ("devcontainer", []), ("environment_configuration", "false")]:
            with self.subTest(field=field):
                with self.assertRaises(ValueError):
                    self.run_audit(policy={**self.policy, field: value})
        with self.assertRaises(ValueError):
            self.run_audit(metadata={"defaults_visibility": []})

    def test_empty_editorconfig_and_environment_example_do_not_pass(self):
        self.write(self.root, ".editorconfig", "root = true\n[*]\n")
        self.assertEqual("fail", self.check("editorconfig")["status"])
        self.policy["environment_configuration"] = True
        self.write(self.root, ".env.example", "# fill in environment variables later\n")
        self.assertEqual("fail", self.check("env_example")["status"])

    def test_oversized_guidance_cannot_pass(self):
        self.write(self.root, "CONTRIBUTING.md", GUIDES["CONTRIBUTING.md"] + "x" * 300_000)
        self.assertNotEqual("pass", self.check("contributing")["status"])

    def test_dependabot_can_satisfy_dependency_updates_without_renovate(self):
        (self.root / "renovate.json").unlink()
        self.write(self.root, ".github/dependabot.yaml", "version: 2\nupdates:\n - package-ecosystem: github-actions\n   directory: /\n   schedule:\n     interval: weekly\n")
        self.assertEqual("pass", self.check("dependency_updates")["status"])

    def test_cli_required_unknown_returns_nonzero_and_writes_report(self):
        policy_path = Path(self.temp.name) / "policy.json"
        policy_path.write_text(json.dumps(self.policy))
        output = Path(self.temp.name) / "report.json"
        with contextlib.redirect_stdout(io.StringIO()):
            code = audit.main(["--repository-dir", str(self.root), "--policy", str(policy_path), "--output", str(output)])
        self.assertEqual(1, code)
        report = json.loads(output.read_text())
        self.assertIn("discussion_templates", report["failures"])
        self.assertEqual(0o600, output.stat().st_mode & 0o777)

    def test_cli_cannot_overwrite_inspected_source(self):
        original = (self.root / "README.md").read_bytes()
        with contextlib.redirect_stderr(io.StringIO()):
            code = audit.main(["--repository-dir", str(self.root), "--output", str(self.root / "README.md")])
        self.assertEqual(2, code)
        self.assertEqual(original, (self.root / "README.md").read_bytes())

    def test_cli_cannot_overwrite_nonregular_output(self):
        output = Path(self.temp.name) / "pipe"
        os.mkfifo(output)
        with contextlib.redirect_stderr(io.StringIO()):
            code = audit.main(["--repository-dir", str(self.root), "--output", str(output)])
        self.assertEqual(2, code)

    def test_incomplete_declaration_is_rejected(self):
        self.write(self.root, ".github/community-bootstrap.json", '{"schema_version":1,"environment_configuration":false}')
        with self.assertRaises(ValueError):
            self.run_audit()

    def test_complete_central_policy_is_required_when_supplied(self):
        with self.assertRaises(ValueError):
            self.run_audit(policy={"schema_version": 1})

    def test_invalid_workflow_job_structure_fails(self):
        for job in (None, {}, {"runs-on": "ubuntu-latest", "steps": []}):
            with self.subTest(job=job):
                self.write(self.root, ".github/workflows/ci.yml", json.dumps({"on": "push", "jobs": {"test": job}}))
                self.assertEqual("fail", self.check("workflows")["status"])

    def test_invalid_devcontainer_backend_type_fails(self):
        self.policy["devcontainer"] = "required"
        for container in ({"image": None}, {"build": "Dockerfile"}, {"dockerComposeFile": []}):
            with self.subTest(container=container):
                self.write(self.root, ".devcontainer.json", json.dumps(container))
                self.assertEqual("fail", self.check("devcontainer")["status"])

    def test_cli_normalizes_relative_parent_paths_without_overwriting_source(self):
        parent = Path(self.temp.name)
        (parent / "policy.json").write_text(json.dumps(self.policy), encoding="utf-8")
        (parent / "metadata.json").write_text(json.dumps(self.metadata), encoding="utf-8")
        original = (self.root / "README.md").read_bytes()
        previous = Path.cwd()
        try:
            os.chdir(self.root)
            with contextlib.redirect_stdout(io.StringIO()):
                code = audit.main([
                    "--repository-dir", "../repository",
                    "--metadata", "../metadata.json",
                    "--policy", "../policy.json",
                    "--output", "../report.json",
                ])
        finally:
            os.chdir(previous)
        self.assertEqual(0, code)
        self.assertTrue(json.loads((parent / "report.json").read_text())["conformant"])
        self.assertEqual(original, (self.root / "README.md").read_bytes())


    def test_local_copilot_guidance_covers_missing_root_agents(self):
        (self.root / "AGENTS.md").unlink()
        self.write(self.root, ".github/copilot-instructions.md", GUIDES["AGENTS.md"])
        self.write(self.defaults, "AGENTS.md", "Incomplete default instructions.")
        result = self.check("agents")
        self.assertEqual("pass", result["status"])
        self.assertEqual("local", result["source"])
        self.assertEqual([".github/copilot-instructions.md"], result["paths"])

    def test_root_agents_precedes_copilot_and_neither_inherits(self):
        self.write(self.root, ".github/copilot-instructions.md", GUIDES["AGENTS.md"])
        self.assertEqual(["AGENTS.md"], self.check("agents")["paths"])
        self.write(self.root, "AGENTS.md", "# Agent instructions\nIncomplete local guidance.\n")
        result = self.check("agents")
        self.assertEqual("fail", result["status"])
        self.assertEqual(["AGENTS.md"], result["paths"])
        for path in ("AGENTS.md", ".github/copilot-instructions.md"):
            (self.root / path).unlink()
            self.write(self.defaults, path, GUIDES["AGENTS.md"])
        result = self.check("agents")
        self.assertEqual("fail", result["status"])
        self.assertEqual("missing", result["source"])

    def test_invalid_nested_workflow_runner_and_step_shapes_fail(self):
        jobs = [
            {"runs-on": {"labels": None}, "steps": [{"run": "echo checked"}]},
            {"runs-on": {"group": None, "labels": "ubuntu-latest"}, "steps": [{"run": "echo checked"}]},
            {"runs-on": {"labels": []}, "steps": [{"run": "echo checked"}]},
            {"runs-on": {"labels": ["ubuntu-latest", None]}, "steps": [{"run": "echo checked"}]},
            {"uses": "./.github/workflows/reusable.yml", "runs-on": "ubuntu-latest"},
            {"uses": "./.github/workflows/reusable.yml", "runs-on": None},
            {"runs-on": "ubuntu-latest", "steps": [{"run": "echo checked", "uses": None}]},
            {"runs-on": "ubuntu-latest", "steps": [{"run": None, "uses": "actions/checkout@v4"}]},
            {"runs-on": "ubuntu-latest", "steps": [{"run": None}]},
        ]
        for job in jobs:
            with self.subTest(job=job):
                self.write(self.root, ".github/workflows/ci.yml", json.dumps({"on": "push", "jobs": {"test": job}}))
                self.assertEqual("fail", self.check("workflows")["status"])

    def test_supported_mapping_runner_and_reusable_job_shapes_pass(self):
        jobs = [
            {"runs-on": {"group": "standard-runners"}, "steps": [{"run": "echo checked"}]},
            {"runs-on": {"labels": "ubuntu-latest"}, "steps": [{"uses": "actions/checkout@v4"}]},
            {"runs-on": {"group": "standard-runners", "labels": ["linux", "x64"]}, "steps": [{"run": "echo checked"}]},
            {"uses": "./.github/workflows/reusable.yml"},
        ]
        for job in jobs:
            with self.subTest(job=job):
                self.write(self.root, ".github/workflows/ci.yml", json.dumps({"on": "push", "jobs": {"test": job}}))
                self.assertEqual("pass", self.check("workflows")["status"])

    def test_supplied_devcontainer_build_fields_require_nonempty_strings(self):
        self.policy["devcontainer"] = "required"
        for field in ("dockerfile", "context", "target"):
            for value in (None, "", [], 42):
                with self.subTest(field=field, value=value):
                    build = {"dockerfile": "Dockerfile", field: value}
                    self.write(self.root, ".devcontainer.json", json.dumps({"build": build}))
                    self.assertEqual("fail", self.check("devcontainer")["status"])
        self.write(self.root, ".devcontainer.json", json.dumps({"build": {
            "dockerfile": "Dockerfile", "context": ".", "target": "development",
        }}))
        self.assertEqual("pass", self.check("devcontainer")["status"])

    def test_cli_bounds_both_json_configuration_inputs(self):
        parent = Path(self.temp.name)
        metadata_path, policy_path = parent / "metadata.json", parent / "policy.json"
        for oversized in (metadata_path, policy_path):
            with self.subTest(input=oversized.name):
                metadata_path.write_text(json.dumps(self.metadata), encoding="utf-8")
                policy_path.write_text(json.dumps(self.policy), encoding="utf-8")
                with oversized.open("a", encoding="utf-8") as stream:
                    stream.write(" " * (audit.MAX_BYTES + 1))
                with contextlib.redirect_stderr(io.StringIO()), contextlib.redirect_stdout(io.StringIO()):
                    code = audit.main([
                        "--repository-dir", str(self.root),
                        "--metadata", str(metadata_path),
                        "--policy", str(policy_path),
                    ])
                self.assertEqual(2, code)

    def test_cli_rejects_configuration_directory_swapped_for_symlink(self):
        parent = Path(self.temp.name)
        configuration, displaced, outside = parent / "configuration", parent / "displaced", parent / "outside"
        configuration.mkdir()
        outside.mkdir()
        for directory in (configuration, outside):
            (directory / "metadata.json").write_text(json.dumps(self.metadata), encoding="utf-8")
        policy_path = parent / "policy.json"
        policy_path.write_text(json.dumps(self.policy), encoding="utf-8")
        original_open = audit.directory_descriptors

        def swap_parent(directory, **kwargs):
            if Path(directory) == configuration and not displaced.exists():
                configuration.rename(displaced)
                configuration.symlink_to(outside, target_is_directory=True)
            return original_open(directory, **kwargs)

        with patch.object(audit, "directory_descriptors", side_effect=swap_parent):
            with contextlib.redirect_stderr(io.StringIO()), contextlib.redirect_stdout(io.StringIO()):
                code = audit.main([
                    "--repository-dir", str(self.root),
                    "--metadata", str(configuration / "metadata.json"),
                    "--policy", str(policy_path),
                ])
        self.assertTrue(configuration.is_symlink())
        self.assertEqual(2, code)



if __name__ == "__main__":
    unittest.main()
