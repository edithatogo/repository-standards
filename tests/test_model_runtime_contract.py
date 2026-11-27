import hashlib
import tempfile
import unittest
from pathlib import Path

import model_runtime_contract as runtime


IMAGE = 'docker.io/library/python@sha256:' + 'a' * 64


class RuntimeContractTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        (self.root / 'wheels').mkdir()
        self.wheel = self.root / 'wheels/fixture-1.0-py3-none-any.whl'
        self.wheel.write_bytes(b'synthetic wheel bytes')
        self.lock = self.root / 'requirements.lock'
        self.lock.write_text('fixture==1.0 --hash=sha256:' + hashlib.sha256(self.wheel.read_bytes()).hexdigest() + '\n')

    def command(self, image=IMAGE, **changes):
        return runtime.dependency_probe_argv(self.root, **dict(image=image,
            expected_lock_digest=hashlib.sha256(self.lock.read_bytes()).hexdigest(), **changes))

    def test_fixed_dependency_probe_cannot_execute_generated_code(self):
        argv = self.command()
        for option in ('--network=none', '--read-only', '--cap-drop=ALL', '--security-opt=no-new-privileges',
                       '--user=65534:65534', '--pids-limit=64', '--memory=1g', '--memory-swap=1g',
                       '--cpus=1', '--pull=never', '--require-hashes', '--no-index', '--only-binary=:all:',
                       '--dry-run', '--ignore-installed'):
            self.assertIn(option, argv)
        self.assertIn(f'type=bind,src={self.root},dst=/input,readonly', argv)
        self.assertIn(IMAGE, argv)
        self.assertNotIn('--privileged', argv)
        self.assertNotIn('sh', argv)

    def test_unpinned_image_and_substituted_lock_rejected(self):
        with self.assertRaises(runtime.RuntimeContractError):
            self.command('python:latest')
        with self.assertRaises(runtime.RuntimeContractError):
            runtime.dependency_probe_argv(self.root, image=IMAGE, expected_lock_digest='b' * 64)

    def test_unlocked_or_option_bearing_dependencies_rejected(self):
        for line in ('fixture>=1.0', 'fixture @ https://example.invalid/fixture.whl',
                     '--extra-index-url https://example.invalid/', 'fixture==1.0',
                     self.lock.read_text() + self.lock.read_text()):
            with self.subTest(line=line):
                self.lock.write_text(line)
                with self.assertRaises(runtime.RuntimeContractError):
                    self.command()

    def test_tampered_extra_and_symlinked_wheels_fail_closed(self):
        original = self.wheel.read_bytes()
        self.wheel.write_bytes(b'tampered')
        with self.assertRaises(runtime.RuntimeContractError):
            self.command()
        self.wheel.write_bytes(original)
        extra = self.root / 'wheels/extra-1.0-py3-none-any.whl'
        extra.write_bytes(b'other')
        with self.assertRaises(runtime.RuntimeContractError):
            self.command()
        extra.unlink()
        extra.symlink_to(self.wheel)
        with self.assertRaises(runtime.RuntimeContractError):
            self.command()
