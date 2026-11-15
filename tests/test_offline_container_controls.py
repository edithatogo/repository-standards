"""Actual container controls must be observable, not just requested as flags."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


SOURCE = Path(__file__).resolve().parents[1] / "security/offline-ai/security/verify_container.py"
SPEC = importlib.util.spec_from_file_location("offline_container_controls", SOURCE)
CONTROL = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = CONTROL
SPEC.loader.exec_module(CONTROL)

STATUS = """Name:\tpython
Uid:\t65534\t65534\t65534\t65534
Gid:\t65534\t65534\t65534\t65534
CapInh:\t0000000000000000
CapPrm:\t0000000000000000
CapEff:\t0000000000000000
CapBnd:\t0000000000000000
CapAmb:\t0000000000000000
NoNewPrivs:\t1
"""
MOUNTS = """21 1 0:20 / / ro,relatime - overlay overlay rw,lowerdir=/layers
22 21 0:21 / /proc rw,nosuid,nodev,noexec,relatime - proc proc rw
23 21 0:22 / /sys ro,nosuid,nodev,noexec,relatime - sysfs sysfs ro
24 23 0:23 / /sys/fs/cgroup ro,nosuid,nodev,noexec,relatime - cgroup2 cgroup ro
25 21 8:1 /policy-source /policy ro,relatime - ext4 /dev/root rw
26 21 0:24 / /tmp rw,nosuid,relatime - tmpfs tmpfs rw
"""


class ContainerControlTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="container-controls-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.proc = self.root / "proc"
        (self.proc / "self").mkdir(parents=True)
        self.write_proc("status", STATUS)
        self.write_proc("mountinfo", MOUNTS)
        self.write_proc("cgroup", "0::/\n")
        self.controls = self.root / "sys/fs/cgroup"
        self.write_limits(self.controls)
        for target, value in (
            ("PROC_ROOT", self.proc), ("FILESYSTEM_ROOT", self.root),
        ):
            context = patch.object(CONTROL, target, value)
            context.start()
            self.addCleanup(context.stop)
        for target, value in (("geteuid", 65534), ("getegid", 65534)):
            context = patch.object(CONTROL.os, target, return_value=value)
            context.start()
            self.addCleanup(context.stop)
        context = patch.object(CONTROL.sys, "version_info", (3, 15, 2))
        context.start()
        self.addCleanup(context.stop)
        context = patch.object(CONTROL.shutil, "which", return_value="/verified/tool")
        context.start()
        self.addCleanup(context.stop)

    def write_proc(self, name, content):
        (self.proc / "self" / name).write_text(content)

    def write_limits(self, directory):
        directory.mkdir(parents=True, exist_ok=True)
        for name, value in (("memory.max", "8589934592\n"),
                            ("pids.max", "256\n"), ("cpu.max", "400000 100000\n")):
            (directory / name).write_text(value)

    def assert_rejected(self):
        with self.assertRaisesRegex(CONTROL.ContainerIsolationError,
                                    "^Scanner container verification failed$"):
            CONTROL.verify_container()

    def test_restricted_private_cgroup_namespace_passes(self):
        CONTROL.verify_container()

    def test_limits_are_read_from_exact_nested_membership(self):
        self.write_proc("cgroup", "0::/system.slice/docker-qualified.scope\n")
        target = self.controls / "system.slice/docker-qualified.scope"
        self.write_limits(target)
        # Unbounded parent values must not be mistaken for this task's limits.
        (self.controls / "memory.max").write_text("max\n")
        CONTROL.verify_container()
        (target / "pids.max").write_text("max\n")
        self.assert_rejected()

    def test_mount_root_is_removed_from_membership_exactly_once(self):
        self.write_proc("mountinfo", MOUNTS.replace(
            "0:23 / /sys/fs/cgroup", "0:23 /tenant.slice /sys/fs/cgroup"))
        self.write_proc("cgroup", "0::/tenant.slice/job.scope\n")
        self.write_limits(self.controls / "job.scope")
        CONTROL.verify_container()

    def test_escaped_mount_paths_are_resolved_without_shell_interpretation(self):
        self.write_proc("mountinfo", MOUNTS.replace(
            "/sys/fs/cgroup ro,", "/sys/fs/cgroup\\040qualified ro,"))
        self.write_limits(self.root / "sys/fs/cgroup qualified")
        CONTROL.verify_container()

    def test_tighter_positive_limits_pass(self):
        for name, value in (("memory.max", "1073741824\n"),
                            ("pids.max", "128\n"), ("cpu.max", "50000 100000\n")):
            (self.controls / name).write_text(value)
        CONTROL.verify_container()

    def test_unlimited_excessive_zero_missing_and_malformed_limits_fail(self):
        cases = {
            "memory.max": ("max\n", "8589934593\n", "0\n", "-1\n", "8GiB\n", "1 2\n"),
            "pids.max": ("max\n", "257\n", "0\n", "1.5\n"),
            "cpu.max": ("max 100000\n", "400001 100000\n", "0 100000\n", "1 0\n", "1\n", "1 1 1\n"),
        }
        for name, values in cases.items():
            original = (self.controls / name).read_text()
            for value in values:
                with self.subTest(name=name, value=value):
                    (self.controls / name).write_text(value)
                    self.assert_rejected()
            (self.controls / name).unlink()
            with self.subTest(name=name, missing=True):
                self.assert_rejected()
            (self.controls / name).write_text(original)

    def test_parent_limits_cannot_substitute_for_unlimited_process_cgroup(self):
        target = self.controls / "child"
        self.write_limits(target)
        self.write_proc("cgroup", "0::/child\n")
        (target / "memory.max").write_text("max\n")
        self.assert_rejected()

    def test_process_identity_cannot_retain_a_root_saved_or_filesystem_id(self):
        for field in ("Uid", "Gid"):
            for column in range(4):
                values = ["65534"] * 4
                values[column] = "0"
                status = STATUS.replace(field + ":\t65534\t65534\t65534\t65534",
                                        field + ":\t" + "\t".join(values))
                with self.subTest(field=field, column=column):
                    self.write_proc("status", status)
                    self.assert_rejected()
        self.write_proc("status", STATUS)
        with patch.object(CONTROL.os, "geteuid", return_value=0):
            self.assert_rejected()
        with patch.object(CONTROL.os, "getegid", return_value=0):
            self.assert_rejected()

    def test_missing_or_retained_capabilities_and_no_new_privileges_fail(self):
        for field in ("CapInh", "CapPrm", "CapEff", "CapBnd", "CapAmb"):
            for value in ("0000000000000001", "invalid"):
                with self.subTest(field=field, value=value):
                    self.write_proc("status", STATUS.replace(field + ":\t0000000000000000",
                                                            field + ":\t" + value))
                    self.assert_rejected()
            self.write_proc("status", "\n".join(line for line in STATUS.splitlines()
                                                if not line.startswith(field + ":")))
            self.assert_rejected()
        self.write_proc("status", STATUS.replace("NoNewPrivs:\t1", "NoNewPrivs:\t0"))
        self.assert_rejected()

    def test_duplicate_status_fields_are_rejected(self):
        self.write_proc("status", STATUS + "CapEff:\t0000000000000000\n")
        self.assert_rejected()

    def test_root_policy_and_cgroup_mounts_must_be_readonly(self):
        for mount in ("/", "/policy", "/sys/fs/cgroup"):
            with self.subTest(mount=mount):
                self.write_proc("mountinfo", MOUNTS.replace(" " + mount + " ro,",
                                                            " " + mount + " rw,"))
                self.assert_rejected()

    def test_missing_or_writable_nested_policy_mount_is_rejected(self):
        self.write_proc("mountinfo", "\n".join(line for line in MOUNTS.splitlines()
                                               if " /policy " not in line))
        self.assert_rejected()
        self.write_proc("mountinfo", MOUNTS +
                        "27 25 0:25 / /policy/security rw,relatime - tmpfs tmpfs rw\n")
        self.assert_rejected()

    def test_v1_hybrid_and_ambiguous_mounts_are_rejected(self):
        for membership in ("5:memory:/\n", "0::/\n5:memory:/\n", "0::/\n0::/other\n"):
            with self.subTest(membership=membership):
                self.write_proc("cgroup", membership)
                self.assert_rejected()
        self.write_proc("cgroup", "0::/\n")
        self.write_proc("mountinfo", MOUNTS.replace("- cgroup2 cgroup", "- cgroup cgroup"))
        self.assert_rejected()
        self.write_proc("mountinfo", MOUNTS +
                        "27 21 0:23 / /other-cgroup ro,relatime - cgroup2 cgroup ro\n")
        self.assert_rejected()

    def test_cgroup_overmount_cannot_fabricate_limits(self):
        for mount in ("/sys/fs/cgroup", "/sys/fs/cgroup/memory.max", "/sys/fs/cgroup/child"):
            with self.subTest(mount=mount):
                self.write_proc("mountinfo", MOUNTS +
                                f"27 24 0:25 / {mount} ro,relatime - tmpfs tmpfs ro\n")
                self.assert_rejected()

    def test_path_aliases_and_membership_outside_mount_root_fail(self):
        for membership in ("//", "/../", "/a/./b", "/a//b", "/a/", "relative"):
            with self.subTest(membership=membership):
                self.write_proc("cgroup", "0::" + membership + "\n")
                self.assert_rejected()
        self.write_proc("mountinfo", MOUNTS.replace(
            "0:23 / /sys/fs/cgroup", "0:23 /tenant /sys/fs/cgroup"))
        self.write_proc("cgroup", "0::/tenant-other\n")
        self.assert_rejected()

    def test_symlinked_control_file_or_parent_is_rejected(self):
        target = self.root / "fake-limit"
        target.write_text("128\n")
        (self.controls / "pids.max").unlink()
        (self.controls / "pids.max").symlink_to(target)
        self.assert_rejected()
        (self.controls / "pids.max").unlink()
        self.write_limits(self.controls)
        target_directory = self.root / "fake-cgroup"
        self.write_limits(target_directory)
        (self.controls / "child").symlink_to(target_directory, target_is_directory=True)
        self.write_proc("cgroup", "0::/child\n")
        self.assert_rejected()

    def test_oversized_or_nonregular_control_file_is_rejected(self):
        (self.controls / "pids.max").write_text("1" * 4097)
        self.assert_rejected()
        (self.controls / "pids.max").unlink()
        (self.controls / "pids.max").mkdir()
        self.assert_rejected()

    def test_wrong_runtime_or_missing_required_tool_fails(self):
        for version in ((3, 15, 1), (3, 15, 3), (3, 14, 10)):
            with self.subTest(version=version), patch.object(CONTROL.sys, "version_info", version):
                self.assert_rejected()
        with patch.object(CONTROL.shutil, "which", return_value=None):
            self.assert_rejected()

    def test_cli_failure_is_value_free_without_traceback(self):
        result = subprocess.run(
            [sys.executable, str(SOURCE), "--unexpected=SYNTHETIC_PRIVATE_DIAGNOSTIC"],
            capture_output=True, text=True, check=False, timeout=10)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")
        self.assertEqual(result.stderr, "Scanner container verification failed\n")


if __name__ == "__main__":
    unittest.main()
