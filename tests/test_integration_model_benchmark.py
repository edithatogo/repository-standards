import tempfile
import unittest
from pathlib import Path

from integration_model_benchmark import CASES, evaluate, verify_assets


class IntegrationModelBenchmarkTests(unittest.TestCase):
    def test_always_accepting_model_records_harmful_acceptances(self):
        receipt = evaluate(lambda a, b: 1.0)
        harmful = sum(not case[3] for case in CASES)
        self.assertEqual(receipt['nli']['false_accept'], harmful)
        self.assertEqual(receipt['exact']['false_accept'], 0)
        self.assertFalse(receipt['qualified_for_automated_merge'])
        self.assertEqual(len(receipt['cases']), len(CASES))

    def test_always_abstaining_model_records_missed_safe_cases(self):
        receipt = evaluate(lambda a, b: 0.0)
        self.assertEqual(receipt['nli']['false_accept'], 0)
        self.assertEqual(receipt['nli']['false_reject'], sum(case[3] for case in CASES))
        self.assertFalse(receipt['qualified_for_automated_merge'])

    def test_bad_score_fails_closed(self):
        for value in (float('nan'), float('inf'), -0.1, 1.1, True):
            with self.subTest(value=value), self.assertRaises(ValueError):
                evaluate(lambda a, b: value)

    def test_unverified_assets_never_load(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                verify_assets(Path(directory))
            (Path(directory) / 'config.json').write_text('{}')
            with self.assertRaises(ValueError):
                verify_assets(Path(directory))
