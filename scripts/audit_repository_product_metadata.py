#!/usr/bin/env python3
"""Audit an owner's active GitHub repositories for product-metadata standards."""

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
from pathlib import Path
from typing import Any


API = "https://api.github.com"
README_SECTIONS = {
    "installation": re.compile(r"^#{1,3}\s+(installation|install|setup)\b", re.I | re.M),
    "usage": re.compile(r"^#{1,3}\s+(usage|quick ?start|getting started)\b", re.I | re.M),
    "development": re.compile(r"^#{1,3}\s+(development|developing|contributing)\b", re.I | re.M),
    "security": re.compile(r"^#{1,3}\s+security\b", re.I | re.M),
    "license": re.compile(r"^#{1,3}\s+licen[cs]e\b", re.I | re.M),
    "citation": re.compile(r"^#{1,3}\s+(citation|citing)\b", re.I | re.M),
}
LICENSE_NAMES = re.compile(
    r"(^|/)(license|licence|copying|copyright)(\.[^/]+)?$", re.I
)
CITATION_NAMES = {"citation.cff", "citation.bib", "codemeta.json", ".zenodo.json"}
EXECUTABLE_MARKERS = {
    "pyproject.toml",
    "setup.py",
    "setup.cfg",
    "requirements.txt",
    "cargo.toml",
    "package.json",
    "go.mod",
    "pom.xml",
    "build.gradle",
    "build.gradle.kts",
    "composer.json",
    "gemfile",
    "mix.exs",
}
LOGGING_TERMS = re.compile(
    r"\b(structlog|logging|loguru|tracing|tracing-subscriber|pino|winston|"
    r"bunyan|serilog|nlog|slf4j|log4j|zap|zerolog)\b",
    re.I,
)
APP_TERMS = re.compile(
    r"\b(api|service|server|cli|command.line|pipeline|etl|daemon|worker|bot|"
    r"application|app|scraper|crawler|ingest)\b",
    re.I,
)


class GitHub:
    def __init__(self, token: str) -> None:
        self.headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "User-Agent": "repository-product-metadata-audit",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    def get(self, path: str) -> Any:
        request = urllib.request.Request(f"{API}{path}", headers=self.headers)
        for attempt in range(4):
            try:
                with urllib.request.urlopen(request, timeout=60) as response:
                    return json.load(response)
            except urllib.error.HTTPError as error:
                if error.code in {404, 409, 422}:
                    return None
                if error.code not in {429, 500, 502, 503, 504} or attempt == 3:
                    raise
            except (TimeoutError, urllib.error.URLError):
                if attempt == 3:
                    raise
            time.sleep(2**attempt)
        raise RuntimeError("unreachable retry state")

    def active_repositories(self, owner: str) -> list[dict[str, Any]]:
        repositories: list[dict[str, Any]] = []
        page = 1
        while True:
            query = urllib.parse.urlencode(
                {
                    "affiliation": "owner",
                    "per_page": 100,
                    "page": page,
                    "sort": "full_name",
                }
            )
            batch = self.get(f"/user/repos?{query}") or []
            repositories.extend(
                repository
                for repository in batch
                if repository["owner"]["login"].casefold() == owner.casefold()
                and not repository["fork"]
                and not repository["archived"]
            )
            if len(batch) < 100:
                break
            page += 1
        return sorted(repositories, key=lambda item: item["full_name"].casefold())

    def tree(self, repository: str, branch: str) -> list[dict[str, Any]]:
        encoded_branch = urllib.parse.quote(branch, safe="")
        result = self.get(
            f"/repos/{repository}/git/trees/{encoded_branch}?recursive=1"
        )
        return [] if not result else result.get("tree", [])

    def text(self, repository: str, path: str, branch: str) -> str:
        encoded = urllib.parse.quote(path, safe="/")
        result = self.get(
            f"/repos/{repository}/contents/{encoded}?ref="
            f"{urllib.parse.quote(branch, safe='')}"
        )
        if not result or result.get("encoding") != "base64":
            return ""
        return base64.b64decode(result["content"]).decode("utf-8", errors="replace")


def archetype(paths: set[str], description: str) -> str:
    lowered = {path.casefold() for path in paths}
    if "typst.toml" in lowered or any(path.endswith(".typ") for path in lowered):
        return "typesetting"
    if any(path.endswith(".tex") for path in lowered):
        return "typesetting"
    if "mkdocs.yml" in lowered or "docs" in {path.split("/", 1)[0] for path in lowered}:
        if not lowered.intersection(EXECUTABLE_MARKERS):
            return "documentation"
    if "data" in {path.split("/", 1)[0] for path in lowered} and (
        "dataset" in description.casefold() or "corpus" in description.casefold()
    ):
        return "data"
    if lowered.intersection(EXECUTABLE_MARKERS):
        return "software"
    return "documentation"


