"""Verify supplied local vendor assets before any Docker build is attempted."""
from __future__ import annotations

from pathlib import Path
import sys

from .verify_assets import AssetIntegrityError, ERROR_MESSAGE, _verify_bundle


def verify_vendor(vendor_root: Path) -> int:
    """Map the reviewed image-path manifest to the complete local vendor tree."""
    return _verify_bundle(vendor_root / "manifest.json", vendor_root, vendor=True)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(ERROR_MESSAGE, file=sys.stderr)
        raise SystemExit(2)
    try:
        verify_vendor(Path(sys.argv[1]))
    except AssetIntegrityError:
        print(ERROR_MESSAGE, file=sys.stderr)
        raise SystemExit(2) from None
