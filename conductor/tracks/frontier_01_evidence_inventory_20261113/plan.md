# Execution plan — Fresh inventory and evidence-grade conformance

## Incremental deliverables
1. Add coverage-denominator/scope reconciler and typed evidence schema: repository ID, classification, risk, source, observed_at, commit, run, result and explicit unknown status.
2. Test pagination, forks, renamed/empty repositories, inaccessible private repos, rate limits, deleted/archived entries, partial API responses and inconsistent snapshots.
3. Generate bounded redacted JSON/Markdown evidence, attach artifacts and attest audit run provenance; forbid false-green on missing evidence.
4. Compare registry and live estate with drift issue deduplication and freshness SLA; determine which dashboards should be private.
5. Backfill historical audit without overwriting original evidence.

## Implementation loop and review
For every numbered increment: define fixtures and negative controls, demonstrate failing tests, implement the minimum coherent change, run focused and full policy checks, perform independent automated security/behavioral review, fix findings, then verify hosted canary and exact-commit evidence. Update track status only after evidence; archive only after documented acceptance. Use scoped PRs, never force-push or bypass required checks.

## Owned paths (reconciled implementation)
- `scripts/estate_evidence.py` and `scripts/publish_estate_evidence.py`
- `schemas/estate-evidence*.json`
- `tests/test_estate_evidence*.py` and `tests/evidence_schema_acceptance.py`
- `tooling/estate-evidence-requirements.txt`
- `.github/workflows/estate-conformance.yml`
- `docs/estate-evidence-standard.md`
- This Conductor track

The older structural scanner remains available for explicit private analysis;
registry and historical audit inputs are preserved, not rewritten as fresh data.

## Release gate
Every in-scope accessible repo is accounted for once; unavailable identities are counted separately. No undocumented scope mismatch; no inferred branch protection from forbidden API responses; reproducible snapshot schema and redacted public aggregate; stale/missing evidence cannot count as pass; tests prove all counterexamples.

## Acceptance checkpoint, 2026-11-14

- [x] Implement identity/scope reconciliation and versioned evidence schemas.
- [x] Qualify pagination, privacy, stale/unknown and negative-control behavior.
- [x] Implement aggregate outputs, checksum/provenance workflow and bounded issue updates.
- [x] Implement historical scope reconciliation without modifying original inputs.
- [x] Pass full hosted source suite and explicit schema/pipeline cases on Python 3.15.2.
- [x] Merge source PR #138 after the separate security alert gates passed.
- [ ] Supply an estate-readable credential to the main-branch workflow.
- [ ] Observe successful authenticated live inventory and inspect the actual aggregate receipt.
- [ ] Verify actual artifact attestation and bounded public issue publication.
- [ ] Record full acceptance and archive the track only after the preceding gates pass.

Evidence: [acceptance record](acceptance-20261114.md). The live attempt failed at
the credential boundary before scanning; synthetic tests cannot replace it.

## Blockers and recovery
API forbidden, unsupported entitlement, unstarted runners, stale branch, unmerged consumer PR and nondeterministic test are explicit unresolved states. Maintain retry bounds and no-false-green accounting. Do not claim estate deployment when only central code passes.
