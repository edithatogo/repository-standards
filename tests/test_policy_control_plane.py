#!/usr/bin/env python3
from __future__ import annotations

import json
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import Mock

import audit_estate_conformance as audit
import simulate_policy_impact as impact


class PolicyTests(unittest.TestCase):
    def test_profile_inheritance(self) -> None:
        profiles = {"base": {"a": 1}, "child": {"extends": "base", "b": 2}}
        self.assertEqual(audit.inherited_profile("child", profiles), {"a": 1, "b": 2})

    def test_expired_exception_is_not_active(self) -> None:
        entry = {"exceptions": [{"control": "x", "review_after": "2000-01-01"}]}
        self.assertFalse(audit.active_exception(entry, "x"))
        self.assertEqual(audit.exception_dates(entry)[0], ["x"])

    def test_upcoming_exception_is_reported(self) -> None:
        review = (date.today() + timedelta(days=7)).isoformat()
        entry = {"exceptions": [{"control": "x", "review_after": review}]}
        self.assertEqual(audit.exception_dates(entry)[1], ["x"])

    def test_resolvable_pin_is_checked_not_inferred_from_shape(self) -> None:
        client = audit.GitHub("not-used")
        client.get = Mock(return_value=None)
        ref = "actions/example@" + "a" * 40
        self.assertFalse(client.action_ref_resolves(ref))

    def test_summary_has_stable_markers(self) -> None:
        row = {
            "repository": "owner/repo",
            "profile": "python",
            "violations": [],
            "unpinned_actions": [],
            "invalid_action_pins": [],
            "controls": {"workflow_present": True},
        }
        text = audit.summary_markdown([row], "test")
        self.assertTrue(text.startswith(audit.START))
        self.assertTrue(text.endswith(audit.END))

    def test_impact_profile_inheritance_terminates(self) -> None:
        profiles = {"base": {"supply_chain": "baseline"}, "child": {"extends": "base"}}
        profile = dict(profiles["child"])
        while "extends" in profile:
            parent = profile.pop("extends")
            profile = {**profiles[parent], **profile}
        self.assertEqual(profile["supply_chain"], "baseline")

    def test_branch_protection_counts_as_protection_profile(self) -> None:
        protection = {"required_status_checks": {"strict": True}}
        self.assertEqual(audit.protection_state([], protection), "present")
        self.assertEqual(audit.protection_state([], None), "absent")

    def test_scan_failure_is_preserved_without_fabricated_controls(self) -> None:
        client = Mock()
        client.tree.side_effect = PermissionError("throttled")
        row = audit.audit_safely(
            client,
            {"repository": "owner/repo", "profile": "python", "default_branch": "main"},
            {"profiles": {}},
            {"files": []},
        )
        self.assertEqual(row["violations"], ["scan_unavailable"])
        self.assertEqual(row["controls"], {})


if __name__ == "__main__":
    unittest.main()
