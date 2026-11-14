"""Build the three source-pinned wheels needed by the Python 3.15 guard."""

import argparse
import hashlib
import io
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
from pathlib import Path

PYTHON_VERSION = (3, 15, 1)
MAX_SOURCE_BYTES = 10 * 1024 * 1024
SOURCES = {
    "presidio_analyzer-2.2.366": (
        "40/82/5e7511329ed66898b45a83fcff0e4bb7baecde1df42f16c8c144014e5e87",
        "0a83b224765cc3e796cd51aff60c62c75d8be60e8ed21aa08099da78ffbd62bf",
    ),
    "presidio_anonymizer-2.2.366": (
        "77/5e/ecc26a46a5f3024a0f84c55782b0c2620212c10a8c44e0623fb5b6b0db5e",
        "e34662379c5453a7f80012b1dbe87d9fb90d3baf627d355424f74aa740bbf27a",
    ),
    "pyyaml-6.0.3": (
        "05/8e/961c0007c59b8dd7729d542c61a4d537767a59645b82a0b521206e1e25c2",
        "d76623373421df22fb4cf8817020cbb7ef15c725b9d5e45f17e189bfc384190f",
    ),
}
PRESIDIO_CHANGES = (
    ('version = "2.2.366"', 'version = "2.2.366+python315.1"'),
    ('requires-python = ">=3.11,<3.15"', 'requires-python = "==3.15.1"'),
)
ANALYZER_CHANGES = (
    ('"numpy (>=1.19.0,<2.5.0)"', '"numpy (==2.5.4)"'),
    ('"preshed (<3.0.14)"', '"preshed (==3.0.15)"'),
)


def verified_source(name: str, directory: Path) -> Path:
    """Download an exact PyPI source archive and extract only verified bytes."""
    location, digest = SOURCES[name]
    url = f"https://files.pythonhosted.org/packages/{location}/{name}.tar.gz"
    with urllib.request.urlopen(url, timeout=60) as response:
        payload = response.read(MAX_SOURCE_BYTES + 1)
    if len(payload) > MAX_SOURCE_BYTES or hashlib.sha256(payload).hexdigest() != digest:
        raise ValueError(f"Source hash mismatch: {name}")
    with tarfile.open(fileobj=io.BytesIO(payload), mode="r:gz") as archive:
        archive.extractall(directory, filter="data")
    source = directory / name
    if not (source / "pyproject.toml").is_file():
        raise ValueError(f"Source layout mismatch: {name}")
    return source


def patch_presidio(source: Path) -> None:
    """Declare the exact compatibility build without changing scanner code."""
    project = source / "pyproject.toml"
    content = project.read_text(encoding="utf-8")
    changes = PRESIDIO_CHANGES
    if source.name.startswith("presidio_analyzer"):
        changes += ANALYZER_CHANGES
    for before, after in changes:
        if content.count(before) != 1:
            raise ValueError(f"Unexpected upstream metadata: {source.name}")
        content = content.replace(before, after, 1)
    project.write_text(content, encoding="utf-8")


def build(destination: Path) -> None:
    """Build in a temporary directory using the verified interpreter and toolset."""
    if sys.version_info[:3] != PYTHON_VERSION:
        raise RuntimeError("The privacy wheel build requires Python 3.15.1")
    uv = shutil.which("uv")
    if uv is None:
        raise RuntimeError("The privacy wheel build requires uv")
    destination.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="privacy-wheel-sources-") as work:
        root = Path(work)
        for name in SOURCES:
            source = verified_source(name, root)
            if name.startswith("presidio_"):
                patch_presidio(source)
            subprocess.run(
                [
                    uv,
                    "build",
                    "--wheel",
                    "--python",
                    sys.executable,
                    "--no-build-isolation",
                    "--offline",
                    "--no-index",
                    "--out-dir",
                    os.fspath(destination),
                    os.fspath(source),
                ],
                check=True,
            )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destination", required=True, type=Path)
    build(parser.parse_args().destination.resolve())


if __name__ == "__main__":
    main()
