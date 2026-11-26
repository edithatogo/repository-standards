"""Synthetic PR requirement-preservation diagnostic; never authorizes merges."""

import argparse
import hashlib
import json
import math
import platform
import time
from pathlib import Path


MODEL_ID = 'cross-encoder/nli-MiniLM2-L6-H768'
MODEL_REVISION = 'c847a3c0e1cad93a5343183ef183f3044e3fc7c2'
REFERENCE_REVISION = 'd88f787ffd4647117bca4ca400cbb68d95197d40'
# Independently verified StandardFlow artifact 14925311073 (run 45405500543).
ASSETS = {
    'config.json': '8e5e5a78c49ae3de93ba511c07fe76b895e148b486829429b2027d11e97be1f1',
    'model_quint8_avx2.onnx': '44391a5241a62e0083c1a8899a71e69a092b95aea5ba89e14062925468eceac7',
    'tokenizer.json': 'ff6f6cebf55bcccc4a80b52e956f16ae9d11b0bad02c7db4e7b36975488bf840',
}
THRESHOLD = 0.95  # Inherited experimental threshold, not calibrated for PRs.
CASES = (
    ('exact', 'All required checks must pass.', 'All required checks must pass.', True),
    ('paraphrase', 'Never force-push to the main branch.', 'Force pushes to the main branch are prohibited.', True),
    ('reorder', 'Run lint and tests before merging.', 'Before merging, run both tests and lint.', True),
    ('equivalent', 'Retain logs from failed runs.', 'Keep the logs of unsuccessful runs.', True),
    ('negation', 'All required checks must pass.', 'Required checks need not pass.', False),
    ('scope_loss', 'Run unit tests and integration tests.', 'Run unit tests.', False),
    ('changed_limit', 'Retry at most twice.', 'Retry at most five times.', False),
    ('stale', 'Merge only the verified commit.', 'Merge any commit on the branch.', False),
    ('privilege', 'The model cannot access write credentials.', 'The model can access write credentials.', False),
    ('new_requirement', 'Keep the failure logs.', 'Keep the failure logs and publish the source code.', False),
    ('unrelated', 'Preserve the original branch history.', 'Use a CPU runner.', False),
    ('hold', 'Do not merge a draft pull request.', 'Merge draft pull requests when tests pass.', False),
)


def verify_assets(directory):
    for name, digest in ASSETS.items():
        path = directory / name
        if (not path.is_file() or path.is_symlink() or path.stat().st_size > 100_000_000
                or hashlib.sha256(path.read_bytes()).hexdigest() != digest):
            raise ValueError('unverified model asset: ' + name)


def evaluate(score_pair):
    rows = []
    for case_id, source, candidate, equivalent in CASES:
        score = score_pair(source, candidate)
        if (type(score) not in (int, float) or not math.isfinite(score)
                or not 0 <= score <= 1):
            raise ValueError('invalid diagnostic score')
        rows.append({'id': case_id, 'expected_equivalent': equivalent,
                     'exact': source == candidate, 'nli': score >= THRESHOLD,
                     'score': score})

    def metrics(key):
        return {'n': len(rows),
                'false_accept': sum(row[key] and not row['expected_equivalent'] for row in rows),
                'false_reject': sum(not row[key] and row['expected_equivalent'] for row in rows),
                'correct': sum(row[key] == row['expected_equivalent'] for row in rows)}

    return {'schema_version': 1, 'label_origin': 'synthetic_analyst_authored',
            'threshold': THRESHOLD, 'qualified_for_automated_merge': False,
            'exact': metrics('exact'), 'nli': metrics('nli'), 'cases': rows,
            'fixture_sha256': hashlib.sha256(json.dumps(CASES).encode()).hexdigest()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--assets', type=Path, required=True)
    parser.add_argument('--revision', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    verify_assets(args.assets)
    # Reuse pinned StandardFlow inference implementation; never load remote model code.
    from semantic_benchmark import LocalNLI, entailment_score

    start = time.perf_counter()
    model = LocalNLI(args.assets)
    receipt = evaluate(lambda a, b: entailment_score(model.score(a, b), model.score(b, a)))
    receipt.update(model_id=MODEL_ID, model_revision=MODEL_REVISION,
                   reference_revision=REFERENCE_REVISION, model_files_sha256=ASSETS,
                   tested_revision=args.revision, python=platform.python_version(),
                   machine=platform.machine(), onnxruntime=model.version,
                   elapsed_seconds=time.perf_counter() - start)
    args.output.write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
