# Execution plan — Continuous assurance scorecard and frontier certification

## Incremental deliverables
1. Publish machine-readable metric dictionary and explain how unknown, inapplicable, blocked and failed results differ.
2. Use risk-weighted scorecards with hard blockers: stale inventory, missing required gate, unresolved executed secret finding, unsupported privacy claims and unverified publication evidence.
3. Implement longitudinal data retention, audit diff and signed evidence exports; provide redacted public and access-controlled private views.
4. Evaluate independent adversarial canaries and simulated drift, including an invalid exception, expired pin, failed scheduled check and false-green snapshot.
5. Review policy precision, cost and false-positive impacts quarterly; avoid gaming by using hard gates plus trend diagnostics rather than an arbitrary blended score.

## Implementation loop and review
For every numbered increment: define fixtures and negative controls, demonstrate failing tests, implement the minimum coherent change, run focused and full policy checks, perform independent automated security/behavioral review, fix findings, then verify hosted canary and exact-commit evidence. Update track status only after evidence; archive only after documented acceptance. Use scoped PRs, never force-push or bypass required checks.

## Owned paths (initial candidates; reconcile before edits)
- `audits/`
- `registry/assurance-controls.json`
- `docs/assurance-scorecards.md`

## Release gate
Frontier designation is evidence-backed and dated, never permanent; all P0 hard gates demonstrated on applicable canaries; no unknown recorded as pass; audit regression reliably revokes designation; clear exceptions/owners/expiry and low-cost ongoing operation.

## Blockers and recovery
API forbidden, unsupported entitlement, unstarted runners, stale branch, unmerged consumer PR and nondeterministic test are explicit unresolved states. Maintain retry bounds and no-false-green accounting. Do not claim estate deployment when only central code passes.
