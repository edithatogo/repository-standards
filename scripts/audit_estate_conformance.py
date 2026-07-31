#!/usr/bin/env python3
"""Measure repository-estate conformance and reconcile a bounded central issue."""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, date, datetime
from pathlib import Path
from threading import Lock
from typing import Any


API = "https://api.github.com"
START = "<!-- estate-conformance:start -->"
END = "<!-- estate-conformance:end -->"
ACTION_REF = re.compile(r"(?m)^\s*uses:\s*([^#\s]+)")
FULL_SHA = re.compile(r"@[0-9a-f]{40}$", re.I)
SCHEDULE = re.compile(r"(?m)^\s*schedule\s*:")


class GitHub:
    def __init__(self, token: str) -> None:
        self.headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "User-Agent": "estate-conformance-audit",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        self._action_resolution: dict[str, bool] = {}
        self._action_resolution_lock = Lock()
        self._metrics_lock = Lock()
        self.metrics = {"requests": 0, "retries": 0, "tolerated_errors": 0}

    def request(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
        *,
        tolerated: set[int] | None = None,
    ) -> Any:
        data = None if payload is None else json.dumps(payload).encode()
        request = urllib.request.Request(
            f"{API}{path}",
            data=data,
            method=method,
            headers=self.headers,
        )
        tolerated = tolerated or {404, 409, 422}
        for attempt in range(4):
            with self._metrics_lock:
                self.metrics["requests"] += 1
            try:
                with urllib.request.urlopen(request, timeout=60) as response:
                    content = response.read()
                    return json.loads(content) if content else None
            except urllib.error.HTTPError as error:
                if error.code in tolerated:
                    with self._metrics_lock:
                        self.metrics["tolerated_errors"] += 1
                    return None
                if error.code not in {429, 500, 502, 503, 504} or attempt == 3:
                    raise
            except (TimeoutError, urllib.error.URLError):
                if attempt == 3:
                    raise
            with self._metrics_lock:
                self.metrics["retries"] += 1
            time.sleep(2**attempt)
        raise RuntimeError("unreachable retry state")

    def get(self, path: str, *, tolerated: set[int] | None = None) -> Any:
        return self.request("GET", path, tolerated=tolerated)

    def tree(self, repository: str, branch: str) -> list[dict[str, Any]]:
        result = self.get(
            f"/repos/{repository}/git/trees/"
            f"{urllib.parse.quote(branch, safe='')}?recursive=1"
        )
        return [] if not result else result.get("tree", [])

    def text(self, repository: str, path: str, branch: str) -> str:
        result = self.get(
            f"/repos/{repository}/contents/{urllib.parse.quote(path, safe='/')}"
            f"?ref={urllib.parse.quote(branch, safe='')}"
        )
        if not result or result.get("encoding") != "base64":
            return ""
        return base64.b64decode(result["content"]).decode("utf-8", errors="replace")

    def action_ref_resolves(self, ref: str) -> bool:
        """Verify an immutable marketplace action SHA exists in its source repo."""
        if not FULL_SHA.search(ref):
            return False
        action, sha = ref.rsplit("@", 1)
        parts = action.split("/")
        if len(parts) < 2:
            return False
        key = f"{parts[0]}/{parts[1]}@{sha.lower()}"
        with self._action_resolution_lock:
            cached = self._action_resolution.get(key)
        if cached is not None:
            return cached
        result = self.get(
            f"/repos/{parts[0]}/{parts[1]}/git/commits/{sha}",
            tolerated={404, 409, 422},
        )
        resolved = bool(result and result.get("sha", "").lower() == sha.lower())
        with self._action_resolution_lock:
            self._action_resolution[key] = resolved
        return resolved


def inherited_profile(name: str, profiles: dict[str, Any]) -> dict[str, Any]:
    current = dict(profiles[name])
    parent = current.pop("extends", None)
    return {**(inherited_profile(parent, profiles) if parent else {}), **current}


def present(paths: set[str], patterns: tuple[str, ...]) -> bool:
    lowered = {path.casefold() for path in paths}
    return any(
        candidate in lowered
        or any(path.endswith(candidate) for path in lowered)
        for candidate in patterns
    )


def active_exception(entry: dict[str, Any], control: str) -> bool:
    today = date.today()
    for exception in entry.get("exceptions", []):
        if exception.get("control") != control:
            continue
        try:
            return date.fromisoformat(exception["review_after"]) >= today
        except (KeyError, ValueError):
            return False
    return False


