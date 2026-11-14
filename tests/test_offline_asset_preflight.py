"""Process-level offline asset checks, using only stdlib and synthetic bytes.

The fake Docker verifies build sequencing; it is not scanner-image qualification.
These checks run in the existing hosted policy gate without installing pytest.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
OFFLINE = ROOT / "security/offline-ai"
FAILURE = "Scanner toolchain asset verification failed\n"


class OfflineAssetPreflightTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="offline-assets-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def bundle(self, parent):
        vendor = parent / "vendor"
        files = {
            "bin/gitleaks": "/usr/local/bin/gitleaks",
            "bin/opengrep": "/usr/local/bin/opengrep",
            "requirements.lock": "/opt/offline-ai/requirements.lock",
            "python-wheels/fixture-0.0-py3-none-any.whl": "/opt/offline-ai/wheels/fixture-0.0-py3-none-any.whl",
            "promptfoo/package.json": "/opt/promptfoo/package.json",
            "promptfoo/package-lock.json": "/opt/promptfoo/package-lock.json",
            "promptfoo/node_modules/promptfoo/bin/cli.js": "/opt/promptfoo/node_modules/promptfoo/bin/cli.js",
            "models/gliner-pii/config.json": "/opt/models/gliner-pii/config.json",
            "models/gliner-pii/model.safetensors": "/opt/models/gliner-pii/model.safetensors",
        }
        records = []
        for relative, installed in files.items():
            path = vendor / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"synthetic reviewed fixture: " + relative.encode())
            path.chmod(0o755 if relative.startswith("bin/") or relative.endswith("cli.js") else 0o644)
            records.append({"path": installed, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
        link = vendor / "promptfoo/node_modules/.bin/promptfoo"
        link.parent.mkdir(parents=True)
        link.symlink_to("../promptfoo/bin/cli.js")
        payload = {"schema_version": 2, "files": records, "symlinks": [{
            "path": "/opt/promptfoo/node_modules/.bin/promptfoo",
            "target": "../promptfoo/bin/cli.js",
        }]}
        (vendor / "manifest.json").write_text(json.dumps(payload))
        return vendor

    def verify(self, vendor):
        return subprocess.run(
            [sys.executable, "-m", "security.verify_vendor", str(vendor)],
            env=dict(os.environ, PYTHONPATH=str(OFFLINE)),
            capture_output=True, text=True, check=False, timeout=30,
        )

    def assert_rejected(self, result):
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")
        self.assertEqual(result.stderr, FAILURE)

    def test_complete_supplied_bundle_verifies_in_process(self):
        result = self.verify(self.bundle(self.root))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout + result.stderr, "")

    def test_missing_supplied_components_are_rejected(self):
        for relative in ("bin/opengrep", "requirements.lock", "promptfoo/package-lock.json",
                         "models/gliner-pii/model.safetensors", "python-wheels/fixture-0.0-py3-none-any.whl"):
            with self.subTest(component=relative), tempfile.TemporaryDirectory(dir=self.root) as temporary:
                vendor = self.bundle(Path(temporary))
                (vendor / relative).unlink()
                self.assert_rejected(self.verify(vendor))

    def test_tampering_is_rejected(self):
        for relative in ("bin/gitleaks", "requirements.lock", "models/gliner-pii/model.safetensors"):
            with self.subTest(component=relative), tempfile.TemporaryDirectory(dir=self.root) as temporary:
                vendor = self.bundle(Path(temporary))
                (vendor / relative).write_text("synthetic-private-marker")
                self.assert_rejected(self.verify(vendor))

    def test_bad_manifest_errors_are_value_free(self):
        vendor = self.bundle(self.root)
        for content in ('{"schema_version": 2, "schema_version": 2}',
                        '{"synthetic-private-marker": NaN}', 'null', '{broken-json'):
            with self.subTest(content=content):
                (vendor / "manifest.json").write_text(content)
                self.assert_rejected(self.verify(vendor))

    def build(self, *, tamper=False, missing=False):
        checkout = self.root / "checkout"
        checkout.mkdir()
        subprocess.run(["git", "init", "-q", str(checkout)], check=True, capture_output=True, timeout=30)
        vendor = self.bundle(checkout)
        if tamper:
            (vendor / "requirements.lock").write_text("synthetic-private-marker")
        if missing:
            (vendor / "bin/opengrep").unlink()
        destination = checkout / "security/offline-ai"
        shutil.copytree(OFFLINE / "security", destination / "security",
                        ignore=shutil.ignore_patterns("__pycache__"))
        (destination / "docker").mkdir()
        shutil.copy2(OFFLINE / "docker/build_offline.sh", destination / "docker/build_offline.sh")
        tools = self.root / "tools"
        tools.mkdir()
        calls = self.root / "docker-calls.jsonl"
        driver = tools / "docker"
        driver.write_text("#!" + sys.executable + "\nimport json, os, sys\n"
            "with open(os.environ['FAKE_DOCKER_CALLS'], 'a') as stream: stream.write(json.dumps(sys.argv[1:]) + '\\n')\n"
            "if sys.argv[1:3] == ['image', 'inspect']: print('localhost/offline-ai-security@sha256:' + 'c' * 64)\n")
        driver.chmod(0o755)
        environment = dict(os.environ,
            PATH=str(tools) + os.pathsep + str(Path(sys.executable).parent) + os.pathsep + os.environ["PATH"],
            BASE_IMAGE="localhost/synthetic-base@sha256:" + "a" * 64,
            FAKE_DOCKER_CALLS=str(calls))
        result = subprocess.run(["bash", "security/offline-ai/docker/build_offline.sh"],
            cwd=checkout, env=environment, capture_output=True, text=True, check=False, timeout=30)
        return result, calls

    def test_missing_bundle_is_rejected_before_docker(self):
        result, calls = self.build(missing=True)
        self.assert_rejected(result)
        self.assertFalse(calls.exists())

    def test_tampered_bundle_is_rejected_before_docker(self):
        result, calls = self.build(tamper=True)
        self.assert_rejected(result)
        self.assertFalse(calls.exists())

    def test_valid_bundle_reaches_network_disabled_build_in_fake_driver(self):
        result, calls = self.build()
        self.assertEqual(result.returncode, 0, result.stderr)
        commands = [json.loads(line) for line in calls.read_text().splitlines()]
        builds = [command for command in commands if command[0] == "build"]
        self.assertEqual(len(builds), 1)
        self.assertIn("--network=none", builds[0])
        self.assertIn("--pull=false", builds[0])


if __name__ == "__main__":
    unittest.main()
