# Grype rollout — 20 November 2026

## Scope and ownership

Own the new `grype-scan`, `cargo-lock-sbom` and `download-release-sbom` actions,
their focused scripts/tests, the released-SBOM reusable monitor and adoption
documentation. Preserve the existing supply-chain workflow and all offline
security branches. Consumer changes are separate scoped pull requests.

## Acceptance

- Resolved inventories retain dependency versions and truthful coverage limits.
- Critical findings block protected publication; PR findings are advisory.
- Operational errors, missing/empty inventory and stale databases fail.
- Container publication promotes the exact scanned candidate across every
  configured platform, with no rebuild after scan.
- Tool, database, source role, artifact digest and policy evidence is retained.
- Weekly released-asset scans resolve and hash-check immutable input bytes.

## Evidence and open gates

Local behavioral verification and real scanner canaries are recorded in the
pull request. Hosted checks must run on the final proposed head. Consumer
release execution, initial vulnerability baselines, private storage qualification
and existing scientific/publication holds are not inferred from central tests.
No release, deployment, branch-protection change or offline-security approval
is included. Keep this track open until actual consumer integration is observed.