def exception_dates(entry: dict[str, Any]) -> tuple[list[str], list[str]]:
    """Return expired and soon-to-expire exception control names."""
    today = date.today()
    expired: list[str] = []
    upcoming: list[str] = []
    for exception in entry.get("exceptions", []):
        control = exception.get("control", "unknown")
        try:
            review_after = date.fromisoformat(exception["review_after"])
        except (KeyError, ValueError):
            expired.append(control)
            continue
        if review_after < today:
            expired.append(control)
        elif (review_after - today).days <= 30:
            upcoming.append(control)
    return sorted(set(expired)), sorted(set(upcoming))


def audit_one(
    client: GitHub,
    entry: dict[str, Any],
    profiles_document: dict[str, Any],
    managed_document: dict[str, Any],
) -> dict[str, Any]:
    repository = entry["repository"]
    branch = entry["default_branch"]
    tree = client.tree(repository, branch)
    paths = {item["path"] for item in tree if item.get("type") == "blob"}
    workflow_paths = sorted(
        path
        for path in paths
        if re.match(r"^\.github/workflows/[^/]+\.ya?ml$", path, re.I)
    )
    workflow_texts = [
        client.text(repository, path, branch) for path in workflow_paths
    ]
    workflow = "\n".join(workflow_texts)
    action_refs = [
        match.group(1)
        for match in ACTION_REF.finditer(workflow)
        if not match.group(1).startswith(("./", "docker://"))
    ]
    unpinned = [ref for ref in action_refs if not FULL_SHA.search(ref)]
    invalid_pins = [
        ref
        for ref in action_refs
        if FULL_SHA.search(ref) and not client.action_ref_resolves(ref)
    ]
    scheduled = bool(SCHEDULE.search(workflow))
    scheduled_run = None
    if scheduled:
        scheduled_run = client.get(
            f"/repos/{repository}/actions/runs?event=schedule&status=completed&per_page=1"
        )
    last_schedule = (
        scheduled_run.get("workflow_runs", [None])[0]
        if scheduled_run and scheduled_run.get("workflow_runs")
        else None
    )
    schedule_fresh = bool(
        not scheduled
        or (
            last_schedule
            and last_schedule.get("created_at")
            and (
                datetime.now(UTC)
                - datetime.fromisoformat(last_schedule["created_at"].replace("Z", "+00:00"))
            ).days <= 8
        )
    )
    expired_exceptions, upcoming_exceptions = exception_dates(entry)
    rulesets = client.get(
        f"/repos/{repository}/rulesets?includes_parents=false",
        tolerated={403, 404},
    )
    ruleset_state = (
        "unknown" if rulesets is None else ("present" if rulesets else "absent")
    )

    profile_name = entry["profile"]
    profile = inherited_profile(profile_name, profiles_document["profiles"])
    executable = bool(profile.get("executable"))
    supply_chain_profile = entry.get(
        "supply_chain_profile", profile.get("supply_chain", "baseline")
    )
    scorecard_applicable = (
        entry.get("visibility", "").casefold() == "public"
        and supply_chain_profile in {"published", "high_risk"}
    )
    managed = {
        item["path"]: item["path"] in paths
        for item in managed_document["files"]
        if "*" in item["profiles"] or profile_name in item["profiles"]
        if item["path"] != ".github/workflows/scorecard.yml" or scorecard_applicable
    }
    controls = {
        "workflow_present": bool(workflow_paths),
        "explicit_permissions": bool(re.search(r"(?m)^permissions\s*:", workflow)),
        "concurrency_cancellation": bool(
            re.search(r"(?m)^concurrency\s*:", workflow)
            and "cancel-in-progress" in workflow
        ),
        "job_timeouts": "timeout-minutes:" in workflow,
        "immutable_action_pins": bool(action_refs) and not unpinned,
        "resolvable_action_pins": bool(action_refs) and not unpinned and not invalid_pins,
        "ruleset": ruleset_state == "present",
        "harness": present(
            paths,
            (
                "makefile",
                "justfile",
                "taskfile.yml",
                "taskfile.yaml",
                "tox.ini",
                "noxfile.py",
                "scripts/verify.py",
                "scripts/verify.ps1",
                "scripts/validate.py",
                "scripts/validate.ps1",
            ),
        ),
        "verification_receipt": any(
            re.search(r"(verification|validation)[-_]receipt.*\.json$", path, re.I)
            for path in paths
        )
        or "verification-receipt" in workflow,
        "agents": "AGENTS.md" in paths,
        "codeql": any("codeql" in path.casefold() for path in workflow_paths)
        or "github/codeql-action" in workflow,
        "dependency_review": "actions/dependency-review-action" in workflow,
        "scorecard": "ossf/scorecard-action" in workflow,
        "sbom": bool(re.search(r"\b(sbom|syft|cyclonedx|spdx)\b", workflow, re.I))
        or present(paths, ("sbom.json", "sbom.spdx.json", "bom.json")),
        "provenance": "attest-build-provenance" in workflow
        or "slsa-framework" in workflow,
        "checksums": present(
            paths,
            ("checksums.sha256", "sha256sums", "checksums.txt"),
        )
        or bool(re.search(r"\bsha256(sum)?\b", workflow, re.I)),
        "signed_release": bool(
            re.search(r"\b(cosign|sigstore|gpg|signed.tag)\b", workflow, re.I)
        ),
        "changelog": present(paths, ("changelog.md", "changes.md", "news.md")),
        "release_workflow": any(
            re.search(r"(release|publish|deploy)", path, re.I)
            for path in workflow_paths
        ),
        "build_publish_separated": bool(
            re.search(r"(workflow_dispatch|tags:)", workflow)
            and re.search(r"(publish|release|deploy)", workflow, re.I)
        ),
        "rollback": any("rollback" in path.casefold() for path in paths),
        "schedule_success": bool(
            not scheduled or (last_schedule and last_schedule.get("conclusion") == "success")
        ),
        "schedule_freshness": schedule_fresh,
        "exceptions_current": not expired_exceptions,
        "data_governance": all(
            [
                present(paths, ("rights.md", "license", "licence")),
                any("schema" in path.casefold() for path in paths),
                any(
                    term in path.casefold()
                    for path in paths
                    for term in ("source-manifest", "sources.json", "provenance")
                ),
            ]
        ),
        "deterministic_seed": bool(
            re.search(r"\b(seed|random_seed|rng)\b", workflow, re.I)
        )
        or any("seed" in path.casefold() for path in paths),
        "flaky_governance": bool(
            re.search(r"\b(quarantine|flaky|retry|rerun)\b", workflow, re.I)
        )
        or any(
            term in path.casefold()
            for path in paths
            for term in ("quarantine", "flaky", "retry-policy")
        ),
        "performance_governance": any(
            term in path.casefold()
            for path in paths
            for term in ("benchmark", "performance-budget", "regression-budget")
        ),
        "lifecycle_classified": entry.get("canonical_status") != "review_required",
        "release_classified": entry.get("release_maturity") != "review_required",
        "maintenance_classified": entry.get("maintenance_tier") != "review_required",
    }
    controls.update({f"managed:{path}": state for path, state in managed.items()})

    required = [
        "workflow_present",
        "explicit_permissions",
        "concurrency_cancellation",
        "job_timeouts",
        "immutable_action_pins",
        "resolvable_action_pins",
        "ruleset",
        "agents",
        "lifecycle_classified",
        "release_classified",
        "maintenance_classified",
        "exceptions_current",
    ]
    if executable:
        required.extend(["harness", "verification_receipt", "deterministic_seed"])
    if profile.get("data_governance") == "required":
        required.append("data_governance")
    if profile.get("schedule_health") == "required" or scheduled:
        required.extend(["schedule_success", "schedule_freshness"])
    supply_chain = list(profiles_document["supply_chain_profiles"][
        supply_chain_profile
    ])
    if entry.get("visibility", "").casefold() != "public":
        supply_chain = [control for control in supply_chain if control != "scorecard"]
    required.extend(supply_chain)
    required.extend(f"managed:{path}" for path in managed)
    violations = sorted(
        {
            control
            for control in required
            if not controls.get(control, False)
            and not active_exception(entry, control)
        }
    )
    return {
        "repository": repository,
        "profile": profile_name,
        "workflow_count": len(workflow_paths),
        "workflow_paths": workflow_paths,
        "unpinned_actions": unpinned,
        "invalid_action_pins": invalid_pins,
        "ruleset": ruleset_state,
        "scheduled": scheduled,
        "last_scheduled_run": (
            None
            if not last_schedule
            else {
                "conclusion": last_schedule.get("conclusion"),
                "created_at": last_schedule.get("created_at"),
                "url": last_schedule.get("html_url"),
            }
        ),
        "controls": controls,
        "violations": violations,
        "exception_count": len(entry.get("exceptions", [])),
        "expired_exceptions": expired_exceptions,
        "upcoming_exceptions": upcoming_exceptions,
    }


