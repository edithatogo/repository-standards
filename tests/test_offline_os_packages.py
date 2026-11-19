"""Pinned OS preparation tests. Fixtures do not qualify a Docker image."""
from __future__ import annotations

import contextlib
import copy
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "os_preparation", ROOT / "security/offline-ai/provision/prepare_os_packages.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
PRIVATE = "SYNTHETIC_PRIVATE_DIAGNOSTIC"


class OSPackageTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="os-package-evidence-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.source = self.root / "source"
        self.source.mkdir()
        self.base_status = self.root / "base-status"
        self.base_status.write_bytes(b"fixture dpkg status\n")
        self.payloads = {name: ("fixture-" + name).encode()
                         for name in ("git", "libatomic1", "libgomp1")}
        packages = []
        for name, payload in self.payloads.items():
            filename = name + "_1.0-1_amd64.deb"
            packages.append({"name": name, "version": "1.0-1", "architecture": "amd64",
                             "filename": filename,
                             "url": "https://deb.debian.org/debian/pool/main/g/git/" + filename,
                             "size_bytes": len(payload),
                             "sha256": hashlib.sha256(payload).hexdigest()})
        self.catalog = {
            "schema_version": 1, "distribution": "trixie", "architecture": "amd64",
            "base_image": "docker.io/library/python@sha256:" + "a" * 64,
            "base_status_sha256": hashlib.sha256(self.base_status.read_bytes()).hexdigest(),
            "required_base": {"libstdc++6": "1.0-1", "libgcc-s1": "1.0-1"},
            "packages": packages,
        }
        self.metadata_error = False
        self.installed_error = False
        self.install_error = False
        self.audit_error = False
        self.calls = []
        self.write_catalog()
        (self.source / "base-images.json").write_text(json.dumps(
            {"python": {"reference": self.catalog["base_image"]}}))
        (self.source / "prepare_os_packages.py").write_bytes(Path(MODULE.__file__).read_bytes())
        self.debs = self.source / "debs"
        self.debs.mkdir()
        for package in packages:
            (self.debs / package["filename"]).write_bytes(self.payloads[package["name"]])

    def write_catalog(self):
        (self.source / MODULE.CATALOG).write_text(json.dumps(self.catalog))

    def fake_response(self, request, timeout):
        name = Path(request.full_url).name.split("_")[0]
        response = io.BytesIO(self.payloads[name])
        response.geturl = lambda: request.full_url
        return response

    def fake_command(self, arguments, *, capture=False):
        args = [str(arg) for arg in arguments]
        self.calls.append(args)
        if args[:2] == ["dpkg-deb", "--field"]:
            package = next(p for p in self.catalog["packages"]
                           if p["filename"] == Path(args[2]).name)
            version = "9.9-1" if self.metadata_error else package["version"]
            return (f"Package: {package['name']}\nVersion: {version}\n"
                    f"Architecture: {package['architecture']}\n").encode()
        if args == ["dpkg", "--print-architecture"]:
            return b"amd64\n"
        if args[:2] == ["dpkg", "--install"]:
            self.assertFalse(capture)
            self.assertEqual({Path(p).name for p in args[2:]},
                             {p["filename"] for p in self.catalog["packages"]})
            if self.install_error:
                raise subprocess.CalledProcessError(1, args, output=PRIVATE, stderr=PRIVATE)
            return b""
        if args[:2] == ["dpkg", "--purge"]:
            self.assertEqual(args[2:], self.catalog.get("purge"))
            self.assertFalse(capture)
            return b""
        if args[0] == "dpkg-query":
            versions = dict(self.catalog["required_base"])
            versions.update({p["name"]: p["version"] for p in self.catalog["packages"]})
            if not getattr(self, "purge_incomplete", False):
                for name in self.catalog.get("purge", []):
                    del versions[name]
            if self.installed_error:
                versions["git"] = "9.9-1"
            return "".join(f"{name}\t{version}\tamd64\tii \n"
                           for name, version in sorted(versions.items())).encode()
        if args == ["dpkg", "--audit"]:
            return PRIVATE.encode() if self.audit_error else b""
        self.fail("unexpected command")

    def invoke(self, *, install=False):
        receipt = self.root / "receipt.json"
        arguments = (["--install", str(self.source)] if install else
                     ["--destination", str(self.root / "prepared")])
        output, error = io.StringIO(), io.StringIO()
        with (patch.object(MODULE, "HERE", self.source),
              patch.object(MODULE, "BASE_STATUS", self.base_status),
              patch.object(MODULE, "command", side_effect=self.fake_command),
              patch.object(MODULE.urllib.request, "urlopen", side_effect=self.fake_response),
              contextlib.redirect_stdout(output), contextlib.redirect_stderr(error)):
            status = MODULE.main([*arguments, "--receipt", str(receipt)])
        self.assertEqual(output.getvalue(), "")
        self.assertEqual(error.getvalue(), "" if status == 0 else MODULE.ERROR + "\n")
        data = json.loads(receipt.read_text())
        self.assertFalse(data["release_qualified"])
        self.assertFalse(data["runner_registration_qualified"])
        self.assertEqual(receipt.stat().st_mode & 0o777, 0o600)
        return status, data

    def test_preparation_receipt_binds_catalog_and_verified_bytes(self):
        previous = MODULE.os.umask(0)
        try:
            status, receipt = self.invoke()
        finally:
            MODULE.os.umask(previous)
        self.assertEqual((status, receipt["status"]), (0, "prepared"))
        self.assertEqual(receipt["catalog_sha256"],
                         hashlib.sha256((self.source / MODULE.CATALOG).read_bytes()).hexdigest())
        self.assertEqual((self.root / "prepared" / MODULE.CATALOG).read_bytes(),
                         (self.source / MODULE.CATALOG).read_bytes())
        self.assertFalse(any(c[:2] == ["dpkg", "--install"] for c in self.calls))

    def test_install_verifies_baseline_and_records_real_package_versions(self):
        status, receipt = self.invoke(install=True)
        self.assertEqual((status, receipt["status"]), (0, "installed"))
        self.assertEqual(receipt["installed_versions"]["git"], "1.0-1")
        self.assertEqual(receipt["installed_versions"]["libgcc-s1"], "1.0-1")
        self.assertFalse(any("apt" in c[0] or "--force-depends" in c for c in self.calls))

    def test_wrong_base_is_rejected_before_installing_any_package(self):
        self.base_status.write_bytes(b"another image\n")
        status, receipt = self.invoke(install=True)
        self.assertEqual((status, receipt["last_stage"]), (2, "base-status"))
        self.assertEqual(self.calls, [])

    def test_purge_requires_the_complete_resulting_package_inventory(self):
        self.catalog["required_base"].update({"libncursesw6": "1.0-1", "mount": "1.0-1"})
        self.catalog["purge"] = ["libncursesw6", "mount"]
        (self.source / MODULE.CATALOG).write_text(json.dumps(self.catalog))
        status, receipt = self.invoke(install=True)
        self.assertEqual((status, receipt["status"]), (0, "installed"))
        self.assertEqual(receipt["purged_packages"], ["libncursesw6", "mount"])
        self.assertNotIn("mount", receipt["installed_versions"])
        self.assertNotIn("libncursesw6", receipt["installed_versions"])
        self.assertIn(["dpkg", "--purge", "libncursesw6", "mount"], self.calls)
        (self.root / "receipt.json").unlink()
        self.purge_incomplete = True
        status, receipt = self.invoke(install=True)
        self.assertEqual((status, receipt["last_stage"]), (2, "installed-versions"))

    def test_tampered_package_cannot_reach_dpkg_install(self):
        package = self.catalog["packages"][0]
        (self.debs / package["filename"]).write_bytes(b"tampered")
        status, receipt = self.invoke(install=True)
        self.assertEqual((status, receipt["last_stage"]), (2, "package-verification"))
        self.assertFalse(any(c[:2] == ["dpkg", "--install"] for c in self.calls))

    def test_extra_or_symlinked_package_is_rejected(self):
        extra = self.debs / "extra.deb"
        extra.write_bytes(b"extra")
        with self.assertRaises(MODULE.PreparationError):
            MODULE.verify_packages(self.source, self.catalog)
        extra.unlink()
        package = self.catalog["packages"][0]
        target = self.debs / package["filename"]
        target.unlink()
        target.symlink_to(self.base_status)
        with self.assertRaises(MODULE.PreparationError):
            MODULE.verify_packages(self.source, self.catalog)

    def test_deb_identity_must_match_the_catalog(self):
        self.metadata_error = True
        status, receipt = self.invoke(install=True)
        self.assertEqual((status, receipt["last_stage"]), (2, "package-verification"))
        self.assertFalse(any(c[:2] == ["dpkg", "--install"] for c in self.calls))

    def test_dpkg_failure_leaves_private_fixed_failure_receipt(self):
        self.install_error = True
        previous = MODULE.os.umask(0)
        try:
            status, receipt = self.invoke(install=True)
        finally:
            MODULE.os.umask(previous)
        self.assertEqual((status, receipt["status"], receipt["last_stage"]),
                         (2, "failed", "offline-install"))

    def test_wrong_final_version_or_audit_failure_cannot_pass(self):
        for field in ("installed_error", "audit_error"):
            with self.subTest(field=field):
                setattr(self, field, True)
                status, receipt = self.invoke(install=True)
                self.assertEqual((status, receipt["last_stage"]), (2, "installed-versions"))
                (self.root / "receipt.json").unlink()
                setattr(self, field, False)

    def test_catalog_rejects_traversal_duplicate_packages_and_unpinned_sources(self):
        original = copy.deepcopy(self.catalog)
        changes = [("filename", "../git.deb"), ("sha256", "latest"),
                   ("url", "http://deb.debian.org/debian/pool/main/g/git/git_1.0-1_amd64.deb")]
        for field, value in changes:
            with self.subTest(field=field):
                self.catalog = copy.deepcopy(original)
                self.catalog["packages"][0][field] = value
                self.write_catalog()
                with self.assertRaises(MODULE.PreparationError):
                    MODULE.read_catalog(self.source / MODULE.CATALOG)
        self.catalog = copy.deepcopy(original)
        self.catalog["packages"].append(self.catalog["packages"][0])
        self.write_catalog()
        with self.assertRaises(MODULE.PreparationError):
            MODULE.read_catalog(self.source / MODULE.CATALOG)

    def test_download_size_hash_and_https_redirect_fail_closed(self):
        package = self.catalog["packages"][0]
        good = self.payloads[package["name"]]
        for payload, url in ((good[:-1], package["url"]), (good + b"x", package["url"]),
                             (b"x" * len(good), package["url"]),
                             (good, "http://example.invalid/file")):
            with self.subTest(payload=payload, url=url):
                response = io.BytesIO(payload)
                response.geturl = lambda: url
                target = self.root / "download.deb"
                with patch.object(MODULE.urllib.request, "urlopen", return_value=response):
                    with self.assertRaises(MODULE.PreparationError):
                        MODULE.download(package, target)
                self.assertFalse(target.exists())

    def test_existing_destination_is_never_removed_by_download_failure(self):
        target = self.root / "existing.deb"
        target.write_bytes(b"preserved")
        with self.assertRaises(MODULE.PreparationError):
            MODULE.download(self.catalog["packages"][0], target)
        self.assertEqual(target.read_bytes(), b"preserved")

    def test_command_failure_does_not_publish_subprocess_output(self):
        output, error = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(error):
            with self.assertRaises(subprocess.CalledProcessError):
                MODULE.command([sys.executable, "-c", "import sys; print('" + PRIVATE
                                + "'); print('" + PRIVATE
                                + "', file=sys.stderr); sys.exit(1)"])
        self.assertEqual(output.getvalue() + error.getvalue(), "")

    def test_committed_catalog_is_bound_to_the_slim_base(self):
        directory = ROOT / "security/offline-ai/provision"
        catalog = MODULE.read_catalog(directory / MODULE.CATALOG)
        bases = json.loads((directory / "base-images.json").read_text())
        self.assertEqual(catalog["base_image"], bases["python"]["reference"])
        self.assertTrue(bases["python"]["source"].endswith("/3.15.2-slim-trixie"))
        names = {p["name"] for p in catalog["packages"]}
        self.assertEqual(names, {"libatomic1", "libgomp1", "zlib1g"})
        self.assertNotIn("zlib1g", catalog["required_base"])

    def test_catalog_rejects_the_retired_base_distribution(self):
        self.catalog["distribution"] = "bookworm"
        self.write_catalog()
        with self.assertRaises(MODULE.PreparationError):
            MODULE.read_catalog(self.source / MODULE.CATALOG)


if __name__ == "__main__":
    unittest.main()
