"""Synthetic bundle checks; these are not usable scanner or model assets."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

from security.verify_assets import AssetIntegrityError, verify_manifest

ERROR = "Scanner toolchain asset verification failed"
LINK = "/opt/promptfoo/node_modules/.bin/promptfoo"
TARGET = "/opt/promptfoo/node_modules/promptfoo/bin/promptfoo.js"
MODEL = "/opt/models/gliner-pii"
WHEEL = "/opt/offline-ai/wheels/fixture_package-0.0.0-py3-none-any.whl"
PATHS = {
    "/usr/local/bin/gitleaks": "bin/gitleaks",
    "/usr/local/bin/opengrep": "bin/opengrep",
    "/opt/offline-ai/requirements.lock": "requirements.lock",
    WHEEL: "python-wheels/fixture_package-0.0.0-py3-none-any.whl",
    "/opt/promptfoo/package.json": "promptfoo/package.json",
    "/opt/promptfoo/package-lock.json": "promptfoo/package-lock.json",
    "/opt/promptfoo/node_modules/promptfoo/package.json": "promptfoo/node_modules/promptfoo/package.json",
    TARGET: "promptfoo/node_modules/promptfoo/bin/promptfoo.js",
    MODEL + "/config.json": "models/gliner-pii/config.json",
    MODEL + "/model.safetensors": "models/gliner-pii/model.safetensors",
    MODEL + "/tokenizer.json": "models/gliner-pii/tokenizer.json",
}


def make_bundle(tmp_path, *, vendor=False):
    root = tmp_path / ("vendor" if vendor else "image")
    root.mkdir()
    local, records = {}, []
    for image_path, vendor_path in PATHS.items():
        path = root / (vendor_path if vendor else image_path.removeprefix("/"))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"synthetic asset: " + image_path.encode())
        path.chmod(0o755 if image_path in {"/usr/local/bin/gitleaks", "/usr/local/bin/opengrep", TARGET} else 0o644)
        local[image_path] = path
        records.append({"path": image_path, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    link = root / ("promptfoo/node_modules/.bin/promptfoo" if vendor else LINK.removeprefix("/"))
    link.parent.mkdir(parents=True)
    link.symlink_to("../promptfoo/bin/promptfoo.js")
    local[LINK] = link
    payload = {"schema_version": 2, "files": records, "symlinks": [
        {"path": LINK, "target": "../promptfoo/bin/promptfoo.js"}
    ]}
    manifest = root / ("manifest.json" if vendor else "opt/offline-ai/manifest.json")
    manifest.write_text(json.dumps(payload))
    return root, manifest, payload, local


def assert_invalid(manifest, root):
    with pytest.raises(AssetIntegrityError, match="^" + ERROR + "$"):
        verify_manifest(manifest, image_root=root)


def test_complete_bundle_including_reviewed_promptfoo_link(tmp_path):
    root, manifest, payload, _ = make_bundle(tmp_path)
    assert verify_manifest(manifest, image_root=root) == len(payload["files"]) + 1


def test_legacy_model_only_schema_cannot_qualify_toolchain(tmp_path):
    root, manifest, payload, _ = make_bundle(tmp_path)
    manifest.write_text(json.dumps({"schema_version": 1, "files": [
        item for item in payload["files"] if item["path"].startswith(MODEL + "/")
    ]}))
    assert_invalid(manifest, root)


@pytest.mark.parametrize("missing", [
    "/usr/local/bin/gitleaks", "/usr/local/bin/opengrep",
    "/opt/offline-ai/requirements.lock", WHEEL,
    "/opt/promptfoo/package.json", "/opt/promptfoo/package-lock.json",
    MODEL + "/config.json", MODEL + "/model.safetensors", LINK,
])
def test_required_component_cannot_be_omitted(tmp_path, missing):
    root, manifest, payload, local = make_bundle(tmp_path)
    local[missing].unlink()
    for category in ("files", "symlinks"):
        payload[category] = [item for item in payload[category] if item["path"] != missing]
    manifest.write_text(json.dumps(payload))
    assert_invalid(manifest, root)


@pytest.mark.parametrize("tree", ["opt/promptfoo", "opt/models/gliner-pii", "opt/offline-ai/wheels"])
def test_complete_tree_inventory_rejects_unlisted_files(tmp_path, tree):
    root, manifest, _, _ = make_bundle(tmp_path)
    (root / tree / "unlisted.whl").write_bytes(b"unreviewed")
    assert_invalid(manifest, root)


@pytest.mark.parametrize("changed", [
    "/usr/local/bin/gitleaks", WHEEL, "/opt/offline-ai/requirements.lock",
    "/opt/promptfoo/package-lock.json", MODEL + "/model.safetensors",
])
def test_tampering_fails_closed(tmp_path, changed):
    root, manifest, _, local = make_bundle(tmp_path)
    local[changed].write_bytes(b"tampered")
    assert_invalid(manifest, root)


@pytest.mark.parametrize("field", ["schema_version", "sha256"])
def test_duplicate_json_keys_fail_closed(tmp_path, field):
    root, manifest, _, _ = make_bundle(tmp_path)
    value = manifest.read_text()
    if field == "schema_version":
        value = value.replace('"schema_version": 2', '"schema_version": 999, "schema_version": 2', 1)
    else:
        value = value.replace('"sha256": ', '"sha256": "' + "0" * 64 + '", "sha256": ', 1)
    manifest.write_text(value)
    assert_invalid(manifest, root)


@pytest.mark.parametrize("invalid", [None, [], "synthetic-private-marker", 2,
    {"schema_version": True, "files": [], "symlinks": []},
    {"schema_version": 2, "files": {}, "symlinks": []},
    {"schema_version": 2, "files": [], "symlinks": {}},
    {"schema_version": 2, "files": [], "symlinks": [], "unknown": "private"},
])
def test_malformed_schema_has_value_free_error(tmp_path, invalid):
    root, manifest, _, _ = make_bundle(tmp_path)
    manifest.write_text(json.dumps(invalid))
    assert_invalid(manifest, root)


@pytest.mark.parametrize("path", [
    "/usr/local/bin/../bin/gitleaks", "/usr//local/bin/gitleaks",
    "/usr/local/bin/./gitleaks", "/usr/local/bin/gitleaks/",
    "usr/local/bin/gitleaks", "/etc/untrusted", "/opt/offline-ai/manifest.json",
])
def test_noncanonical_or_untrusted_paths_are_rejected(tmp_path, path):
    root, manifest, payload, _ = make_bundle(tmp_path)
    payload["files"][0]["path"] = path
    manifest.write_text(json.dumps(payload))
    assert_invalid(manifest, root)


def test_duplicate_asset_path_is_rejected(tmp_path):
    root, manifest, payload, _ = make_bundle(tmp_path)
    payload["files"].append(payload["files"][0])
    manifest.write_text(json.dumps(payload))
    assert_invalid(manifest, root)


def test_symlinked_parent_directory_is_rejected(tmp_path):
    root, manifest, _, _ = make_bundle(tmp_path)
    model_parent = root / "opt/models"
    model_parent.rename(root / "opt/model-alias-target")
    model_parent.symlink_to("model-alias-target", target_is_directory=True)
    assert_invalid(manifest, root)


def test_symlinked_image_root_is_rejected(tmp_path):
    root, manifest, _, _ = make_bundle(tmp_path)
    alias = tmp_path / "image-alias"
    alias.symlink_to(root, target_is_directory=True)
    assert_invalid(manifest, alias)


def test_hardlinked_asset_is_rejected(tmp_path):
    root, manifest, payload, local = make_bundle(tmp_path)
    source = local[MODEL + "/config.json"]
    os.link(source, root / "opt/promptfoo/alias.json")
    payload["files"].append({"path": "/opt/promptfoo/alias.json", "sha256": hashlib.sha256(source.read_bytes()).hexdigest()})
    manifest.write_text(json.dumps(payload))
    assert_invalid(manifest, root)


@pytest.mark.parametrize("target", [TARGET, "../../../outside.js", "../promptfoo", "../missing.js"])
def test_promptfoo_link_must_resolve_to_verified_regular_file_in_tree(tmp_path, target):
    root, manifest, payload, local = make_bundle(tmp_path)
    (root / "opt/outside.js").write_bytes(b"outside")
    local[LINK].unlink()
    local[LINK].symlink_to(target)
    payload["symlinks"][0]["target"] = target
    manifest.write_text(json.dumps(payload))
    assert_invalid(manifest, root)


def test_promptfoo_link_text_must_match_approved_inventory(tmp_path):
    root, manifest, _, local = make_bundle(tmp_path)
    local[LINK].unlink()
    local[LINK].symlink_to("../promptfoo/./bin/promptfoo.js")
    assert_invalid(manifest, root)


def test_unlisted_promptfoo_link_fails(tmp_path):
    root, manifest, payload, _ = make_bundle(tmp_path)
    payload["symlinks"] = []
    manifest.write_text(json.dumps(payload))
    assert_invalid(manifest, root)


def test_links_outside_promptfoo_are_rejected(tmp_path):
    root, manifest, payload, local = make_bundle(tmp_path)
    local[MODEL + "/config.json"].unlink()
    local[MODEL + "/config.json"].symlink_to("tokenizer.json")
    payload["files"] = [item for item in payload["files"] if item["path"] != MODEL + "/config.json"]
    payload["symlinks"].append({"path": MODEL + "/config.json", "target": "tokenizer.json"})
    manifest.write_text(json.dumps(payload))
    assert_invalid(manifest, root)


def test_nonregular_asset_does_not_block_on_fifo(tmp_path):
    root, manifest, _, _ = make_bundle(tmp_path)
    os.mkfifo(root / "opt/promptfoo/fifo")
    assert_invalid(manifest, root)


@pytest.mark.parametrize("command", ["/usr/local/bin/gitleaks", "/usr/local/bin/opengrep", TARGET])
def test_scanner_entrypoints_must_be_executable(tmp_path, command):
    root, manifest, _, local = make_bundle(tmp_path)
    local[command].chmod(0o644)
    assert_invalid(manifest, root)


def test_manifest_symlink_is_rejected(tmp_path):
    root, manifest, _, _ = make_bundle(tmp_path)
    original = manifest.with_name("original-manifest.json")
    manifest.rename(original)
    manifest.symlink_to(original.name)
    assert_invalid(manifest, root)


def test_vendor_layout_uses_same_complete_approved_manifest(tmp_path):
    from security.verify_vendor import verify_vendor
    root, _, payload, _ = make_bundle(tmp_path, vendor=True)
    assert verify_vendor(root) == len(payload["files"]) + 1


def test_vendor_tampering_fails_before_any_build(tmp_path):
    from security.verify_vendor import verify_vendor
    root, _, _, local = make_bundle(tmp_path, vendor=True)
    local["/usr/local/bin/opengrep"].write_bytes(b"tampered")
    with pytest.raises(AssetIntegrityError, match="^" + ERROR + "$"):
        verify_vendor(root)


def test_vendor_cli_does_not_print_paths_or_tracebacks(tmp_path):
    root, manifest, _, _ = make_bundle(tmp_path, vendor=True)
    manifest.write_text('{"synthetic-private-marker": NaN}')
    result = subprocess.run([sys.executable, "-m", "security.verify_vendor", str(root)],
                            capture_output=True, text=True, check=False)
    assert result.returncode == 2
    assert result.stdout == ""
    assert result.stderr == ERROR + "\n"


@pytest.mark.parametrize("tamper", [False, True])
def test_build_wrapper_runs_verified_bundle_before_docker(tmp_path, tamper):
    """Fake Docker proves orchestration only, never real image qualification."""
    checkout = tmp_path / "checkout"
    checkout.mkdir()
    subprocess.run(["git", "init", "-q", str(checkout)], check=True)
    _, _, _, local = make_bundle(checkout, vendor=True)
    if tamper:
        local["/opt/offline-ai/requirements.lock"].write_bytes(b"tampered")
    source = Path(__file__).resolve().parents[1]
    destination = checkout / "security/offline-ai"
    shutil.copytree(source / "security", destination / "security", ignore=shutil.ignore_patterns("__pycache__"))
    (destination / "docker").mkdir()
    shutil.copy2(source / "docker/build_offline.sh", destination / "docker/build_offline.sh")
    tools = tmp_path / "tools"
    tools.mkdir()
    calls = tmp_path / "docker-calls.jsonl"
    docker = tools / "docker"
    docker.write_text("#!" + sys.executable + "\nimport json, os, sys\n"
        "with open(os.environ['DOCKER_CALLS'], 'a') as stream: stream.write(json.dumps(sys.argv[1:]) + '\\n')\n"
        "if sys.argv[1:3] == ['image', 'inspect']: print('localhost/offline-ai-security@sha256:' + 'c' * 64)\n")
    docker.chmod(0o755)
    environment = dict(os.environ,
        PATH=str(tools) + os.pathsep + str(Path(sys.executable).parent) + os.pathsep + os.environ["PATH"],
        BASE_IMAGE="localhost/synthetic-base@sha256:" + "a" * 64, DOCKER_CALLS=str(calls))
    result = subprocess.run(["bash", "security/offline-ai/docker/build_offline.sh"],
        cwd=checkout, env=environment, capture_output=True, text=True, check=False)
    if tamper:
        assert result.returncode == 2
        assert not calls.exists()
        assert result.stderr == ERROR + "\n"
    else:
        assert result.returncode == 0, result.stderr
        commands = [json.loads(line) for line in calls.read_text().splitlines()]
        builds = [command for command in commands if command[0] == "build"]
        assert len(builds) == 1
        assert {"--network=none", "--pull=false"}.issubset(builds[0])
