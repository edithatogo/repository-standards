"""Executable orchestration tests; fake Docker is never image qualification."""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


REPO = Path(__file__).resolve().parents[1]
HELPER = Path("security/offline-ai/docker/qualify_image.py")
IMAGE = "localhost/offline-ai-security@sha256:" + "a" * 64
MANIFEST = "b" * 64
CANARY = "SYNTHETIC_PRIVATE_TOOL_OUTPUT"


class ImageQualificationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.policy = self.root / "policy checkout"
        self.policy.mkdir()
        self.helper = self.policy / HELPER
        self.helper.parent.mkdir(parents=True)
        shutil.copyfile(REPO / HELPER, self.helper)
        self.git("init", "-q")
        self.git("add", ".")
        self.git("-c", "user.name=Fixture", "-c", "user.email=fixture@example.test",
                 "commit", "-qm", "Synthetic policy fixture")
        self.sha = self.git("rev-parse", "HEAD").strip()
        self.receipt = self.root / "qualification.json"
        self.log = self.root / "docker-calls.jsonl"
        self.bin = self.root / "bin"
        self.bin.mkdir()
        docker = self.bin / "docker"
        docker.write_text("#!" + sys.executable + "\n" + r'''
import json, os, sys, time
from pathlib import Path
args = sys.argv[1:]
with Path(os.environ["FAKE_DOCKER_LOG"]).open("a") as log:
    log.write(json.dumps(args) + "\n")
if args[:2] == ["context", "inspect"]:
    print(os.environ.get("FAKE_ENDPOINT", "unix:///var/run/docker.sock"))
elif "inspect" in args:
    print(json.dumps([os.environ.get("FAKE_IMAGE", "localhost/offline-ai-security@sha256:" + "a" * 64)]))
elif "run" in args:
    mount = next(value for value in args if value.startswith("type=bind,src="))
    source = Path(mount.removeprefix("type=bind,src=").split(",dst=", 1)[0])
    if (source / "ignored.py").exists():
        sys.exit(23)
    original = os.environ.get("FAKE_MUTATE_ORIGINAL")
    if original:
        Path(original).write_text("changed after the first control")
        if (source / "tracked.txt").read_text() != "committed policy":
            sys.exit(24)
    print("SYNTHETIC_PRIVATE_TOOL_OUTPUT", file=sys.stderr)
    if os.environ.get("FAKE_FAIL_MATCH", "NEVER_MATCH") in " ".join(args):
        print("SYNTHETIC_PRIVATE_TOOL_OUTPUT")
        sys.exit(19)
    if os.environ.get("FAKE_SLEEP_MATCH", "NEVER_MATCH") in " ".join(args):
        time.sleep(4)
elif "rm" in args:
    sys.exit(17 if os.environ.get("FAKE_CLEANUP_FAIL") else 0)
else:
    sys.exit(21)
''', encoding="utf-8")
        docker.chmod(0o700)
        self.env = dict(os.environ, PATH=str(self.bin) + os.pathsep + os.environ["PATH"],
                        FAKE_DOCKER_LOG=str(self.log))
        for key in ("DOCKER_HOST", "DOCKER_CONTEXT", "GIT_DIR", "GIT_WORK_TREE"):
            self.env.pop(key, None)

    def git(self, *args):
        return subprocess.check_output(["git", "-C", str(self.policy), *args], text=True,
                                       stderr=subprocess.DEVNULL)

    def invoke(self, *extra, **environment):
        return subprocess.run(
            [sys.executable, str(self.helper), "--policy-sha", self.sha,
             "--image", IMAGE, "--manifest-sha256", MANIFEST,
             "--receipt", str(self.receipt), *extra],
            env=dict(self.env, **environment), capture_output=True, text=True, timeout=15,
        )

    def calls(self):
        return [json.loads(line) for line in self.log.read_text().splitlines()] if self.log.exists() else []

    def assert_rejected(self, result):
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.receipt.exists())
        self.assertNotIn(CANARY, result.stdout + result.stderr)

    def test_complete_simulation_binds_receipt_to_all_required_stages(self):
        result = self.invoke()
        self.assertEqual(result.returncode, 0, result.stderr)
        receipt = json.loads(self.receipt.read_text())
        self.assertEqual(receipt["image"], IMAGE)
        self.assertEqual(receipt["policy_commit"], self.sha)
        self.assertEqual(receipt["asset_manifest_sha256"], MANIFEST)
        self.assertEqual(receipt["status"], "passed")
        self.assertFalse(receipt["application_adapters_qualified"])
        self.assertFalse(receipt["runner_registration_qualified"])
        self.assertEqual([stage["name"] for stage in receipt["stages"]], [
            "runtime", "network-preflight", "manifest-binding", "asset-preflight",
            "gitleaks-fixtures", "sast-fixtures", "dlp-model", "promptfoo-mock",
        ])
        self.assertTrue(all(stage["status"] == "passed" for stage in receipt["stages"]))
        self.assertEqual(self.receipt.stat().st_mode & 0o777, 0o600)
        self.assertNotIn(CANARY, result.stdout + result.stderr + self.receipt.read_text())
        runs = [call for call in self.calls() if "run" in call]
        self.assertEqual(len(runs), 8)
        mounts = set()
        for call in runs:
            for required in ("--pull=never", "--network=none", "--read-only",
                             "--cap-drop=ALL", "--security-opt=no-new-privileges",
                             "--user=65534:65534", "--pids-limit=256", "--memory=8g", "--cpus=4"):
                self.assertIn(required, call)
            mount = next(value for value in call if value.startswith("type=bind,src="))
            mounts.add(mount)
            self.assertTrue(mount.endswith(",dst=/policy,readonly"))
            self.assertNotIn(str(self.policy), mount)
            self.assertTrue(any(value.startswith("--entrypoint=") for value in call))
            self.assertIn("SECURITY_ASSET_MANIFEST=/opt/offline-ai/manifest.json", call)
            self.assertIn("GLINER_MODEL_DIR=/opt/models/gliner-pii", call)
            self.assertIn(IMAGE, call)
            self.assertNotIn("--privileged", call)
            self.assertNotIn("pull", call)
        self.assertEqual(len(mounts), 1)
        self.assertTrue(any("qualify_model.py" in " ".join(call) for call in runs))

    def test_each_real_stage_failure_records_unexecuted_controls_without_raw_output(self):
        for match in ("import sys", "security.verify_network", "hashlib", "security.verify_assets",
                      "verify_gitleaks.py", "verify_sast_fixtures.py", "qualify_model.py",
                      "promptfooconfig.yaml"):
            with self.subTest(stage=match):
                result = self.invoke(FAKE_FAIL_MATCH=match)
                self.assertNotEqual(result.returncode, 0)
                receipt = json.loads(self.receipt.read_text())
                self.assertEqual(receipt["status"], "failed")
                self.assertEqual(receipt["cleanup_status"], "passed")
                statuses = [stage["status"] for stage in receipt["stages"]]
                self.assertEqual(statuses.count("failed"), 1)
                failed = statuses.index("failed")
                self.assertEqual(statuses[:failed], ["passed"] * failed)
                self.assertEqual(statuses[failed + 1:], ["not-run"] * (7 - failed))
                self.assertNotIn(CANARY, result.stdout + result.stderr + self.receipt.read_text())
                self.receipt.unlink()

    def test_unpinned_or_mismatched_inputs_never_run_docker(self):
        for args in (("--image", "localhost/offline-ai-security:latest"),
                     ("--policy-sha", "main"), ("--policy-sha", "c" * 40),
                     ("--manifest-sha256", "not-a-digest")):
            with self.subTest(args=args):
                self.assert_rejected(self.invoke(*args))
        self.assertEqual(self.calls(), [])

    def test_dirty_or_untracked_policy_is_not_qualified(self):
        self.helper.write_text(self.helper.read_text() + "\n# uncommitted change\n")
        self.assert_rejected(self.invoke())
        self.git("checkout", "--", str(HELPER))
        (self.policy / "untracked.txt").write_text("synthetic")
        self.assert_rejected(self.invoke())
        self.assertEqual(self.calls(), [])

    def test_inspected_image_must_match_requested_digest(self):
        self.assert_rejected(self.invoke(FAKE_IMAGE="localhost/offline-ai-security@sha256:" + "d" * 64))
        self.assertFalse(any("run" in call for call in self.calls()))

    def test_remote_daemon_is_rejected_before_mounting_local_policy(self):
        self.assert_rejected(self.invoke(FAKE_ENDPOINT="ssh://example.test"))
        self.assertFalse(any("run" in call for call in self.calls()))

    def test_stage_timeout_records_failure_and_removes_its_named_container(self):
        result = self.invoke("--stage-timeout", "1", FAKE_SLEEP_MATCH="security.verify_network")
        self.assertNotEqual(result.returncode, 0)
        receipt = json.loads(self.receipt.read_text())
        self.assertEqual(receipt["status"], "failed")
        self.assertEqual(receipt["cleanup_status"], "passed")
        runs = [call for call in self.calls() if "run" in call]
        name = next(arg.removeprefix("--name=") for arg in runs[-1] if arg.startswith("--name="))
        self.assertTrue(any(call[-3:] == ["rm", "--force", name] for call in self.calls()))

    def test_cleanup_failure_is_distinct_and_does_not_claim_qualification(self):
        result = self.invoke(FAKE_FAIL_MATCH="security.verify_network", FAKE_CLEANUP_FAIL="1")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("network-preflight", result.stderr)
        self.assertIn("container-cleanup", result.stderr)
        self.assertEqual(json.loads(self.receipt.read_text())["cleanup_status"], "failed")

    def test_ignored_files_and_later_edits_cannot_change_the_qualified_policy(self):
        (self.policy / ".gitignore").write_text("ignored.py\n")
        original = self.policy / "tracked.txt"
        original.write_text("committed policy")
        self.git("add", ".")
        self.git("-c", "user.name=Fixture", "-c", "user.email=fixture@example.test",
                 "commit", "-qm", "Freeze qualification content")
        self.sha = self.git("rev-parse", "HEAD").strip()
        (self.policy / "ignored.py").write_text("uncommitted input")
        result = self.invoke(FAKE_MUTATE_ORIGINAL=str(original))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(original.read_text(), "changed after the first control")
        self.assertEqual(json.loads(self.receipt.read_text())["policy_commit"], self.sha)

    def test_existing_receipt_is_preserved_and_cannot_mask_failure(self):
        self.receipt.write_text("previous receipt")
        result = self.invoke()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.receipt.read_text(), "previous receipt")
        self.assertEqual(self.calls(), [])

    def test_receipt_cannot_be_written_into_the_policy_checkout(self):
        result = self.invoke("--receipt", str(self.policy / "receipt.json"))
        self.assert_rejected(result)
        self.assertFalse((self.policy / "receipt.json").exists())


if __name__ == "__main__":
    unittest.main()
