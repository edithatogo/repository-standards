"""Public community policy/declaration contracts must agree with runtime policy."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import unittest

import fastjsonschema

from audit_community_bootstrap import CONTROLS, validate_policy

ROOT = Path(__file__).resolve().parents[1]


class CommunityContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.policy = json.loads((ROOT / "profiles/community-bootstrap.json").read_text())
        cls.declaration = json.loads((ROOT / ".github/community-bootstrap.json").read_text())
        cls.policy_schema = staticmethod(fastjsonschema.compile(json.loads(
            (ROOT / "schemas/community-bootstrap-policy.schema.json").read_text()
        )))
        cls.declaration_schema = staticmethod(fastjsonschema.compile(json.loads(
            (ROOT / "schemas/community-bootstrap-declaration.schema.json").read_text()
        )))

    def test_committed_contracts_validate(self):
        self.policy_schema(copy.deepcopy(self.policy))
        self.declaration_schema(copy.deepcopy(self.declaration))
        validate_policy(copy.deepcopy(self.policy))

    def test_policy_requires_every_supported_control(self):
        self.assertEqual(set(self.policy["required"]), set(CONTROLS))
        self.assertEqual(self.policy["recommended"], [])

    def test_only_native_community_profile_allows_an_empty_role_mapping(self):
        narrow = json.loads((ROOT / "profiles/native-community.json").read_text())
        self.policy_schema(copy.deepcopy(narrow))
        validate_policy(copy.deepcopy(narrow))
        self.assertEqual(set(self.policy["issue_form_kinds"]), {"bug", "feature", "documentation"})
        for invalid in (
            {**self.policy, "issue_form_kinds": {}},
            {**narrow, "required": narrow["required"][:-1]},
            {**narrow, "recommended": ["agents"]},
        ):
            with self.subTest(required=invalid["required"]):
                with self.assertRaises(fastjsonschema.JsonSchemaException):
                    self.policy_schema(copy.deepcopy(invalid))
                with self.assertRaises(ValueError):
                    validate_policy(copy.deepcopy(invalid))

    def test_unknown_control_is_rejected(self):
        policy = copy.deepcopy(self.policy)
        policy["required"].append("unknown_future_control")
        with self.assertRaises(fastjsonschema.JsonSchemaException):
            self.policy_schema(policy)

    def test_local_declaration_cannot_replace_required_controls(self):
        declaration = copy.deepcopy(self.declaration)
        declaration["required"] = []
        with self.assertRaises(fastjsonschema.JsonSchemaException):
            self.declaration_schema(declaration)

    def test_applicability_needs_substantive_rationale(self):
        declaration = copy.deepcopy(self.declaration)
        declaration["rationale"]["environment_configuration"] = ""
        with self.assertRaises(fastjsonschema.JsonSchemaException):
            self.declaration_schema(declaration)

    def test_string_boolean_is_rejected(self):
        declaration = copy.deepcopy(self.declaration)
        declaration["environment_configuration"] = "false"
        with self.assertRaises(fastjsonschema.JsonSchemaException):
            self.declaration_schema(declaration)

    def test_boolean_is_not_a_contract_version(self):
        for document, validate in (
            (self.policy, self.policy_schema),
            (self.declaration, self.declaration_schema),
        ):
            with self.subTest(document="policy" if document is self.policy else "declaration"):
                invalid = copy.deepcopy(document)
                invalid["schema_version"] = True
                with self.assertRaises(fastjsonschema.JsonSchemaException):
                    validate(invalid)

    def test_manifest_and_archetypes_link_the_same_contract(self):
        manifest = json.loads((ROOT / "managed-files/manifest.json").read_text())
        profiles = json.loads((ROOT / "profiles/archetype-profiles.json").read_text())
        self.assertEqual(
            manifest["community_bootstrap"]["policy"],
            profiles["defaults"]["community_bootstrap"]["policy"],
        )
        self.assertEqual(manifest["community_bootstrap"]["policy"],
                         "profiles/community-bootstrap.json")
        self.assertEqual(profiles["defaults"]["mandatory_human_approvals"], 0)
        self.assertEqual(
            profiles["defaults"]["community_bootstrap"]["mandatory_human_approvals"], 0
        )
        self.assertTrue(manifest["policy"]["never_force_overwrite"])


if __name__ == "__main__":
    unittest.main()
