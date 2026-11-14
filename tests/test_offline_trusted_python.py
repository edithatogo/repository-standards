"""Consumer Python packages must not replace the trusted scanner controls."""
from __future__ import annotations

import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
import unittest


OFFLINE = Path(__file__).resolve().parents[1] / "security/offline-ai"
CANARY = "SYNTHETIC_PRIVATE_CONSUMER_OUTPUT"


class TrustedScannerPythonTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="offline-shadow-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.consumer = self.root / "consumer"
        self.package = self.consumer / "security"
        self.package.mkdir(parents=True)
        (self.package / "__init__.py").write_text("")
        tools = self.root / "bin"
        tools.mkdir()
        (tools / "python").symlink_to(sys.executable)
        self.environment = dict(os.environ,
            PATH=str(tools) + os.pathsep + os.environ["PATH"],
            SECURITY_ASSET_MANIFEST=str(self.root / (CANARY + ".missing.json")))
        # An inherited safe-path option must not hide a regression in run.sh.
        self.environment.pop("PYTHONSAFEPATH", None)

    def run_control(self, label, *command):
        functions = [line for line in (OFFLINE / "run.sh").read_text().splitlines()
                     if line.startswith("quiet() {")]
        self.assertEqual(len(functions), 1)
        # Substitute only the fixture's trusted policy mount path. Execute the
        # actual shell function, including its interpreter flags/environment.
        function = functions[0].replace("/policy/security/offline-ai", shlex.quote(str(OFFLINE)))
        invocation = " ".join(shlex.quote(item) for item in ("quiet", label, *command))
        return subprocess.run(["bash", "-c", function + "\n" + invocation],
            cwd=self.consumer, env=self.environment, capture_output=True,
            text=True, check=False, timeout=30)

    def assert_fixed_failure(self, result):
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")
        self.assertEqual(result.stderr, "Security control failed: asset-preflight\n")
        self.assertNotIn(CANARY, result.stdout + result.stderr)

    def test_consumer_cannot_replace_quiet_wrapper_with_success(self):
        (self.package / "quiet_exec.py").write_text(
            "print(" + repr(CANARY) + ")\nraise SystemExit(0)\n")
        result = self.run_control("asset-preflight", "python", "-m", "security.verify_assets")
        self.assert_fixed_failure(result)

    def test_child_module_cannot_be_replaced_after_trusted_wrapper_runs(self):
        # The pre-fix wrapper import delegates to the real wrapper to isolate
        # child import behavior from the separate wrapper-shadowing regression.
        (self.package / "quiet_exec.py").write_text(
            "import runpy\nrunpy.run_path(" + repr(str(OFFLINE / "security/quiet_exec.py"))
            + ", run_name='__main__')\n")
        (self.package / "verify_assets.py").write_text(
            "print(" + repr(CANARY) + ")\nraise SystemExit(0)\n")
        result = self.run_control("asset-preflight", "python", "-m", "security.verify_assets")
        self.assert_fixed_failure(result)

    def test_successful_trusted_child_output_is_also_suppressed(self):
        (self.package / "quiet_exec.py").write_text(
            "print(" + repr(CANARY) + ")\nraise SystemExit(0)\n")
        result = self.run_control("pytest", "python", "-c", "print(" + repr(CANARY) + ")")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout + result.stderr, "")


if __name__ == "__main__":
    unittest.main()