def summary_markdown(rows: list[dict[str, Any]], scope: str) -> str:
    def missing(control: str) -> int:
        return sum(control in row["violations"] for row in rows)

    workflow_absent = sum(not row["controls"]["workflow_present"] for row in rows)
    unpinned = sum(bool(row["unpinned_actions"]) for row in rows)
    invalid_pins = sum(bool(row["invalid_action_pins"]) for row in rows)
    lines = [
        START,
        "## Scheduled conformance status",
        "",
        f"Scope: **{scope}**. Repositories measured: **{len(rows)}**.",
        "",
        "| Control | Repositories requiring work |",
        "|---|---:|",
        f"| Workflow absent | {workflow_absent} |",
        f"| Explicit permissions | {missing('explicit_permissions')} |",
        f"| Concurrency/cancellation | {missing('concurrency_cancellation')} |",
        f"| Job timeouts | {missing('job_timeouts')} |",
        f"| Immutable action pins | {missing('immutable_action_pins')} ({unpinned} with detected floating refs) |",
        f"| Resolvable immutable pins | {missing('resolvable_action_pins')} ({invalid_pins} with invalid pins) |",
        f"| Ruleset/protection profile | {missing('ruleset')} |",
        f"| One-command harness | {missing('harness')} |",
        f"| Machine-readable verification receipt | {missing('verification_receipt')} |",
        f"| Repository AGENTS.md | {missing('agents')} |",
        f"| Deterministic seed evidence | {missing('deterministic_seed')} |",
        f"| Scheduled-run success evidence | {missing('schedule_success')} |",
        f"| Scheduled-run freshness | {missing('schedule_freshness')} |",
        f"| Expired or invalid exceptions | {missing('exceptions_current')} |",
        f"| Lifecycle classification | {missing('lifecycle_classified')} |",
        f"| Release maturity classification | {missing('release_classified')} |",
        "",
        "Highest-gap repositories:",
        "",
    ]
    for row in sorted(rows, key=lambda item: (-len(item["violations"]), item["repository"]))[:20]:
        lines.append(f"- `{row['repository']}` ({row['profile']}): {len(row['violations'])}")
    lines.extend(
        [
            "",
            "The attached JSON is authoritative for exact controls and exceptions.",
            f"Generated: {datetime.now(UTC).isoformat(timespec='seconds')}.",
            END,
        ]
    )
    return "\n".join(lines)


