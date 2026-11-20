"""Bounded source-build candidate regressions; no toolchain or network required."""
from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / "security/offline-ai/provision"
SPEC = importlib.util.spec_from_file_location("gitleaks_candidate", HERE / "gitleaks_candidate.py")
CANDIDATE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CANDIDATE)


class Response(io.BytesIO):
    def geturl(self):
        return "https://go.dev/dl/public-fixture.tar.gz"


class GitleaksCandidateTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def test_reviewed_build_rejects_source_or_lock_drift(self):
        _, catalog_hash = CANDIDATE.load_catalog()
        expected_mod = (HERE / "gitleaks-reviewed/go.mod").read_bytes()
        lock, mod, sums = CANDIDATE.locked_inputs(catalog_hash, expected_mod)
        self.assertEqual(hashlib.sha256(mod).hexdigest(), lock["files"]["go.mod"])
        self.assertEqual(hashlib.sha256(sums).hexdigest(), lock["files"]["go.sum"])
        with self.assertRaises(CANDIDATE.CandidateError):
            CANDIDATE.locked_inputs("0" * 64, expected_mod)
        with self.assertRaises(CANDIDATE.CandidateError):
            CANDIDATE.locked_inputs(catalog_hash, expected_mod + b"\n")

    def test_reviewed_output_binds_all_metadata_and_compiled_bytes(self):
        payloads = {name: name.encode() for name in CANDIDATE.OUTPUTS[1:]}
        lock = {"files": {name: hashlib.sha256(data).hexdigest() for name, data in payloads.items()},
                "binary_sha256": "a" * 64, "binary_size_bytes": 20}
        CANDIDATE.verify_locked_output(lock, payloads, "a" * 64, 20)
        for name in payloads:
            with self.subTest(name=name), self.assertRaises(CANDIDATE.CandidateError):
                CANDIDATE.verify_locked_output(lock, {**payloads, name: b"changed"}, "a" * 64, 20)
        for digest, size in [("b" * 64, 20), ("a" * 64, 19)]:
            with self.assertRaises(CANDIDATE.CandidateError):
                CANDIDATE.verify_locked_output(lock, payloads, digest, size)

    def archive(self, entries):
        path = self.root / "archive.tar.gz"
        with tarfile.open(path, "w:gz") as archive:
            for name, kind, payload in entries:
                member = tarfile.TarInfo(name)
                if kind == "file":
                    member.size = len(payload)
                    archive.addfile(member, io.BytesIO(payload))
                else:
                    member.type = tarfile.SYMTYPE if kind == "symlink" else tarfile.LNKTYPE
                    member.linkname = payload
                    archive.addfile(member)
        return path

    def test_exact_known_test_symlink_is_verified_but_never_created(self):
        target = "../source_file/id_ed25519"
        path = "testdata/repos/symlinks/file_symlink/symlinked_id_ed25519"
        archive = self.archive([
            ("source/main.go", "file", b"package main\n"),
            ("source/" + path, "symlink", target),
        ])
        output = self.root / "source"
        result = CANDIDATE.unpack(archive, output, "source", [{
            "path": path, "target": target,
            "git_blob_sha1": "fd0203d88ba52c0a69fbdb10dc1c4c8a9af947bc",
        }])
        self.assertEqual(result["regular_files"], 1)
        self.assertEqual(result["omitted_symlinks"], [path])
        self.assertFalse((output / path).exists())
        self.assertFalse((output / path).is_symlink())
        self.assertEqual((output / "main.go").read_bytes(), b"package main\n")

    def test_traversal_unapproved_links_and_hardlinks_are_rejected(self):
        for name, kind, payload in (
            ("source/../escape", "file", b"no"),
            ("source/link", "symlink", "../outside"),
            ("source/link", "hardlink", "source/main.go"),
        ):
            with self.subTest(name=name, kind=kind):
                archive = self.archive([(name, kind, payload)])
                with tempfile.TemporaryDirectory(dir=self.root) as temporary:
                    with self.assertRaises(CANDIDATE.CandidateError):
                        CANDIDATE.unpack(archive, Path(temporary) / "output", "source")
        self.assertFalse((self.root / "escape").exists())

    def test_missing_or_changed_expected_link_fails_closed(self):
        expected = [{"path": "fixture", "target": "expected",
                     "git_blob_sha1": CANDIDATE.git_blob(b"expected")}]
        for entries in (
            [("source/main.go", "file", b"public")],
            [("source/fixture", "symlink", "changed")],
        ):
            with self.subTest(entries=entries):
                archive = self.archive(entries)
                with tempfile.TemporaryDirectory(dir=self.root) as temporary:
                    with self.assertRaises(CANDIDATE.CandidateError):
                        CANDIDATE.unpack(archive, Path(temporary) / "output",
                                         "source", expected)

    def test_duplicate_archive_members_are_rejected(self):
        archive = self.archive([("source/file", "file", b"one"),
                                ("source/file", "file", b"two")])
        with self.assertRaises(CANDIDATE.CandidateError):
            CANDIDATE.unpack(archive, self.root / "output", "source")

    def test_archive_digest_and_exact_size_are_required(self):
        raw = b"public archive bytes"
        for index, record in enumerate((
            {"size_bytes": len(raw), "sha256": "0" * 64},
            {"size_bytes": len(raw) + 1, "sha256": hashlib.sha256(raw).hexdigest()},
        )):
            with self.subTest(index=index):
                with mock.patch.object(CANDIDATE.urllib.request, "urlopen",
                                       return_value=Response(raw)):
                    with self.assertRaises(CANDIDATE.CandidateError):
                        CANDIDATE.download({"url": "https://go.dev/dl/fixture", **record},
                                           self.root / str(index))

    def test_only_observed_go_mod_changes_are_accepted(self):
        catalog, _ = CANDIDATE.load_catalog()
        original = ("module example.invalid/public\n\ngo "
                    + catalog["go_minimum_before"] + "\n\nrequire (\n"
                    + "".join("\t" + entry["path"] + " " + entry["before"] + "\n"
                              for entry in catalog["updates"]) + ")\n").encode()
        expected = CANDIDATE.expected_go_mod(original, catalog)
        for entry in catalog["updates"]:
            self.assertIn((entry["path"] + " " + entry["after"]).encode(), expected)
        path = self.root / "go.mod"
        path.write_bytes(expected)
        CANDIDATE.assert_go_mod(path, expected)
        path.write_bytes(expected + b"require example.invalid/unreviewed v1.0.0\n")
        with self.assertRaises(CANDIDATE.CandidateError):
            CANDIDATE.assert_go_mod(path, expected)
        with self.assertRaises(CANDIDATE.CandidateError):
            CANDIDATE.expected_go_mod(original.replace(
                catalog["updates"][0]["before"].encode(), b"v0.0.0"), catalog)

    def test_environment_does_not_inherit_credentials_or_go_git_overrides(self):
        with mock.patch.dict(os.environ, {
            "GOFLAGS": "-toolexec=untrusted", "GOPROXY": "https://private.invalid",
            "GOTOOLCHAIN": "auto", "GIT_CONFIG_SYSTEM": "/private/config",
            "GITHUB_TOKEN": "private-token", "AWS_SECRET_ACCESS_KEY": "private-value",
        }):
            online = CANDIDATE.environment(self.root)
            offline = CANDIDATE.environment(self.root, offline=True)
        for key in ("GOFLAGS", "GITHUB_TOKEN", "AWS_SECRET_ACCESS_KEY", "GIT_CONFIG_SYSTEM"):
            self.assertNotIn(key, online)
            self.assertNotIn(key, offline)
        self.assertEqual(online["GOPROXY"], "https://proxy.golang.org")
        self.assertEqual(online["GOSUMDB"], "sum.golang.org")
        for key in ("GOPROXY", "GOSUMDB", "GOENV"):
            self.assertEqual(offline[key], "off")
        self.assertEqual(offline["GOTOOLCHAIN"], "local")
        self.assertEqual(offline["CGO_ENABLED"], "0")
        self.assertEqual((offline["GOOS"], offline["GOARCH"]), ("linux", "amd64"))

    def test_missing_closure_and_replaced_modules_are_rejected(self):
        catalog = {"selected_module_entries": 2,
                   "source": {"module": "example.invalid/main"}, "updates": []}
        selected = [{"Path": "example.invalid/main", "Main": True},
                    {"Path": "example.invalid/dependency", "Version": "v1.0.0"}]
        with self.assertRaises(CANDIDATE.CandidateError):
            CANDIDATE.module_closure(selected, [], self.root, catalog, b"")
        selected[1]["Replace"] = {"Path": "../unreviewed"}
        with self.assertRaises(CANDIDATE.CandidateError):
            CANDIDATE.module_closure(selected, [], self.root, catalog, b"")

    def test_child_failure_does_not_expose_raw_output(self):
        result = subprocess.CompletedProcess(["go"], 1, b"private stdout", b"private stderr")
        output, error = io.StringIO(), io.StringIO()
        with mock.patch.object(CANDIDATE.subprocess, "run", return_value=result):
            with redirect_stdout(output), redirect_stderr(error):
                with self.assertRaisesRegex(CANDIDATE.CandidateError, "^build$"):
                    CANDIDATE.run(["go"], cwd=self.root, env={}, stage="build")
        self.assertEqual(output.getvalue() + error.getvalue(), "")

    def test_recovery_envelope_reconstructs_exact_utf8_and_hashes(self):
        payloads = {}
        for name in CANDIDATE.OUTPUTS:
            payload = (name + "\n" + "public λ metadata\n" * 300).encode()
            (self.root / name).write_bytes(payload)
            payloads[name] = payload
        output = io.StringIO()
        with redirect_stdout(output):
            CANDIDATE.emit_public_metadata(self.root, complete=True)
        records = [json.loads(line.removeprefix(CANDIDATE.MARKER))
                   for line in output.getvalue().splitlines()]
        self.assertEqual(records[0]["kind"], "manifest")
        self.assertEqual(records[-1]["kind"], "complete")
        self.assertTrue(all(r["artifact"] == "offline-gitleaks-candidate" for r in records))
        for manifest in records[0]["files"]:
            chunks = [r for r in records if r["kind"] == "chunk"
                      and r["path"] == manifest["path"]]
            self.assertEqual([r["index"] for r in chunks], list(range(len(chunks))))
            self.assertTrue(all(len(r["data"]) <= 2048 for r in chunks))
            recovered = "".join(r["data"] for r in chunks).encode("utf-8")
            self.assertEqual(recovered, payloads[manifest["path"]])
            self.assertEqual(hashlib.sha256(recovered).hexdigest(), manifest["sha256"])
            self.assertEqual(len(recovered), manifest["size_bytes"])

    def test_recovery_rejects_unlisted_files_and_oversized_payloads(self):
        (self.root / "candidate-receipt.json").write_text("{}\n")
        extra = self.root / "gitleaks"
        extra.write_bytes(b"binary must never be emitted")
        with self.assertRaises(CANDIDATE.CandidateError):
            CANDIDATE.emit_public_metadata(self.root, complete=False)
        extra.unlink()
        (self.root / "candidate-receipt.json").write_bytes(
            b"x" * (CANDIDATE.MAX_FILE_BYTES + 1))
        with self.assertRaises(CANDIDATE.CandidateError):
            CANDIDATE.emit_public_metadata(self.root, complete=False)

    def test_rejected_existing_destination_cannot_be_emitted(self):
        (self.root / "candidate-receipt.json").write_text("private pre-existing bytes")
        output, error = io.StringIO(), io.StringIO()
        with mock.patch.object(sys, "argv", [
                "gitleaks_candidate.py", "--destination", str(self.root)]):
            with redirect_stdout(output), redirect_stderr(error):
                self.assertEqual(CANDIDATE.main(), 2)
        self.assertNotIn("private", output.getvalue() + error.getvalue())
        self.assertNotIn(CANDIDATE.MARKER, output.getvalue())


if __name__ == "__main__":
    unittest.main()
