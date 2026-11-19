"""Run actual Opengrep CLI against fail-open and fail-closed synthetic fixtures.

This MUST run within the isolated image. It deliberately does not use mock SAST.
"""

from __future__ import annotations
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures" / "taint"
RULES = ROOT / ".opengrep" / "rules.yaml"
sys.path.insert(0, str(ROOT / "scripts"))
import scan_opengrep  # noqa: E402

RUST_FINDINGS = frozenset({
    "rust_bad.rs",
    "rust_direct_env_bad.rs",
    "rust_raw_identifier_bad.rs",
    "rust_raw_log_macro_bad.rs",
    "rust_indirect_env_bad.rs",
})
RUST_CLEAN = frozenset({
    "rust_good.rs",
    "rust_macro_literals_good.rs",
    "rust_env_alias_literals_good.rs",
    "rust_unrelated_env_good.rs",
})
RUST_FINDING_LINES = frozenset({
    ("rust_raw_identifier_bad.rs", 2),
    ("rust_raw_identifier_bad.rs", 3),
    ("rust_raw_identifier_bad.rs", 4),
    ("rust_raw_log_macro_bad.rs", 2),
    ("rust_raw_log_macro_bad.rs", 3),
})


def verify_tracked_source_scanner(executable: str = "/usr/local/bin/opengrep",
                                  esbuild: str = scan_opengrep.ESBUILD) -> None:
    """Exercise actual selection and parsing despite consumer ignore files."""
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary).resolve()
        env = scan_opengrep.secrets_scan.clean_environment()
        for command in (["git", "init", "-q", str(root)],
                        ["git", "-C", str(root), "add", "-f", "hidden.py"]):
            if "add" in command:
                (root / ".gitignore").write_text("*.py\n")
                (root / ".semgrepignore").write_text("*.py\n")
                shutil.copyfile(FIXTURES / "python_good.py", root / "hidden.py")
            subprocess.run(command, env=env, capture_output=True, check=True, timeout=30)
        clean = scan_opengrep.scan(root, RULES, executable=executable, esbuild=esbuild, offline_container=False)
        if clean.status or clean.tracked != 1 or clean.scanned != 1:
            raise RuntimeError("Tracked-source clean control failed")
        for filename, content in (("valid.ts", "const x: number = 1;\n"),
                                  ("valid.tsx", "const x = <div/>;\n"),
                                  ("valid.jsx", "const x = <div/>;\n")):
            (root / filename).write_text(content)
        subprocess.run(["git", "-C", str(root), "add", "-f", "valid.ts", "valid.tsx", "valid.jsx"],
                       env=env, capture_output=True, check=True, timeout=30)
        clean = scan_opengrep.scan(root, RULES, executable=executable, esbuild=esbuild, offline_container=False)
        if clean.status or clean.tracked != 4 or clean.scanned != 4:
            raise RuntimeError("Tracked-source language controls failed")
        shutil.copyfile(FIXTURES / "python_bad.py", root / ".py")
        subprocess.run(["git", "-C", str(root), "add", "-f", ".py"], env=env,
                       capture_output=True, check=True, timeout=30)
        bad = scan_opengrep.scan(root, RULES, executable=executable, esbuild=esbuild, offline_container=False)
        if bad.status == 0 or bad.findings == 0 or bad.errors or bad.parse_failures or bad.scanned != 5:
            raise RuntimeError("Tracked-source detection control failed")
        shutil.copyfile(FIXTURES / "python_good.py", root / ".py")
        for extension in ("py", "rs", "js", "ts"):
            (root / ("invalid." + extension)).write_text("function broken( {\n")
        (root / "invalid_null.py").write_bytes(b"a = 1\x00\n")
        (root / "invalid_continue.py").write_text("def f():\n    continue\n")
        (root / "invalid_indent.py").write_text("def f():\n   x = 1\n    print(x)\n")
        (root / "typescript_in_js.js").write_text("function f(req) { const ra:w = req.body; console.log(raw); }\n")
        subprocess.run(["git", "-C", str(root), "add", "-f", "invalid.py", "invalid.rs",
                        "invalid.js", "invalid.ts", "invalid_null.py", "invalid_continue.py",
                        "invalid_indent.py", "typescript_in_js.js"], env=env,
                       capture_output=True, check=True, timeout=30)
        invalid = scan_opengrep.scan(root, RULES, executable=executable, esbuild=esbuild, offline_container=False)
        if invalid.status == 0 or invalid.parse_failures != 8:
            raise RuntimeError("Tracked-source parser control failed")


def verify() -> None:
    result = subprocess.run(
        [
            "opengrep",
            "scan",
            "--no-git-ignore",
            "--semgrepignore-filename=/dev/null",
            "--taint-intrafile",
            "--strict",
            "--disable-nosem",
            "--json",
            "--config",
            str(RULES),
            str(FIXTURES),
        ],
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError("Opengrep fixture invocation or parsing failed")
    try:
        payload = json.loads(result.stdout)
        if payload.get("errors"):
            raise ValueError("Rules were rejected")
        hits = payload["results"]
        observed = {Path(item["path"]).name for item in hits}
        scanned = {Path(name).name for name in payload["paths"]["scanned"]}
    except (ValueError, TypeError, KeyError):
        raise RuntimeError("Opengrep fixture report invalid") from None
    required = {
        "python_bad.py",
        "python_spoofed_sanitizer_bad.py",
        "typescript_bad.ts",
        "typescript_spoofed_sanitizer_bad.ts",
    } | RUST_FINDINGS
    clean = {
        "python_good.py",
        "typescript_good.ts",
    } | RUST_CLEAN
    if not (required | clean).issubset(scanned):
        raise RuntimeError("Opengrep did not scan every required control")
    if not required.issubset(observed) or (observed & clean):
        raise RuntimeError(
            "Opengrep rule regression: unexpected coverage on synthetic fixtures"
        )
    try:
        hit_lines = {(Path(item["path"]).name, item["start"]["line"]) for item in hits}
    except (KeyError, TypeError, ValueError):
        raise RuntimeError("Opengrep fixture report invalid") from None
    if not RUST_FINDING_LINES.issubset(hit_lines):
        raise RuntimeError("Opengrep did not detect every Rust representation control")
    verify_tracked_source_scanner()


if __name__ == "__main__":
    try:
        verify()
    except (RuntimeError, OSError, ValueError, subprocess.SubprocessError, scan_opengrep.ScanError,
            scan_opengrep.secrets_scan.ScanError):
        print("SAST fixture qualification failed", file=sys.stderr)
        raise SystemExit(2)
