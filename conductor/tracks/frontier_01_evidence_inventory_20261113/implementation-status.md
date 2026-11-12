# F01 implementation checkpoint — 2026-11-13

This increment adds explicit protection evidence states to the estate scan.

## Behavioral acceptance
- A 403 read from either GitHub protection API is **unknown**, not demonstrated absence.
- An observed positive ruleset or branch protection result is **present** even if another read is denied.
- Only complete negative reads may establish **absent**.
- A recorded present configuration does not prove merge-gate enforcement.
- The output retains missing-as-violation semantics while providing unknown and observed-absent counts independently.

## Execution and limitations
Implementation proposed in a PR; hosted checks and canary must pass before merging. This is **not** a new comprehensive live-estate inventory. No write permissions, repository rulesets, branch protection, private registry disclosure or consumer workflows are modified.

## Remaining F01 work
Reconcile accessible GitHub estate against the historical registry with identity- and scope-aware pagination; schema-validate evidence, include freshness/commit/run provenance and partial coverage handling; protect public/private evidence boundaries; generate dated redacted aggregates and validate scheduled-run history. No F01 completion claim until the complete track acceptance gates are met.