def badge_state(readme: str) -> dict[str, bool | int]:
    lowered = readme.casefold()
    return {
        "count": len(re.findall(r"!\[[^\]]*]\([^)]*(?:badge|shields|actions)[^)]*\)", readme, re.I)),
        "ci": "actions/workflows" in lowered or "github/workflow/status" in lowered,
        "coverage": "codecov" in lowered or "coveralls" in lowered,
        "license": "license-" in lowered or "/license" in lowered,
        "citation": "citation.cff" in lowered or "doi.org" in lowered or "zenodo" in lowered,
        "version": "version-" in lowered or "/v/release" in lowered or "/v/tag" in lowered,
    }


def version_state(files: dict[str, str], kind: str) -> dict[str, Any]:
    pyproject = files.get("pyproject.toml", "")
    cargo = files.get("cargo.toml", "")
    package = files.get("package.json", "")
    typst = files.get("typst.toml", "")
    citation = files.get("citation.cff", "")
    source = "not_applicable"
    manifest_version: str | None = None
    dynamic = False
    if pyproject:
        match = re.search(r'(?m)^\s*version\s*=\s*"([^"]+)"', pyproject)
        manifest_version = match.group(1) if match else None
        dynamic = bool(
            re.search(r'(?s)dynamic\s*=\s*\[[^\]]*"version"', pyproject)
            and re.search(r"hatch-vcs|setuptools[-_]scm|versioningit|pdm-backend", pyproject, re.I)
        )
        source = "git_tags_dynamic" if dynamic else "pyproject_manifest"
    elif cargo:
        match = re.search(r'(?m)^\s*version\s*=\s*"([^"]+)"', cargo)
        manifest_version = match.group(1) if match else None
        source = "cargo_manifest"
    elif package:
        try:
            manifest_version = json.loads(package).get("version")
        except json.JSONDecodeError:
            manifest_version = None
        source = "package_manifest"
    elif typst:
        match = re.search(r'(?m)^\s*version\s*=\s*"([^"]+)"', typst)
        manifest_version = match.group(1) if match else None
        source = "typst_manifest"
    elif kind in {"documentation", "typesetting", "data"}:
        source = "release_tags_or_doi"

    citation_match = re.search(r'(?m)^version:\s*["\']?([^"\'\s]+)', citation)
    citation_version = citation_match.group(1) if citation_match else None
    return {
        "source": source,
        "dynamic": dynamic,
        "manifest_version": manifest_version,
        "citation_version": citation_version,
        "drift": bool(
            manifest_version
            and citation_version
            and manifest_version != citation_version
        ),
    }


