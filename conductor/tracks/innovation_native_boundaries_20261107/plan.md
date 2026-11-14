# Innovation Native Standards Implementation Plan

> For agentic workers: execute bounded tasks using superpowers:executing-plans or superpowers:subagent-driven-development; preserve the single-accountable-maintainer model.

**Goal:** One current ownership/native/data/dependency policy with executable checks and verified consumer handoffs.

**Architecture:** Central declarative graph and qualification receipts, local provider implementations and installed consumer evidence.

**Tech Stack:** JSON policy, Python standard-library validation/tests, Rust/Polars/Arrow consumers.

**Spec:** [spec.md](spec.md).

## Global constraints

No automatic mass migration; no second human approval dependency; no production/runtime claim from a policy test; no library-to-application or cyclic core edge.

## Review focus

VOP mislabelled as generic framework; game-runtime/application sharing a repository confused with import ownership; optional Voiage adapter becoming a mutual core dependency; transitive pandas/xarray or host fallback; version declarations mistaken for qualified pins.

## S01 — Central declarations and regression tests

Files: `profiles/scientific-native.json`, `docs/scientific-native.md`, `docs/innovation-ecosystem-boundaries.md`, `tests/test_innovation_scope_policy.py`.

- [x] Write six tests for broad innovation scope, native/Polars contract, VOP promotion, one game-runtime incubator, optional forward adapter/artifact feedback and non-acceptance semantics.
- [x] Run against the pre-change policy: six expected assertion failures, no test errors.
- [x] Update policy/docs and rerun: six tests pass; independent graph check finds no cycle or library-to-application edge.
- [ ] Run the complete repository policy/test harness on the exact PR head and retain hosted results before merging. Local focused checks are not a full-suite claim.

Paignia reconciliation check, 8 November 2026: the updated source-path and then
created-repository assertions failed against their old policy values; all 30 repository unit tests
passed with `PYTHONPATH=scripts python -m unittest discover -s tests -v`; the
`scientific_ecosystem.py policy profiles/scientific-native.json` graph check and
`git diff --check` also passed. Local interpreter: Python 3.12.14. The configured
Python 3.15.1 hosted harness remains required; these policy checks do not qualify
the seed, any consumer or a release.

## S02 — Extend actual consumer conformance auditing

Files: `scripts/audit_estate_conformance.py`; create `tests/test_native_consumer_controls.py` and scope-specific fixtures.
Interface: per-repository audit emits separate declared-policy, source-scan, resolved-dependency, native-execution and release-evidence states; unknown/unrun never becomes pass.

- [ ] Add failing fixtures for hidden Python subprocess, pandas/xarray transitive supported extras, absent native binary and stale/wrong-revision receipts.
- [ ] Implement read-only checks without executing untrusted repository commands or mutating consumer settings.
- [ ] Run `PYTHONPATH=scripts python -m unittest discover -s tests -v`; verify old archetypes unaffected; review and commit.

## S03 — Provider ownership/extraction handoffs

Targets: Innovate PR570 taskbook E01–E05/G01–G04; Kairos track110 S01–S04; Voiage `rust/crates/voiage-domain` and `voiage-numerics`; `edithatogo/paignia` seed `crates/paignia-core`/`paignia-solve` (transferred from the reimbursement incubator's `uogto-game-*`; not published or qualified).

Keep `game-runtime` as the stable policy key. T17.01–T17.17 keeps its IDs through
provider transfer to Paignia, with application .09/.10/.11 handoffs retaining
their external owners. T17.01–T17.03 plus actual T17.09/T17.10 consumers feed static
T17.12 eligibility; dynamic-adapter and per-algorithm receipts remain separate.
Reimbursement plus Innovate can be the first consumer pair. Reuse those receipts
and UOGTO SGC.01–SGC.08; do not add another naming/completion ledger.

- [ ] Record existing callers, mathematical contracts, provider PRs, exact accepted pins and independently computed references.
- [ ] Verify library/provider graph and actual installed consumers, including VOP migration and two game-runtime consumers; an issue is not acceptance.
- [ ] Update central profile evidence references only after tests pass; keep scope-specific unsupported states explicit.

## S04 — Qualified frontier dependency cohorts

Files: existing scientific candidate/receipt schemas and per-consumer locks; add dated records, not guessed evergreen versions.

- [ ] Start with observed Rust1.99.1/Python3.15.2 candidates and current Kairos Polars Git/root-patch closure; inspect newer candidates at execution.
- [ ] Run all five qualification checks and actual publishability tests; record blockers/owner/revisit for retained versions.
- [ ] Requalify RNG/schema/ABI changes and dependent consumers; never relabel historical receipts or waive existing HPC gates.

## S05 — Mature release conformance

- [ ] Bind beta/RC/stable support matrices to exact source/artifact/native/numerical/security/consumer receipts.
- [ ] Require separate evidence for scientific accuracy, empirical validity and comparative performance; reject documentation-only acceptance.
- [ ] Run complete central harness, review scoped rollout and publish no package/data/manuscript without separately authorised action.
