"""Offline fail-closed integrity verification for preprovisioned scanner assets."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path

class AssetIntegrityError(RuntimeError):
    pass

def verify_manifest(manifest_path: Path, *, allowed_roots: tuple[Path, ...]) -> int:
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("schema_version") != 1:
            raise ValueError("Unsupported manifest version")
        records = manifest["files"]
        if not isinstance(records, list) or not records:
            raise ValueError("No assets")
        seen: set[str] = set()
        has_config = False
        has_weights = False
        for item in records:
            path = Path(item["path"])
            digest = item["sha256"]
            if not path.is_absolute() or not isinstance(digest, str) or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
                raise ValueError("Invalid asset specification")
            if str(path) in seen or path.is_symlink():
                raise ValueError("Duplicate or symlinked asset")
            seen.add(str(path))
            real = path.resolve(strict=True)
            if not any(real.is_relative_to(root.resolve(strict=True)) for root in allowed_roots):
                raise ValueError("Asset outside trusted roots")
            if not real.is_file():
                raise ValueError("Missing regular file")
            actual = hashlib.sha256()
            with real.open("rb") as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                    actual.update(chunk)
            if actual.hexdigest() != digest:
                raise ValueError("Digest mismatch")
            if "/gliner-pii/" in str(real):
                has_config |= real.name == "config.json"
                has_weights |= real.name.endswith(".safetensors") or real.name == "pytorch_model.bin"
        if not (has_config and has_weights):
            raise ValueError("Required model config/weights not verified")
        return len(records)
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        raise AssetIntegrityError("Scanner toolchain asset verification failed") from None

if __name__ == "__main__":
    verify_manifest(
        Path(os.environ.get("SECURITY_ASSET_MANIFEST", "/opt/offline-ai/manifest.json")),
        allowed_roots=(Path("/opt/models"), Path("/opt/offline-ai"), Path("/usr/local/bin"), Path("/usr/bin")),
    )