def reconcile_issue(
    issue_client: GitHub,
    repository: str,
    number: int,
    generated: str,
) -> str:
    issue = issue_client.get(f"/repos/{repository}/issues/{number}")
    if not issue:
        raise RuntimeError(f"Issue {repository}#{number} not found")
    body = issue.get("body") or ""
    if START in body and END in body:
        before = body.split(START, 1)[0].rstrip()
        after = body.split(END, 1)[1].lstrip()
        updated = f"{before}\n\n{generated}"
        if after:
            updated += f"\n\n{after}"
    else:
        updated = f"{body.rstrip()}\n\n{generated}"
    result = issue_client.request(
        "PATCH",
        f"/repos/{repository}/issues/{number}",
        {"body": updated},
        tolerated=set(),
    )
    return result["html_url"]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--registry", type=Path, required=True)
    parser.add_argument("--profiles", type=Path, required=True)
    parser.add_argument("--managed-files", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--issue-repository")
    parser.add_argument("--issue-number", type=int)
    args = parser.parse_args()
    audit_token = os.environ.get("ESTATE_AUDIT_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not audit_token:
        print("ESTATE_AUDIT_TOKEN or GITHUB_TOKEN is required", file=sys.stderr)
        return 2
    registry = json.loads(args.registry.read_text(encoding="utf-8-sig"))
    profiles = json.loads(args.profiles.read_text(encoding="utf-8-sig"))
    managed = json.loads(args.managed_files.read_text(encoding="utf-8-sig"))
    client = GitHub(audit_token)
    with ThreadPoolExecutor(max_workers=10) as executor:
        rows = list(
            executor.map(
                lambda entry: audit_one(client, entry, profiles, managed),
                registry["repositories"],
            )
        )
    scope = registry.get("scope", "registry-defined active repositories")
    generated = summary_markdown(rows, scope)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "scope": scope,
        "repository_count": len(rows),
        "repositories": rows,
        "telemetry": client.metrics,
    }
    (args.output_dir / "estate-conformance.json").write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )
    (args.output_dir / "estate-conformance.md").write_text(
        generated + "\n",
        encoding="utf-8",
    )
    issue_url = None
    issue_token = os.environ.get("ISSUE_TOKEN")
    if args.issue_repository and args.issue_number and issue_token:
        issue_url = reconcile_issue(
            GitHub(issue_token),
            args.issue_repository,
            args.issue_number,
            generated,
        )
    print(
        json.dumps(
            {
                "repositories": len(rows),
                "issue": issue_url,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
