import hashlib
import json
import pytest
from security.verify_assets import verify_manifest, AssetIntegrityError

def setup(tmp_path):
    model = tmp_path / "gliner-pii"
    model.mkdir()
    a, b = model / "config.json", model / "model.safetensors"
    a.write_text("{}")
    b.write_bytes(b"synthetic-model-fixture")
    manifest = tmp_path / "manifest.json"
    items = [{"path": str(p), "sha256": hashlib.sha256(p.read_bytes()).hexdigest()} for p in (a, b)]
    manifest.write_text(json.dumps({"schema_version": 1, "files": items}))
    return manifest, a, b

def test_known_good_manifest(tmp_path):
    manifest, _, _ = setup(tmp_path)
    assert verify_manifest(manifest, allowed_roots=(tmp_path,)) == 2

def test_tampering_fails_closed(tmp_path):
    manifest, _, weights = setup(tmp_path)
    weights.write_bytes(b"tampered")
    with pytest.raises(AssetIntegrityError):
        verify_manifest(manifest, allowed_roots=(tmp_path,))

def test_missing_verified_weights_fails(tmp_path):
    manifest, _, _ = setup(tmp_path)
    payload = json.loads(manifest.read_text())
    payload["files"] = payload["files"][:1]
    manifest.write_text(json.dumps(payload))
    with pytest.raises(AssetIntegrityError):
        verify_manifest(manifest, allowed_roots=(tmp_path,))

def test_duplicate_asset_fails(tmp_path):
    manifest, _, _ = setup(tmp_path)
    payload = json.loads(manifest.read_text())
    payload["files"].append(payload["files"][0])
    manifest.write_text(json.dumps(payload))
    with pytest.raises(AssetIntegrityError):
        verify_manifest(manifest, allowed_roots=(tmp_path,))

def test_symlink_fails(tmp_path):
    manifest, config, _ = setup(tmp_path)
    link = tmp_path / "alias.json"
    link.symlink_to(config)
    payload = json.loads(manifest.read_text())
    payload["files"][0] = {"path": str(link), "sha256": payload["files"][0]["sha256"]}
    manifest.write_text(json.dumps(payload))
    with pytest.raises(AssetIntegrityError):
        verify_manifest(manifest, allowed_roots=(tmp_path,))

def test_outside_root_fails(tmp_path):
    manifest, _, _ = setup(tmp_path)
    other = tmp_path / "other"
    other.mkdir()
    with pytest.raises(AssetIntegrityError):
        verify_manifest(manifest, allowed_roots=(other,))

def test_malformed_manifest_fails_without_contents(tmp_path):
    manifest = tmp_path / "manifest.json"
    manifest.write_text("{bad json")
    with pytest.raises(AssetIntegrityError) as error:
        verify_manifest(manifest, allowed_roots=(tmp_path,))
    assert "bad json" not in str(error.value)