def audit_repository(client: GitHub, repository: dict[str, Any]) -> dict[str, Any]:
    full_name = repository["full_name"]
    branch = repository.get("default_branch") or "main"
    tree = client.tree(full_name, branch)
    paths = {item["path"] for item in tree if item.get("type") == "blob"}
    lowered_paths = {path.casefold(): path for path in paths}
    description = repository.get("description") or ""
    kind = archetype(paths, description)

    readme_path = next(
        (actual for lowered, actual in lowered_paths.items() if lowered in {"readme.md", "readme.rst", "readme"}),
        "",
    )
    candidate_names = [
        readme_path,
        lowered_paths.get("citation.cff", ""),
        lowered_paths.get("pyproject.toml", ""),
        lowered_paths.get("cargo.toml", ""),
        lowered_paths.get("package.json", ""),
        lowered_paths.get("typst.toml", ""),
    ]
    files = {
        path.casefold(): client.text(full_name, path, branch)
        for path in candidate_names
        if path
    }
    readme = files.get(readme_path.casefold(), "") if readme_path else ""
    badges = badge_state(readme)
    citation_files = sorted(
        path for path in paths if path.casefold().rsplit("/", 1)[-1] in CITATION_NAMES
    )
    license_files = sorted(path for path in paths if LICENSE_NAMES.search(path))
    executable = bool({path.casefold() for path in paths}.intersection(EXECUTABLE_MARKERS))
    logging_warranted = kind in {"software", "data"} and executable and bool(
        APP_TERMS.search(f"{repository['name']} {description}")
        or any(
            path.casefold().startswith(("src/", "app/", "cmd/", "scripts/"))
            for path in paths
        )
    )
    manifest_text = "\n".join(
        files.get(name, "")
        for name in ("pyproject.toml", "cargo.toml", "package.json")
    )
    logging_detected = bool(
        LOGGING_TERMS.search(manifest_text)
        or any(
            re.search(r"(^|/)(logging|logger|telemetry|observability)(\.|/)", path, re.I)
            for path in paths
        )
    )
    version = version_state(files, kind)
    citation_warranted = bool(paths) and kind in {
        "software",
        "data",
        "documentation",
        "typesetting",
    }
    readme_sections = {
        section: bool(pattern.search(readme))
        for section, pattern in README_SECTIONS.items()
    }
    gaps: list[str] = []
    if not readme_path:
        gaps.append("README missing")
    else:
        for section in ("usage", "development", "security", "license"):
            if not readme_sections[section]:
                gaps.append(f"README {section} section missing")
        if citation_warranted and not readme_sections["citation"]:
            gaps.append("README citation section missing")
        if not badges["ci"] and ".github/workflows" in {
            path.rsplit("/", 1)[0] for path in paths if "/" in path
        }:
            gaps.append("CI badge missing")
        if license_files and not badges["license"]:
            gaps.append("license badge missing")
        if citation_files and not badges["citation"]:
            gaps.append("citation badge missing")
    if not description.strip():
        gaps.append("GitHub description missing")
    if not repository.get("topics"):
        gaps.append("GitHub topics missing")
    if not license_files and repository.get("license") is None:
        gaps.append("license decision/file missing")
    if citation_warranted and not citation_files:
        gaps.append("citation metadata missing")
    if version["drift"]:
        gaps.append("manifest and citation versions disagree")
    if logging_warranted and not logging_detected:
        gaps.append("structured logging decision/implementation missing")

    return {
        "repository": full_name,
        "url": repository["html_url"],
        "visibility": repository.get("visibility"),
        "archetype": kind,
        "default_branch": branch,
        "description": description,
        "topics": repository.get("topics") or [],
        "readme": {
            "path": readme_path or None,
            "sections": readme_sections,
            "badges": badges,
        },
        "license": {
            "api_spdx": (repository.get("license") or {}).get("spdx_id"),
            "files": license_files,
            "present": bool(license_files or repository.get("license")),
        },
        "citation": {
            "warranted": citation_warranted,
            "files": citation_files,
            "present": bool(citation_files),
        },
        "versioning": version,
        "logging": {
            "warranted": logging_warranted,
            "detected": logging_detected,
        },
        "gaps": gaps,
    }


def markdown(rows: list[dict[str, Any]]) -> str:
    def count(predicate: Any) -> int:
        return sum(1 for row in rows if predicate(row))

    lines = [
        "# Repository product-metadata audit",
        "",
        f"Active, non-fork, non-archived repositories: **{len(rows)}**.",
        "",
        "## Summary",
        "",
        f"- Missing README: **{count(lambda row: not row['readme']['path'])}**",
        f"- Missing GitHub description: **{count(lambda row: not row['description'])}**",
        f"- Missing topics: **{count(lambda row: not row['topics'])}**",
        f"- Missing license decision/file: **{count(lambda row: not row['license']['present'])}**",
        f"- Citation warranted but absent: **{count(lambda row: row['citation']['warranted'] and not row['citation']['present'])}**",
        f"- Version drift detected: **{count(lambda row: row['versioning']['drift'])}**",
        f"- Logging warranted but not detected: **{count(lambda row: row['logging']['warranted'] and not row['logging']['detected'])}**",
        "",
        "## Repository findings",
        "",
        "| Repository | Archetype | Gaps |",
        "|---|---|---:|",
    ]
    for row in sorted(rows, key=lambda item: (-len(item["gaps"]), item["repository"])):
        lines.append(
            f"| [{row['repository']}]({row['url']}) | {row['archetype']} | "
            f"{len(row['gaps'])} |"
        )
    lines.extend(
        [
            "",
            "The machine-readable JSON contains the exact files, badge states, README",
            "sections, version sources, and logging applicability decisions.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--owner", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not token:
        print("GITHUB_TOKEN or GH_TOKEN is required", file=sys.stderr)
        return 2
    client = GitHub(token)
    repositories = client.active_repositories(args.owner)
    with ThreadPoolExecutor(max_workers=12) as executor:
        rows = list(
            executor.map(
                lambda repository: audit_repository(client, repository),
                repositories,
            )
        )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "repository-product-metadata-audit.json").write_text(
        json.dumps(
            {
                "owner": args.owner,
                "scope": "active non-fork non-archived owner repositories",
                "repositories": rows,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (args.output_dir / "repository-product-metadata-audit.md").write_text(
        markdown(rows),
        encoding="utf-8",
    )
    print(json.dumps({"repositories": len(rows)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
