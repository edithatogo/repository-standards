"""Qualify installed Gitleaks with disposable Git repositories (no tracked secrets)."""
from __future__ import annotations
import subprocess
import tempfile
from pathlib import Path

class GitleaksQualificationError(RuntimeError):
    pass

def qualify(config: Path) -> None:
    def run(*args, cwd=None):
        return subprocess.run(args, cwd=cwd, text=True, capture_output=True, check=False, timeout=60)
    try:
        with tempfile.TemporaryDirectory(prefix="offline-gitleaks-") as tmp:
            root = Path(tmp)
            if run("git", "init", "-q", str(root)).returncode: raise RuntimeError()
            run("git", "config", "user.email", "offline@example.invalid", cwd=root)
            run("git", "config", "user.name", "Offline Fixture", cwd=root)
            clean = root / "example.txt"
            clean.write_text("Nothing sensitive in this public fixture.\n")
            if run("git", "add", ".", cwd=root).returncode: raise RuntimeError()
            if run("git", "-c", "commit.gpgsign=false", "commit", "-m", "safe fixture", "-q", cwd=root).returncode: raise RuntimeError()
            if run("gitleaks", "git", str(root), "--config", str(config), "--redact", "--exit-code", "1").returncode != 0:
                raise RuntimeError()
            clean.write_text("CANARY-" + "A1B2C3D4" + "\n")
            if run("git", "add", ".", cwd=root).returncode: raise RuntimeError()
            if run("git", "-c", "commit.gpgsign=false", "commit", "-m", "synthetic fixture", "-q", cwd=root).returncode: raise RuntimeError()
            if run("gitleaks", "git", str(root), "--config", str(config), "--redact", "--exit-code", "1").returncode != 1:
                raise RuntimeError()
    except (OSError, RuntimeError, subprocess.TimeoutExpired):
        raise GitleaksQualificationError("Gitleaks synthetic fixture qualification failed") from None

if __name__ == "__main__":
    qualify(Path(__file__).resolve().parents[1] / ".gitleaks.toml")
