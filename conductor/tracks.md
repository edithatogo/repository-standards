# Tracks

## Frontier control-plane programme (13 November 2026)

[Programme roadmap](frontier-roadmap-20261113.md). F01 is in progress; the other
programme tracks remain planned. Merged source changes are not completed estate
deployments. See the [2026-11-14 reconciliation](merge-reconciliation-20261114.md)
for exact-head evidence, superseded PRs and open gates.

- [~] **P0 Fresh inventory and evidence-grade conformance** — [Track](tracks/frontier_01_evidence_inventory_20261113/index.md).
- [ ] **P0 Risk-tiered enforcement and privacy rollout** — [Track](tracks/frontier_02_enforcement_20261113/index.md); depends on `frontier_01_evidence_inventory_20261113`, `privacy_secrets_rollout_20261110`.
- [ ] **P0 Bounded GitHub App remediation control plane** — [Track](tracks/frontier_03_managed_remediation_20261113/index.md); depends on `frontier_01_evidence_inventory_20261113`, `frontier_02_enforcement_20261113`.
- [ ] **P1 Archetype-based verification and scientific reproducibility** — [Track](tracks/frontier_04_verification_harness_20261113/index.md); depends on `frontier_01_evidence_inventory_20261113`, `bounded_execution_merkle_lineage_20261110`.
- [ ] **P1 Reproducible release and supply-chain evidence** — [Track](tracks/frontier_05_release_supplychain_20261113/index.md); depends on `frontier_03_managed_remediation_20261113`, `frontier_04_verification_harness_20261113`.
- [ ] **P1 Agent harness, context and change safety** — [Track](tracks/frontier_06_agent_assurance_20261113/index.md); depends on `frontier_03_managed_remediation_20261113`, `frontier_04_verification_harness_20261113`.
- [ ] **P1 Continuous assurance scorecard and frontier certification** — [Track](tracks/frontier_07_observability_certification_20261113/index.md); depends on `frontier_01_evidence_inventory_20261113`, `frontier_02_enforcement_20261113`, `frontier_03_managed_remediation_20261113`, `frontier_04_verification_harness_20261113`, `frontier_05_release_supplychain_20261113`, `frontier_06_agent_assurance_20261113`.

## Existing tracks (retained)

- [~] **Scientific ecosystem alignment: ownership, dependencies and build qualification**
  [Track](tracks/scientific_ecosystem_alignment_20261029/index.md)

- [~] **Innovation/native ownership, Polars and application capability promotion**
  [Track](tracks/innovation_native_boundaries_20261107/index.md)
  Central policy/tests recorded; consumer runtime migrations and acceptance remain open.

- [ ] **Bounded process-group execution, two-tier Merkle lineage and metamorphic property gates**
  [Track](tracks/bounded_execution_merkle_lineage_20261110/index.md)
  Estate-wide standard for PGID-scoped macOS RSS guards, non-circular two-tier Merkle provenance manifests and deterministic metamorphic property suites (`tobac` F00/H2 co-design).

- [~] **Privacy and secret scanning across owned repositories**
  [Track](tracks/privacy_secrets_rollout_20261110/index.md)
  Shared pinned Presidio/Gitleaks tooling; inventory complete, implementation in
  progress, consumer deployment and execution pending. Public evidence is aggregate-only.
