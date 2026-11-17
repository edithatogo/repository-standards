"""The consumer mount must contain only an immutable policy snapshot."""
from __future__ import annotations

import importlib.util
import io
import os
from pathlib import Path
import py_compile
import shlex
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch

REPO = Path(__file__).resolve().parents[1]
HELPER = Path("security/offline-ai/provision/export_consumer_policy.py")
QUALIFIER = Path("security/offline-ai/docker/qualify_image.py")


class ConsumerPolicyExportTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="consumer-policy-export-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.policy = self.root / "policy"
        self.policy.mkdir()
        for source in (HELPER, QUALIFIER):
            target = self.policy / source
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(REPO / source, target)
        (self.policy / ".gitignore").write_text("ignored.txt\n__pycache__/\n")
        (self.policy / "tracked.txt").write_text("committed fixture\n")
        self.git("init", "--quiet")
        self.git("add", ".")
        self.commit("Initial fixture")
        self.sha = self.git("rev-parse", "HEAD").strip()
        self.destination = self.root / "export"

    def git(self, *args: str) -> str:
        return subprocess.check_output(
            ["git", "-C", str(self.policy), *args],
            stderr=subprocess.DEVNULL,
            text=True,
        )

    def commit(self, message: str) -> None:
        self.git("-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
                 "-c", "commit.gpgsign=false", "commit", "--quiet", "-m", message)

    def invoke(self, commit: str | None = None, destination: Path | None = None, *, umask=-1):
        return subprocess.run(
            [sys.executable, "-I", str(self.policy / HELPER), "--commit", commit or self.sha,
             "--destination", str(destination or self.destination)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
            timeout=30,
            umask=umask,
        )

    def test_exports_committed_files_without_git_or_ignored_content(self):
        (self.policy / "ignored.txt").write_text("untracked private fixture\n")
        result = self.invoke()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.destination / "tracked.txt").read_text(), "committed fixture\n")
        self.assertTrue((self.destination / HELPER).is_file())
        self.assertFalse((self.destination / ".git").exists())
        self.assertFalse((self.destination / "ignored.txt").exists())
        self.assertEqual(self.destination.stat().st_mode & 0o005, 0o005)
        self.assertNotIn("untracked private fixture", result.stdout + result.stderr)

    def test_export_ignore_cannot_omit_committed_policy(self):
        (self.policy / ".git/info/attributes").write_text("tracked.txt export-ignore\n")
        raw = subprocess.check_output(["git", "-C", str(self.policy), "archive", self.sha])
        with tarfile.open(fileobj=io.BytesIO(raw)) as archive:
            self.assertNotIn("tracked.txt", archive.getnames())
        self.assertNotEqual(self.invoke().returncode, 0)
        self.assertFalse(self.destination.exists())

    def test_export_substitution_cannot_change_committed_policy(self):
        (self.policy / "tracked.txt").write_text("$Format:%H$\n")
        self.git("add", "tracked.txt")
        self.commit("Synthetic substitution fixture")
        self.sha = self.git("rev-parse", "HEAD").strip()
        (self.policy / ".git/info/attributes").write_text("tracked.txt export-subst\n")
        raw = subprocess.check_output(["git", "-C", str(self.policy), "archive", self.sha])
        with tarfile.open(fileobj=io.BytesIO(raw)) as archive:
            self.assertNotEqual(archive.extractfile("tracked.txt").read(), b"$Format:%H$\n")
        self.assertNotEqual(self.invoke().returncode, 0)
        self.assertFalse(self.destination.exists())

    @unittest.skipUnless(os.name == "posix", "POSIX permissions unavailable")
    def test_restrictive_umask_cannot_make_snapshot_unreadable(self):
        self.git("config", "tar.umask", "0077")
        result = self.invoke(umask=0o077)
        self.assertEqual(result.returncode, 0, result.stderr)
        for path in (self.destination, *self.destination.rglob("*")):
            with self.subTest(path=path.relative_to(self.destination)):
                expected = 0o005 if path.is_dir() else 0o004
                self.assertEqual(path.stat().st_mode & expected, expected)

    def test_ignored_bytecode_cannot_execute_instead_of_committed_helper(self):
        qualifier = self.policy / QUALIFIER
        marker = self.root / "cached-code-ran"
        fake = self.root / "fake-qualifier.py"
        payload = "from pathlib import Path\nPath(" + repr(str(marker)) + ").write_text('ran')\n"
        size = qualifier.stat().st_size
        self.assertLess(len(payload), size)
        fake.write_text(payload + "#" * (size - len(payload)))
        stat = qualifier.stat()
        os.utime(fake, ns=(stat.st_atime_ns, stat.st_mtime_ns))
        cache = Path(importlib.util.cache_from_source(str(qualifier)))
        cache.parent.mkdir(parents=True)
        py_compile.compile(str(fake), cfile=str(cache), dfile=str(qualifier),
                           invalidation_mode=py_compile.PycInvalidationMode.TIMESTAMP,
                           doraise=True)
        subprocess.run(
            [sys.executable, "-I", "-c", "import importlib.util,sys; s=importlib.util.spec_from_file_location('q',sys.argv[1]); m=importlib.util.module_from_spec(s); s.loader.exec_module(m)", str(qualifier)],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        self.assertTrue(marker.exists(), "Fixture must demonstrate cached bytecode executes")
        marker.unlink()
        result = self.invoke()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(marker.exists())

    def test_rejects_dirty_wrong_or_existing_destination(self):
        for bad in ("a" * 40, "HEAD"):
            with self.subTest(commit=bad):
                self.assertNotEqual(self.invoke(commit=bad).returncode, 0)
                self.assertFalse(self.destination.exists())
        (self.policy / "tracked.txt").write_text("uncommitted change\n")
        self.assertNotEqual(self.invoke().returncode, 0)
        self.assertFalse(self.destination.exists())
        (self.policy / "tracked.txt").write_text("committed fixture\n")
        self.destination.mkdir()
        marker = self.destination / "preserve.txt"
        marker.write_text("preserve\n")
        self.assertNotEqual(self.invoke().returncode, 0)
        self.assertEqual(marker.read_text(), "preserve\n")

    def test_untrusted_git_environment_and_fsmonitor_do_not_run(self):
        marker = self.root / "fsmonitor-ran"
        helper = self.root / "fsmonitor.sh"
        helper.write_text("#!/bin/sh\nprintf invoked > " + shlex.quote(str(marker)) + "\n")
        helper.chmod(0o700)
        self.git("config", "core.fsmonitor", str(helper))
        self.git("status", "--porcelain")
        self.assertTrue(marker.exists(), "Fixture must demonstrate the Git hook runs")
        marker.unlink()
        with patch.dict(os.environ, {"GIT_DIR": str(self.root / "untrusted-git-dir")}):
            result = self.invoke()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(marker.exists())
        self.assertEqual((self.destination / "tracked.txt").read_text(), "committed fixture\n")

    @unittest.skipUnless(hasattr(os, "symlink"), "Symbolic links unavailable")
    def test_rejects_a_committed_symlink(self):
        (self.policy / "link").symlink_to("tracked.txt")
        self.git("add", "link")
        self.commit("Add synthetic link")
        result = self.invoke(commit=self.git("rev-parse", "HEAD").strip())
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.destination.exists())


if __name__ == "__main__":
    unittest.main()
