# Execution plan — Reproducible release and supply-chain evidence

## Incremental deliverables
1. Define publication contract: source SHA, immutable toolchain, SPDX/CycloneDX SBOM, dependency audit, SLSA-style provenance, artifact digest, verification status and rollback instructions.
2. Test artifact substitution, wrong source URI, mismatched builder ID, unsigned/tampered provenance and expired/revoked signing trust as applicable.
3. Canary release dry-runs, compare reproducible builds where feasible and record known nondeterminism; use artifact attestations rather than misleading guarantees.
4. Ensure releases/DOI/data publication require explicit authorisation and avoid automated publication from untrusted PRs.
5. Monitor pinned action updates, dependency freshness and verified artifact consumption.

## Implementation loop and review
For every numbered increment: define fixtures and negative controls, demonstrate failing tests, implement the minimum coherent change, run focused and full policy checks, perform independent automated security/behavioral review, fix findings, then verify hosted canary and exact-commit evidence. Update track status only after evidence; archive only after documented acceptance. Use scoped PRs, never force-push or bypass required checks.

## Owned paths (initial candidates; reconcile before edits)
- `.github/workflows/supply-chain-evidence.yml`
- `managed-files/templates/slsa-verification.yml`
- `docs/assurance-scorecards.md`

## Release gate
Canary verifier rejects mismatched provenance/artifacts; publication stays separate from validation; evidence bound to exact source and output digest; no unsupported SLSA-level claims.

## Blockers and recovery
API forbidden, unsupported entitlement, unstarted runners, stale branch, unmerged consumer PR and nondeterministic test are explicit unresolved states. Maintain retry bounds and no-false-green accounting. Do not claim estate deployment when only central code passes.
