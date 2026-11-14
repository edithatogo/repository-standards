"""The qualification source may differ from HEAD only by its immutable pin."""
from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


REPOSITORY = Path(__file__).resolve().parents[1]
SELECTOR = REPOSITORY / "security/offline-ai/provision/select_policy.py"
WORKFLOW = ".github/workflows/reusable-ai-sec-pipeline.yml"
FAILURE = "Runtime policy source verification failed\n"
ORIGINAL_PIN = "0" * 40
TEMPLATE = (
    "name: Fixture\njobs:\n  offline:\n    steps:\n"
    "      - uses: actions/checkout@" + "a" * 40 + "\n"
    "        with:\n          repository: owner/policy\n"
    "          ref: " + ORIGINAL_PIN + "\n"
    "      - run: docker run --entrypoint=bash --network none image /policy/run.sh\n"
)


class PolicySourceTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="policy-source-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.repo = self.root / "repository"
        self.repo.mkdir()
        self.git("init", "-q")
        self.git("config", "user.name", "fixture")
        self.git("config", "user.email", "fixture.invalid")
        self.git("config", "core.hooksPath", "/dev/null")
        self.workflow = self.repo / WORKFLOW
        self.workflow.parent.mkdir(parents=True)
        self.workflow.write_text(TEMPLATE)
        (self.repo / "scanner.txt").write_text("committed policy\n")
        self.source = self.commit()
        self.attempt = 0

    def git(self, *args):
        return subprocess.check_output(["git", "-C", str(self.repo), *args],
                                       stderr=subprocess.DEVNULL).decode().strip()

    def commit(self):
        self.git("add", ".")
        self.git("commit", "-qm", "fixture")
        return self.git("rev-parse", "HEAD")

    def head(self, content=None, pin=None):
        content = TEMPLATE if content is None else content
        pin = self.source if pin is None else pin
        self.workflow.write_text(content.replace(ORIGINAL_PIN, pin))
        return self.commit()

    def select(self):
        self.attempt += 1
        temporary = self.root / f"attempt-{self.attempt}"
        temporary.mkdir()
        output = temporary / "github-output"
        result = subprocess.run([sys.executable, "-I", str(SELECTOR), str(self.repo),
                                 str(temporary), str(output)], capture_output=True,
                                text=True, check=False, timeout=30)
        return result, output, temporary / "offline-qualified-policy"

    def assert_rejected(self):
        result, output, worktree = self.select()
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertEqual(result.stdout, "")
        self.assertEqual(result.stderr, FAILURE)
        self.assertFalse(output.exists())
        self.assertFalse(worktree.exists())

    def test_ref_only_change_is_accepted_and_exports_the_exact_source(self):
        head = self.head()
        result, output, worktree = self.select()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(result.stdout + result.stderr, "")
        self.assertEqual(output.read_text(), f"path={worktree}\nsha={self.source}\n")
        self.assertEqual((worktree / WORKFLOW).read_bytes(), TEMPLATE.encode())
        self.assertEqual(self.git("rev-parse", "HEAD"), head)

    def test_entrypoint_change_is_rejected(self):
        self.head(TEMPLATE.replace("--entrypoint=bash", "--entrypoint=true"))
        self.assert_rejected()

    def test_network_flag_change_is_rejected(self):
        self.head(TEMPLATE.replace("--network none", "--network host"))
        self.assert_rejected()

    def test_other_workflow_bytes_cannot_change_with_the_pin(self):
        for content in (TEMPLATE.replace("name: Fixture", "name: Other"),
                        TEMPLATE + "# changed comment\n", TEMPLATE.rstrip("\n"),
                        TEMPLATE.replace("ref: ", "ref:  ")):
            with self.subTest(content=content):
                self.head(content)
                self.assert_rejected()

    def test_extra_anchored_ref_in_head_is_rejected(self):
        self.head(TEMPLATE + "          ref: " + "b" * 40 + "\n")
        self.assert_rejected()

    def test_extra_ref_in_the_source_is_also_rejected(self):
        self.workflow.write_text(TEMPLATE + "          ref: " + "b" * 40 + "\n")
        self.source = self.commit()
        self.head(TEMPLATE)
        self.assert_rejected()

    def test_other_changed_paths_remain_rejected(self):
        (self.repo / "scanner.txt").write_text("different policy\n")
        self.head()
        self.assert_rejected()

    def test_existing_non_ancestor_pin_is_rejected(self):
        tree = self.git("rev-parse", self.source + "^{tree}")
        unrelated = self.git("commit-tree", tree, "-m", "unrelated source")
        self.head(pin=unrelated)
        self.assert_rejected()

    def test_mutable_or_malformed_pin_is_rejected(self):
        for pin in ("main", "a" * 39, "A" * 40, "a" * 41):
            with self.subTest(pin=pin):
                self.head(pin=pin)
                self.assert_rejected()

    def test_local_replace_ref_cannot_disguise_a_workflow_change(self):
        self.head(TEMPLATE.replace("--entrypoint=bash", "--entrypoint=true"))
        forged = self.git("commit-tree", self.git("rev-parse", "HEAD^{tree}"),
                          "-m", "replacement source")
        self.git("replace", self.source, forged)
        self.assert_rejected()

    def test_dirty_checkout_cannot_supply_uncommitted_selector_inputs(self):
        self.head()
        self.workflow.write_text(TEMPLATE.replace(ORIGINAL_PIN, self.source) + "# uncommitted\n")
        self.assert_rejected()
        self.git("restore", "--", WORKFLOW)
        (self.repo / "untracked-policy.txt").write_text("uncommitted\n")
        self.assert_rejected()

    def test_cli_failure_does_not_echo_source_or_arguments(self):
        result = subprocess.run([sys.executable, "-I", str(SELECTOR),
                                 "SYNTHETIC_PRIVATE_DIAGNOSTIC"], capture_output=True,
                                text=True, check=False, timeout=30)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")
        self.assertEqual(result.stderr, FAILURE)


if __name__ == "__main__":
    unittest.main()
