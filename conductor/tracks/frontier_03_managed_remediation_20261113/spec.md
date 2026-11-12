# Specification — Bounded GitHub App remediation control plane

## Requirement and contract
Turn the existing plan-only managed remediation into a safe, auditable PR writer with single-writer ownership, short-lived least-privilege GitHub App tokens and explicit no-force semantics. Do not enable arbitrary writes or auto-merge until canary and rollback tests pass.

## Acceptance criteria
Apply mode initially fails closed; canary acceptance proves no direct-to-main writes, no loss of local changes, no duplicate PRs, no privilege escalation and safe idempotent retry. Live rollout proceeds only after passing independent checks.

## Boundaries and dependencies
- frontier_01_evidence_inventory_20261113
- frontier_02_enforcement_20261113

## Policy ownership
Central standards controls and evidence contracts only; consumer repositories retain their own product behavior, scientific correctness, and stronger controls. Write authority is separately gated. Never count scheduled/queued/unobserved checks as passed.
