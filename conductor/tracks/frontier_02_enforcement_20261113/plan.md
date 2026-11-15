# Execution plan — Risk-tiered enforcement and privacy rollout

## Incremental deliverables
1. Define fail-closed enforcement contract per risk/archetype: required checks, ruleset semantics, approval_count=0, signed/tag protection where applicable, scoped recovery and immutable evidence.
2. On representative canaries, test safe/unsafe PR merge outcomes, missing checks, fail/skipped/queued/not-started jobs, stale SHA, bypass attempts and deletion/force-push protection.
3. Reconcile consumer privacy PRs and blocked installations via existing rollout track, without treating PR creation as installed or scan configured as executed.
4. Record admins-only gaps as manual external blockers rather than fabricated successful updates; maintain action-level audit of exceptions and rollback.
5. Pilot change simulation and conflict-free ruleset activation by risk tiers; then expand in bounded batches.

## Implementation loop and review
For every numbered increment: define fixtures and negative controls, demonstrate failing tests, implement the minimum coherent change, run focused and full policy checks, perform independent automated security/behavioral review, fix findings, then verify hosted canary and exact-commit evidence. Update track status only after evidence; archive only after documented acceptance. Use scoped PRs, never force-push or bypass required checks.

## Owned paths (initial candidates; reconcile before edits)
- `profiles/`
- `registry/assurance-controls.json`
- `.github/workflows/privacy-secrets.yml`

## Release gate
Canary ruleset tests show both deny and allow behavior; required gates cannot be bypassed by skipped/cancelled jobs; no human reviewer required; every eligible repository either has verified enforcement or a dated, owned exception/blocker.

## Blockers and recovery
API forbidden, unsupported entitlement, unstarted runners, stale branch, unmerged consumer PR and nondeterministic test are explicit unresolved states. Maintain retry bounds and no-false-green accounting. Do not claim estate deployment when only central code passes.
