# Execution plan — Agent harness, context and change safety

## Incremental deliverables
1. Evolve AGENTS.md into testable instruction hierarchy and context-pack format: architecture, risk, owned paths, permissions, out-of-scope actions, local validation, rollback and evidence links.
2. Build benign/malicious corpus for prompt injection, tool-output laundering, secret exfiltration attempts, fake CI statuses, forged policy exceptions and unsafe auto-merge instructions.
3. Require agent-generated changes to pass exact-commit tests and static/security checks; disclose unsupported or unexecuted checks. Independent automated reviewer compares behavior, privacy and policy to explicit specs.
4. Add bounded token/context and tool-call budgets, provenance receipts, semantic-diff review and task-level capability gates.
5. Evaluate on repeated seeded canary tasks and publish false-pass, missed-finding and change-rework metrics without exposing sensitive contents.

## Implementation loop and review
For every numbered increment: define fixtures and negative controls, demonstrate failing tests, implement the minimum coherent change, run focused and full policy checks, perform independent automated security/behavioral review, fix findings, then verify hosted canary and exact-commit evidence. Update track status only after evidence; archive only after documented acceptance. Use scoped PRs, never force-push or bypass required checks.

## Owned paths (initial candidates; reconcile before edits)
- `AGENTS.md`
- `conductor/workflow.md`
- `docs/solo-maintainer-standard.md`

## Release gate
Attacks do not cause prohibited actions; test suite catches forged receipts and instructions; no secret values in logs; artifact can be reproduced at a declared commit; no second human required by default.

## Blockers and recovery
API forbidden, unsupported entitlement, unstarted runners, stale branch, unmerged consumer PR and nondeterministic test are explicit unresolved states. Maintain retry bounds and no-false-green accounting. Do not claim estate deployment when only central code passes.
