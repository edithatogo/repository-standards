# Repository standards

[![OpenSSF Scorecard](https://api.securityscorecards.dev/projects/github.com/edithatogo/repository-standards/badge)](https://securityscorecards.dev/viewer/?uri=github.com/edithatogo/repository-standards)

Executable CI/CD, security, dependency-management, coverage, release, research-governance, and solo-maintainer standards for the `edithatogo` repository estate.

## Operating model

- [`registry/repositories.json`](registry/repositories.json) declares each active, non-fork, non-archived repository's archetype, risk profile, lifecycle status, exceptions, and sole-developer contract.
- [`profiles/archetype-profiles.json`](profiles/archetype-profiles.json) defines inherited controls for software, data, documentation, typesetting, research and infrastructure profiles.
- [`managed-files/manifest.json`](managed-files/manifest.json) separates centrally managed material from repository-owned context.
- [`scripts/audit_estate_conformance.py`](scripts/audit_estate_conformance.py) measures live conformance and reconciles the bounded status section of the central issue.
- [`schemas/verification-receipt.schema.json`](schemas/verification-receipt.schema.json) defines evidence from a one-command validation harness.

The posture is deliberately compatible with one maintainer: zero mandatory human approvals, no CODEOWNERS dependency, automated low-risk dependency updates only after stable checks, and protection against deletion and non-fast-forward changes where supported.

## Safe rollout

The scanner reports drift before managed-file synchronisation or ruleset activation. Lifecycle, licence, publication and canonicalisation decisions stay `review_required` until evidence supports them. See [`docs/continuous-conformance-standard.md`](docs/continuous-conformance-standard.md).
