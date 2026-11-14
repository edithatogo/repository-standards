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
