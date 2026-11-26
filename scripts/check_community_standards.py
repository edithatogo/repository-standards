"""Narrow community file gate; reuse the bootstrap auditor and observed public defaults."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
from urllib.parse import quote

# Only trusted action siblings are importable when invoked with Python -I.
sys.path.insert(0, str(Path(__file__).resolve().parent))
import audit_community_bootstrap as audit
from estate_evidence import API, NAME, SHA

ROOT = Path(__file__).resolve().parents[1]
LICENSE_NAMES = [name + extension for name in ("LICENSE", "LICENCE", "COPYING")
                 for extension in ("", ".md", ".txt", ".rst")]


def observe_defaults(api, repository, revision):
    """Bind the consumer identity to its owner's actually public defaults HEAD."""
    if not NAME.fullmatch(repository) or any(part in {".", ".."} for part in repository.split("/")) or not SHA.fullmatch(revision):
        raise ValueError("Invalid repository or revision")

    def get(path):
        reply = api.get(path)
        if reply.status != 200 or reply.reason or not isinstance(reply.value, dict):
            raise ValueError("GitHub metadata unavailable")
        return reply.value

    consumer = get("/repos/" + repository)
    if consumer.get("full_name", "").casefold() != repository.casefold():
        raise ValueError("Consumer identity mismatch")
    defaults_repository = repository.split("/")[0] + "/.github"
    defaults = get("/repos/" + defaults_repository)
    if (defaults.get("full_name", "").casefold() != defaults_repository.casefold()
            or defaults.get("private") is not False or defaults.get("visibility") != "public"):
        raise ValueError("Account defaults must be observed public")
    branch = defaults.get("default_branch")
    if not audit.nonempty(branch):
        raise ValueError("Default branch is unavailable")
    reference = get("/repos/" + defaults_repository + "/git/ref/heads/" + quote(branch, safe=""))
    target = reference.get("object", {})
    if (reference.get("ref") != "refs/heads/" + branch or not isinstance(target, dict)
            or target.get("type") != "commit" or not SHA.fullmatch(str(target.get("sha", "")))):
        raise ValueError("Default revision is unavailable")
    return {
        "repository": repository, "revision": revision,
        "defaults_repository": defaults_repository, "defaults_revision": target["sha"],
        "defaults_visibility": "public", "has_discussions": consumer.get("has_discussions"),
        "discussion_categories": None, "is_template": consumer.get("is_template"),
    }


def verify_checkout(directory, repository, revision):
    """Verify clean SHA/origin provenance without invoking checkout-owned scripts."""
    tree = audit.Tree(directory)
    if tree.is_blocked(".git") or not NAME.fullmatch(repository) or not SHA.fullmatch(revision):
        raise ValueError("Invalid checkout provenance")

    def git(*arguments):
        return subprocess.check_output(
            ["git", "-c", "core.fsmonitor=false", "-C", str(tree.root), *arguments],
            text=True, stderr=subprocess.DEVNULL, timeout=20,
        ).strip()

    if git("rev-parse", "--show-toplevel") != str(tree.root) or git("rev-parse", "HEAD") != revision:
        raise ValueError("Checkout revision mismatch")
    origin = git("config", "--get", "remote.origin.url").casefold()
    expected = "https://github.com/" + repository.casefold()
    if origin not in {expected, expected + ".git"} or git("status", "--porcelain", "--untracked-files=all"):
        raise ValueError("Checkout origin mismatch or dirty snapshot")


def audit_native_repository(repository_dir, *, defaults_dir, metadata):
    policy = json.loads(audit.bounded_text(ROOT / "profiles", "native-community.json"))
    result = audit.audit_repository(repository_dir, defaults_dir=defaults_dir, metadata=metadata, policy=policy)
    checks = {name: result["checks"][name] for name in audit.NATIVE_COMMUNITY_CONTROLS}
    local = audit.Tree(repository_dir)
    names = {name.casefold() for name in LICENSE_NAMES}
    candidates = sorted(path for path in local.paths | local.blocked
                        if Path(path).parent == Path(".") and Path(path).name.casefold() in names)
    present, details, unknown = [], [], False
    for path in candidates:
        try:
            if not audit.guidance_errors(local.read(path), "license", native=True):
                present.append(path)
            else:
                details.append(path + ": empty or placeholder local licence file")
        except audit.EvidenceError as error:
            unknown = unknown or error.status == "unknown"
            details.append(path + ": " + str(error))
    license_check = audit.record(
        "pass" if present else "unknown" if unknown else "fail",
        "local" if present or candidates else "missing", present or candidates,
        details if candidates else ["A repository-local licence file is required"],
    )
    checks["license"] = license_check
    failures = [name for name, check in checks.items() if check["status"] != "pass"]
    result.update(profile="native-community", checks=checks, failures=failures, conformant=not failures)
    result["limitations"].extend([
        "Licence presence only; no licence is selected, copied, interpreted or granted",
        "Candidate file gate; GitHub default-branch community score and merge requirements are separate",
    ])
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    observe = commands.add_parser("observe")
    observe.add_argument("--repository", required=True)
    observe.add_argument("--revision", required=True)
    check = commands.add_parser("audit")
    check.add_argument("--repository-dir", type=Path, required=True)
    check.add_argument("--defaults-dir", type=Path, required=True)
    check.add_argument("--metadata", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "observe":
            result = observe_defaults(API(os.environ.get("GITHUB_TOKEN", ""), max_requests=12), args.repository, args.revision)
            if os.environ.get("GITHUB_OUTPUT"):
                with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as output:
                    output.write("defaults-repository=" + result["defaults_repository"] + "\n")
                    output.write("defaults-revision=" + result["defaults_revision"] + "\n")
        else:
            metadata_path = args.metadata.absolute()
            metadata = json.loads(audit.bounded_text(metadata_path.parent, metadata_path.name))
            repository = metadata.get("repository", "")
            if (not NAME.fullmatch(repository) or metadata.get("defaults_visibility") != "public"
                    or metadata.get("defaults_repository") != repository.split("/")[0] + "/.github"):
                raise ValueError("Invalid observed account defaults")
            verify_checkout(args.repository_dir, repository, metadata.get("revision", ""))
            verify_checkout(args.defaults_dir, metadata["defaults_repository"], metadata.get("defaults_revision", ""))
            result = audit_native_repository(args.repository_dir, defaults_dir=args.defaults_dir, metadata=metadata)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result.get("conformant", True) else 1
    except (ValueError, OSError, subprocess.SubprocessError, TypeError, AttributeError):
        print(json.dumps({"conformant": False, "error": "community_standards_invalid_input"}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
