# Automation and innovation standard

## Authentication

Estate-wide writes use short-lived GitHub App installation tokens. The App is
installed only on in-scope repositories, has metadata and contents read access,
contents and pull-request write access only where managed remediation is
enabled, and issues write access only in `repository-standards`. Long-lived
personal access tokens are a migration fallback, not the target design.

## Two-phase remediation

1. Audit live hosted evidence and produce a signed, machine-readable snapshot.
2. Simulate the proposed policy change against that snapshot.
3. Generate a bounded plan containing only low-risk managed files.
4. Open one managed pull request per repository without overwriting local
   extensions.
5. Merge automatically only after stable required checks pass; human approvals
   remain zero.
6. Record the policy version, before/after hashes, workflow run and pull request
   in an append-only reconciliation receipt.

Lifecycle, licence, visibility, publication, ruleset activation, release and
canonicalisation changes are never in the low-risk class.

## Control-plane quality

- resolve immutable action SHAs against their source repositories;
- property-test schemas and policy invariants;
- mutation-test control evaluation and exception handling;
- replay recorded API fixtures and inject rate limits, timeouts, partial trees,
  missing permissions and stale schedules;
- use golden tests for bounded issue sections and remediation plans;
- require exception owners, evidence and expiry, with warnings at 30 days;
- sign registry snapshots and emit append-only verification receipts.

## Software and data supply chain

Published profiles produce both SPDX and CycloneDX SBOMs, GitHub artifact
attestations, SLSA provenance, checksums and reproducibility evidence. Build and
publish remain separate. Data and research releases also bind source manifests,
rights, privacy classification, schemas, deterministic regeneration and DOI or
publication receipts.

## Quality signals

Coverage gates use patch coverage plus component flags. Mutation score,
property-test examples, flaky-test quarantine age, deterministic seeds,
benchmark budgets and contract-test compatibility are tracked longitudinally.
Headline percentages alone are insufficient.

## Workflow service levels

Track scheduled-run freshness, queue latency, success rate, dependency-update
latency, mean repair time, cache hit rate, artifact retention and attestation
availability. Alerts link to the exact run and owning nested issue.

## Further innovations

- differential policy evaluation reports newly introduced failures before merge;
- OPA/Rego export permits independent policy evaluation;
- OpenTelemetry spans correlate scanner API calls, retries and issue updates;
- GitHub 403/429 secondary throttling is retried with bounded backoff and telemetry;
- a dependency graph limits propagation blast radius and orders reusable-workflow upgrades;
- canary repositories exercise each archetype before estate rollout;
- automatically generated scorecards show evidence freshness, not only presence;
- deterministic simulation exercises API pagination, eventual consistency and permission loss;
- cryptographic transparency receipts make conformance history tamper-evident.
