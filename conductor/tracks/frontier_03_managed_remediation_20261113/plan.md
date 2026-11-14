# Execution plan — Bounded GitHub App remediation control plane

## Incremental deliverables
1. Formalise an immutable plan schema: source tree SHA, destination head SHA, allowlisted paths, owners, materiality tier, expected diff, TTL and idempotency key.
2. Implement preflight conflict detection, diff/collision tests, dry run as default, rate limits, bounded batches and per-repo locks.
3. Exercise a disposable canary repository with happy path, stale base, protected branch, token denial, runner unavailable, dependency check failure, 429, repeat apply and safe rollback.
4. Create PRs only for additive low-risk managed changes; preserve local context and route semantic conflicts to issues.
5. Gate auto-merge on exact-head required checks, immutable pins and permissions; do not bypass native policies; record receipts and deterministic recovery.

## Implementation loop and review
For every numbered increment: define fixtures and negative controls, demonstrate failing tests, implement the minimum coherent change, run focused and full policy checks, perform independent automated security/behavioral review, fix findings, then verify hosted canary and exact-commit evidence. Update track status only after evidence; archive only after documented acceptance. Use scoped PRs, never force-push or bypass required checks.

## Owned paths (initial candidates; reconcile before edits)
- `.github/workflows/managed-remediation.yml`
- `scripts/plan_managed_remediation.py`
- `managed-files/manifest.json`

## Release gate
Apply mode initially fails closed; canary acceptance proves no direct-to-main writes, no loss of local changes, no duplicate PRs, no privilege escalation and safe idempotent retry. Live rollout proceeds only after passing independent checks.

## Blockers and recovery
API forbidden, unsupported entitlement, unstarted runners, stale branch, unmerged consumer PR and nondeterministic test are explicit unresolved states. Maintain retry bounds and no-false-green accounting. Do not claim estate deployment when only central code passes.
