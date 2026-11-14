# F01 implementation checkpoint — 2026-11-14

Status: **in progress**. The first source increment is merged; the complete
inventory and evidence-grade acceptance contract remains open.

## Merged source increment

[PR #128](https://github.com/edithatogo/repository-standards/pull/128) merged as
`74f2babba6b6baad94afa2537c5b37a49fb73437`. Its verified source head is
`6d74abe2ae7a8c0959b1513bdbdd47430031d0ff`.
The Estate conformance, Policy gate, GitHub Actions security lint and Privacy and
secrets PR workflows were observed successful (run IDs are in metadata.json).
The Estate conformance PR lane validates source policy; it is not a new live
estate inventory. This replaces the stale statement that implementation was
merely proposed and awaiting merge.

The source increment distinguishes inaccessible protection evidence from observed
absence, reports configuration separately from proven enforcement, and avoids
retries on the explicitly fail-fast protection-read path. #78 and #84 subsequently
added expiry/active-exception regressions while preserving these protection tests.

## Behavioral acceptance retained

- A 403 read from either protection API is unknown, not demonstrated absence.
- Observed positive configuration can establish present even if the other read is denied.
- Only conclusive negative reads can establish observed absence.
- Present configuration does not prove merge-gate enforcement.
- Unknown and observed-absent counts remain separate from missing-control violations.

## Verification boundary

The [batch reconciliation](../../merge-reconciliation-20261114.md) records merged
heads, source checks, policy-test skips and explicitly held PRs. Track-level
hosted_canary_verified, estate_rollout_verified and frontier_certified remain false.
No repository protection, permissions, consumer workflow rollout or private
registry publication is implied by this source implementation.

## Remaining F01 work

Reconcile the accessible estate against the historical registry with stable
identity and scope-aware pagination; schema-validate evidence with freshness,
exact-commit/run provenance and incomplete-response handling; separate private
evidence from public aggregates; generate a dated inventory and validate scheduled
execution history. The GraphQL partial-response review on #129 is an explicit
follow-up, not completed by this checkpoint. Complete and archive only when every
F01 specification acceptance gate is observed satisfied.
