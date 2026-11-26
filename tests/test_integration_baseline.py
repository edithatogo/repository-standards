import subprocess
import tempfile
import unittest
from pathlib import Path

from integration_baseline import merge_preview, retry_disposition


class MergePreviewTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.work = Path(self.tmp.name) / 'work'
        self.repo = Path(self.tmp.name) / 'objects.git'
        self.work.mkdir()
        self.git('init', '-q', '-b', 'main')
        self.git('config', 'user.name', 'Fixture')
        self.git('config', 'user.email', 'fixture@example.invalid')
        self.ancestor = self.commit('first\nmiddle\nlast\n')

    def git(self, *args, repo=None):
        return subprocess.check_output(['git', '-C', str(repo or self.work), *args], text=True).strip()

    def commit(self, text):
        (self.work / 'file.txt').write_text(text)
        self.git('add', 'file.txt')
        self.git('commit', '-qm', 'fixture')
        return self.git('rev-parse', 'HEAD')

    def branches(self, head_text, base_text):
        self.git('checkout', '-qb', 'feature')
        head = self.commit(head_text)
        self.git('checkout', '-q', 'main')
        base = self.commit(base_text)
        self.git('clone', '-q', '--bare', str(self.work), str(self.repo))
        return head, base

    def test_non_overlapping_edits_preserve_both_branches_and_refs(self):
        head, base = self.branches('changed first\nmiddle\nlast\n', 'first\nmiddle\nchanged last\n')
        refs = self.git('show-ref', repo=self.repo)
        result = merge_preview(self.repo, head, base)
        self.assertEqual(result['disposition'], 'candidate_tree')
        self.assertEqual(self.git('show', result['tree_sha'] + ':file.txt', repo=self.repo),
                         'changed first\nmiddle\nchanged last')
        self.assertEqual(self.git('show-ref', repo=self.repo), refs)

    def test_material_conflict_returns_no_candidate(self):
        head, base = self.branches('feature\nmiddle\nlast\n', 'base\nmiddle\nlast\n')
        result = merge_preview(self.repo, head, base)
        self.assertEqual(result, {'disposition': 'unresolved_conflict', 'head_sha': head, 'base_sha': base})

    def test_non_sha_and_non_bare_repository_are_rejected(self):
        with self.assertRaises(ValueError):
            merge_preview(self.work, 'HEAD', self.ancestor)
        with self.assertRaises(ValueError):
            merge_preview(self.work, self.ancestor, self.ancestor)

    def test_custom_merge_driver_configuration_is_rejected(self):
        head, base = self.branches('feature\nmiddle\nlast\n', 'base\nmiddle\nlast\n')
        self.git('config', 'merge.custom.driver', 'false', repo=self.repo)
        with self.assertRaises(ValueError):
            merge_preview(self.repo, head, base)

    def test_merge_attributes_are_held(self):
        (self.work / '.gitattributes').write_text('*.txt merge=union\n')
        self.git('add', '.gitattributes')
        self.git('commit', '-qm', 'attributes')
        head, base = self.branches('feature\nmiddle\nlast\n', 'base\nmiddle\nlast\n')
        self.assertEqual(merge_preview(self.repo, head, base)['disposition'], 'hold_attributes')

    def test_unknown_commit_fails_closed(self):
        head, base = self.branches('feature\nmiddle\nlast\n', 'base\nmiddle\nlast\n')
        with self.assertRaises(ValueError):
            merge_preview(self.repo, head, 'f' * 40)


class RetryPlanTests(unittest.TestCase):
    def setUp(self):
        self.head = 'a' * 40
        self.base = 'b' * 40
        self.run = {'id': 42, 'run_attempt': 1, 'head_sha': self.head,
                    'event': 'pull_request', 'status': 'completed', 'conclusion': 'startup_failure'}

    def decide(self, **changes):
        return retry_disposition({**self.run, **changes}, self.head, self.base, self.base)

    def test_only_structured_startup_failure_is_retry_candidate(self):
        self.assertEqual(self.decide(), 'inspect_retry_candidate')
        for conclusion in ('failure', 'cancelled', 'timed_out', 'action_required', 'success', 'stale', 'neutral'):
            with self.subTest(conclusion=conclusion):
                self.assertEqual(self.decide(conclusion=conclusion), 'hold')

    def test_retry_budget_is_two_reruns(self):
        self.assertEqual(self.decide(run_attempt=2), 'inspect_retry_candidate')
        self.assertEqual(self.decide(run_attempt=3), 'budget_exhausted')
        self.assertEqual(self.decide(run_attempt=0), 'hold')
        self.assertEqual(self.decide(run_attempt=True), 'hold')

    def test_stale_candidate_or_base_is_held(self):
        self.assertEqual(self.decide(head_sha='c' * 40), 'hold')
        self.assertEqual(retry_disposition(self.run, self.head, self.base, 'c' * 40), 'hold')

    def test_unknown_and_pending_are_not_retry_candidates(self):
        self.assertEqual(self.decide(status='queued', conclusion=None), 'wait')
        self.assertEqual(self.decide(event='push'), 'hold')
        self.assertEqual(self.decide(id=None), 'hold')
