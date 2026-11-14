"""Verify the complete, externally approved schema-v2 offline asset inventory.

The manifest covers supplied wheels/lock, scanner binaries, Promptfoo and model
files. It is not a substitute for base-image provenance or real tool/model tests.
Schema v1 is deliberately rejected because it could verify only two model files.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import stat
import sys

ERROR_MESSAGE = "Scanner toolchain asset verification failed"
WHEELS = PurePosixPath("/opt/offline-ai/wheels")
PROMPTFOO = PurePosixPath("/opt/promptfoo")
MODEL = PurePosixPath("/opt/models/gliner-pii")
PROMPTFOO_ENTRY = PROMPTFOO / "node_modules/.bin/promptfoo"
SINGLE_FILES = {
    PurePosixPath("/usr/local/bin/gitleaks"): "bin/gitleaks",
    PurePosixPath("/usr/local/bin/opengrep"): "bin/opengrep",
    PurePosixPath("/opt/offline-ai/requirements.lock"): "requirements.lock",
}
TREES = {
    WHEELS: "python-wheels",
    PROMPTFOO: "promptfoo",
    MODEL: "models/gliner-pii",
}
REQUIRED_FILES = frozenset(SINGLE_FILES) | {
    MODEL / "config.json",
    PROMPTFOO / "package.json",
    PROMPTFOO / "package-lock.json",
}


class AssetIntegrityError(RuntimeError):
    pass


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate key")
        result[key] = value
    return result


def _reject_constant(_value):
    raise ValueError("Invalid JSON constant")


def _no_symlink_components(path: Path) -> None:
    for component in (*reversed(path.parents), path):
        if stat.S_ISLNK(component.lstat().st_mode):
            raise ValueError("Symlinked path")


def _regular(path: Path):
    _no_symlink_components(path)
    info = path.stat()
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise ValueError("Nonregular or aliased file")
    return info


def _image_path(value) -> PurePosixPath:
    if not isinstance(value, str) or "\0" in value or "\\" in value:
        raise ValueError("Invalid path")
    path = PurePosixPath(value)
    if not path.is_absolute() or path.as_posix() != value or ".." in path.parts:
        raise ValueError("Noncanonical path")
    if path in SINGLE_FILES:
        return path
    for tree in TREES:
        if path != tree and path.is_relative_to(tree):
            if tree == WHEELS and (path.parent != WHEELS or path.suffix != ".whl"):
                raise ValueError("Wheelhouse must contain flat wheel files")
            return path
    raise ValueError("Untrusted path")


def _manifest(path: Path):
    _regular(path)
    payload = json.loads(path.read_text(encoding="utf-8"),
                         object_pairs_hook=_unique_object,
                         parse_constant=_reject_constant)
    if not isinstance(payload, dict) or set(payload) != {"schema_version", "files", "symlinks"}:
        raise ValueError("Invalid schema")
    if type(payload["schema_version"]) is not int or payload["schema_version"] != 2:
        raise ValueError("Unsupported schema")
    if not isinstance(payload["files"], list) or not payload["files"] or not isinstance(payload["symlinks"], list):
        raise ValueError("Invalid inventory")
    files, links = {}, {}
    for record in payload["files"]:
        if not isinstance(record, dict) or set(record) != {"path", "sha256"}:
            raise ValueError("Invalid file record")
        path, digest = _image_path(record["path"]), record["sha256"]
        if path in files or not isinstance(digest, str) or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
            raise ValueError("Duplicate file or invalid digest")
        files[path] = digest
    for record in payload["symlinks"]:
        if not isinstance(record, dict) or set(record) != {"path", "target"}:
            raise ValueError("Invalid link record")
        path, target = _image_path(record["path"]), record["target"]
        if path in files or path in links or not path.is_relative_to(PROMPTFOO):
            raise ValueError("Duplicate or untrusted link")
        if not isinstance(target, str) or not target or "\0" in target or "\\" in target:
            raise ValueError("Invalid link target")
        target_path = PurePosixPath(target)
        if target_path.is_absolute() or target_path.as_posix() != target:
            raise ValueError("Invalid link target")
        links[path] = target
    if not REQUIRED_FILES.issubset(files) or PROMPTFOO_ENTRY not in files.keys() | links.keys():
        raise ValueError("Incomplete toolchain")
    if not any(path.is_relative_to(WHEELS) for path in files):
        raise ValueError("Missing wheels")
    if not any(path.is_relative_to(MODEL) and
               (path.suffix == ".safetensors" or path.name == "pytorch_model.bin")
               for path in files):
        raise ValueError("Missing model weights")
    return files, links


def _hash_regular(path: Path, before) -> str:
    # Avoid following a swapped final symlink, opening a FIFO indefinitely, or
    # accepting a different inode from the one inspected for the inventory.
    flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
    def identity(info):
        return (info.st_dev, info.st_ino, info.st_mode, info.st_nlink,
                info.st_size, info.st_mtime_ns, info.st_ctime_ns)
    with os.fdopen(os.open(path, flags), "rb") as stream:
        if identity(os.fstat(stream.fileno())) != identity(before):
            raise ValueError("Asset changed")
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
        if identity(os.fstat(stream.fileno())) != identity(before):
            raise ValueError("Asset changed")
    return digest


def _verify_bundle(manifest_path: Path, root: Path, *, vendor: bool) -> int:
    try:
        root = root.absolute()
        _no_symlink_components(root)
        root = root.resolve(strict=True)
        if not root.is_dir():
            raise ValueError("Missing root")
        expected_files, expected_links = _manifest(manifest_path.absolute())

        def local(image_path):
            if not vendor:
                return root / image_path.relative_to("/")
            if image_path in SINGLE_FILES:
                return root / SINGLE_FILES[image_path]
            for tree, relative in TREES.items():
                if image_path.is_relative_to(tree):
                    return root / relative / image_path.relative_to(tree)
            raise ValueError("Untrusted mapping")

        files, links = {}, {}
        for path in SINGLE_FILES:
            files[path] = local(path)
        for tree in TREES:
            directory = local(tree)
            _no_symlink_components(directory)
            pending = [(tree, directory)]
            while pending:
                image_directory, directory = pending.pop()
                info = directory.lstat()
                if not stat.S_ISDIR(info.st_mode) or not info.st_mode & stat.S_IXOTH:
                    raise ValueError("Unreadable directory")
                for child in directory.iterdir():
                    image_path = image_directory / child.name
                    mode = child.lstat().st_mode
                    if stat.S_ISDIR(mode):
                        pending.append((image_path, child))
                    elif stat.S_ISREG(mode):
                        files[image_path] = child
                    elif stat.S_ISLNK(mode) and tree == PROMPTFOO:
                        links[image_path] = child
                    else:
                        raise ValueError("Unsupported asset")

        if files.keys() != expected_files.keys() or links.keys() != expected_links.keys():
            raise ValueError("Inventory mismatch")
        inodes, verified = set(), set()
        for image_path, path in files.items():
            info = _regular(path)
            inode = (info.st_dev, info.st_ino)
            if inode in inodes or not info.st_mode & stat.S_IROTH:
                raise ValueError("Aliased or unreadable file")
            inodes.add(inode)
            if _hash_regular(path, info) != expected_files[image_path]:
                raise ValueError("Digest mismatch")
            verified.add(path)

        for image_path, path in links.items():
            _no_symlink_components(path.parent)
            if os.readlink(path) != expected_links[image_path]:
                raise ValueError("Link changed")
            target = path.resolve(strict=True)
            if not target.is_relative_to(local(PROMPTFOO)) or target not in verified:
                raise ValueError("Link target not verified")

        for entry in (*SINGLE_FILES.keys(), PROMPTFOO_ENTRY):
            if entry.name == "requirements.lock":
                continue
            if not local(entry).stat().st_mode & stat.S_IXOTH:
                raise ValueError("Non-executable entrypoint")
        return len(files) + len(links)
    except (OSError, ValueError, TypeError, KeyError, RuntimeError):
        raise AssetIntegrityError(ERROR_MESSAGE) from None


def verify_manifest(manifest_path: Path, *, image_root: Path = Path("/")) -> int:
    """Verify installed image assets against an externally approved manifest."""
    return _verify_bundle(manifest_path, image_root, vendor=False)


if __name__ == "__main__":
    try:
        verify_manifest(Path(os.environ.get("SECURITY_ASSET_MANIFEST", "/opt/offline-ai/manifest.json")))
    except AssetIntegrityError:
        print(ERROR_MESSAGE, file=sys.stderr)
        raise SystemExit(2) from None
