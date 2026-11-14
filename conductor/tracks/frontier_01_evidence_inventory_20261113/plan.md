# Execution plan — Fresh inventory and evidence-grade conformance

## Incremental deliverables
1. Add coverage-denominator/scope reconciler and typed evidence schema: repository ID, classification, risk, source, observed_at, commit, run, result and explicit unknown status.
2. Test pagination, forks, renamed/empty repositories, inaccessible private repos, rate limits, deleted/archived entries, partial API responses and inconsistent snapshots.
3. Generate bounded redacted JSON/Markdown evidence, attach artifacts and attest audit run provenance; forbid false-green on missing evidence.
4. Compare registry and live estate with drift issue deduplication and freshness SLA; determine which dashboards should be private.
5. Backfill historical audit without overwriting original evidence.

## Implementation loop and review
For every numbered increment: define fixtures and negative controls, demonstrate failing tests, implement the minimum coherent change, run focused and full policy checks, perform independent automated security/behavioral review, fix findings, then verify hosted canary and exact-commit evidence. Update track status only after evidence; archive only after documented acceptance. Use scoped PRs, never force-push or bypass required checks.

## Owned paths (initial candidates; reconcile before edits)
- `scripts/audit_estate_conformance.py`
- `registry/repositories.json`
- `schemas/`
- `audits/latest/`

## Release gate
Every in-scope accessible repo is accounted for once; unavailable identities are counted separately. No undocumented scope mismatch; no inferred branch protection from forbidden API responses; reproducible snapshot schema and redacted public aggregate; stale/missing evidence cannot count as pass; tests prove all counterexamples.

## Blockers and recovery
API forbidden, unsupported entitlement, unstarted runners, stale branch, unmerged consumer PR and nondeterministic test are explicit unresolved states. Maintain retry bounds and no-false-green accounting. Do not claim estate deployment when only central code passes.
