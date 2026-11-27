# Execution plan — Archetype-based verification and scientific reproducibility

## Incremental deliverables
1. Define one-command verifier interface plus receipt schema versioning, exact commit/toolchain/dependency locks, command exits, test inventory, seeds, timeout/resource budgets, retries/quarantine expiry and artifacts.
2. Implement profile canaries: Python (ruff, basedpyright, pytest/hypothesis, bandit, pip-audit, vulture/scalene when justified); Rust (fmt, clippy, nextest, cargo-audit/deny, proptest, fuzz, sanitizer/Miri as applicable); Node, data, docs, LaTeX and Typst analogues.
3. Add property/metamorphic/mutation tests and non-circular Merkle evidence under existing track; use reproducible fixtures, golden references and numerical regression budgets for scientific consumers.
4. Establish tiered mandatory vs advisory status and CI cost ceilings, with no unbounded fuzz or expensive profiler in every PR.
5. Add known-failing/known-passing fixtures proving that a fabricated, malformed, stale or cross-commit receipt cannot pass.

## Implementation loop and review
For every numbered increment: define fixtures and negative controls, demonstrate failing tests, implement the minimum coherent change, run focused and full policy checks, perform independent automated security/behavioral review, fix findings, then verify hosted canary and exact-commit evidence. Update track status only after evidence; archive only after documented acceptance. Use scoped PRs, never force-push or bypass required checks.

## Owned paths (initial candidates; reconcile before edits)
- `schemas/verification-receipt.schema.json`
- `profiles/archetype-profiles.json`
- `conductor/tracks/bounded_execution_merkle_lineage_20261110/`

## Release gate
For each canary profile the same revision yields valid repeatable receipts; mutated/failing fixtures fail; resource/cost budgets are bounded; scientific correctness is not inferred from green infrastructure tests.

## Blockers and recovery
API forbidden, unsupported entitlement, unstarted runners, stale branch, unmerged consumer PR and nondeterministic test are explicit unresolved states. Maintain retry bounds and no-false-green accounting. Do not claim estate deployment when only central code passes.

## First bounded increment — 27 November 2026

Refs [#19](https://github.com/edithatogo/repository-standards/issues/19) and
[#192](https://github.com/edithatogo/repository-standards/issues/192).
Independent F04 source development is permitted alongside the held F03/F06
integration candidate. Do not alter #196 or enable live writes, automatic merges,
model-generated code execution, real PR replay, or estate rollout.

Add `scripts/verify_receipt.py` and `tests/test_verification_receipt.py` only
for the first semantic verification slice. Preserve the existing v1 schema and
producers. The opt-in offline verifier uses the already pinned fastjsonschema
dependency; it expects a receipt digest, exact repository and full commit SHA,
nonempty required-check inventory and explicit freshness cutoff independently
supplied by the caller from a trusted route.

```sh
python scripts/verify_receipt.py "$RECEIPT" \
  --sha256 "$TRUSTED_RECEIPT_DIGEST" --repository "$EXPECTED_REPOSITORY" \
  --revision "$EXPECTED_COMMIT" --require-check tests --require-check security \
  --not-before "$TRUSTED_FRESHNESS_CUTOFF"
```

Exit 0 means only that the receipt is structurally and semantically consistent,
matches its expected digest and context, and all listed checks passed. Exit 1
means a coherent nonpassing result; any failed check yields fail, otherwise any
skip yields partial. Exit 2 means invalid, unavailable, incomplete, stale or
inconsistent evidence. Duplicate keys and check names, missing required checks,
nonfinite numbers and substituted bytes fail closed. A passing result does not
authenticate a producer, independently verify underlying CI runs/artifacts or
grant any write/merge authority. A digest calculated from the same untrusted
receipt is not independent evidence. Artifact paths and evidence strings are
never opened or executed. Keep profile-specific gate discovery and signed
provenance/actual artifact verification separate.

Local TDD at main 7e4dcadc02130c79aa974927fd672b52c34e3aeb: missing-module
failure then ten focused synthetic tests passed, Python 3.13.5 and installed
fastjsonschema 2.21.2. The original schema blob
730561b4ffd2ab8790905f76b648eefcfc8c328f was independently reproduced.
Full repository clone was unavailable due to DNS; full pinned Python 3.15.2
policy suite and independent code/security review remain hosted gates.
Source qualification is not a consumer canary or estate deployment.
No change to the shared tracks registry in this increment: #155 already owns
that path. Track-local index and metadata carry the bounded status.
