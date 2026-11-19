#!/usr/bin/env python3
"""Download one published release SBOM by immutable asset ID and verify its digest."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path
from urllib.parse import quote


def select_asset(release: dict, filename: str) -> dict:
    if release.get("draft") or release.get("prerelease") or not release.get("published_at"):
        raise ValueError("expected a published stable release")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*\.json", filename):
        raise ValueError("sbom-asset must be one JSON filename")
    selected = [asset for asset in release.get("assets", []) if asset.get("name") == filename]
    if len(selected) != 1:
        raise ValueError("release must contain exactly one named SBOM asset")
    asset = selected[0]
    if not isinstance(asset.get("id"), int) or not re.fullmatch(r"sha256:[0-9a-f]{64}", asset.get("digest") or ""):
        raise ValueError("release asset lacks immutable ID or GitHub-provided SHA-256 digest")
    if not isinstance(asset.get("size"), int) or not 0 < asset["size"] <= 100 * 1024 * 1024:
        raise ValueError("release SBOM size is outside the supported bounds")
    return asset


def api(path: str) -> dict:
    result = subprocess.run(["gh", "api", path], check=True, capture_output=True, text=True, timeout=120)
    return json.loads(result.stdout)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--asset", required=True)
    parser.add_argument("--output-directory", type=Path, required=True)
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", args.repository):
        raise ValueError("invalid repository")
    output = args.output_directory.absolute()
    if output.is_symlink() or (output.exists() and any(output.iterdir())):
        raise ValueError("download directory must be new or empty")
    output.mkdir(parents=True, exist_ok=True)
    release = api(f"repos/{args.repository}/releases/latest")
    asset = select_asset(release, args.asset)
    ref = api(f"repos/{args.repository}/git/ref/tags/{quote(release['tag_name'], safe='')}")["object"]
    for _ in range(5):
        if ref["type"] == "commit":
            break
        if ref["type"] != "tag" or not re.fullmatch(r"[0-9a-f]{40}", ref["sha"]):
            raise ValueError("release tag did not resolve to a commit")
        ref = api(f"repos/{args.repository}/git/tags/{ref['sha']}")["object"]
    if ref["type"] != "commit" or not re.fullmatch(r"[0-9a-f]{40}", ref["sha"]):
        raise ValueError("release tag did not resolve to a commit")
    path = output / args.asset
    with path.open("wb") as stream:
        subprocess.run(["gh", "api", f"repos/{args.repository}/releases/assets/{asset['id']}",
                        "--header", "Accept: application/octet-stream"], stdout=stream, check=True, timeout=180)
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    if path.stat().st_size != asset["size"] or "sha256:" + actual != asset["digest"]:
        raise ValueError("downloaded release SBOM does not match the selected immutable asset")
    evidence = {"repository": args.repository, "release_id": release["id"], "tag": release["tag_name"],
                "observed_tag_commit": ref["sha"], "asset_id": asset["id"], "asset_name": args.asset,
                "asset_sha256": actual, "size": asset["size"], "published_at": release["published_at"],
                "claim_boundary": "verified asset bytes; current tag resolution is recorded, not independently verified build provenance"}
    (output / "release-input.json").write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as stream:
        stream.write(f"sbom={path}\nsource-sha={ref['sha']}\nevidence-directory={output}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
