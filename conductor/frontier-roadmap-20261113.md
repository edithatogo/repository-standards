# Frontier control-plane programme — 13 November 2026

## Decision and scope
Objective: turn `edithatogo/repository-standards` from an advanced policy catalogue into a demonstrably enforced, evidence-backed, continuously improving control plane for a one-maintainer GitHub estate. The programme is **planned, not implemented**. This roadmap does not assert that branch protection can be administered via the current integration, that queued jobs passed, or that a generated SBOM implies verified provenance.

## Evidence baseline and limitations
- Historical committed audit (2026-07-31): 163 measured in its narrower scope, with 156 ruleset/protection gaps, 138 pinning gaps and 84 missing verification receipts; stale and not comparable directly to later totals.
- Privacy checkpoint (2026-11-10): 303 inventoried, 277 active, 26 archived; 41 installed default-branch workflows, 234 open installation PRs, 2 PR-creation blockers and 68 successful new privacy jobs. This is not proof of complete execution.
- Managed remediation is plan-only: its workflow intentionally refuses write mode.
- GitHub App administration/branch-protection reads may be forbidden; represent as unknown until checked through an authorised route.
- Existing scientific/native, privacy and bounded-execution tracks remain authoritative; do not overwrite or falsely close them.

## Delivery order and dependencies
| Phase | Track | Priority | Depends on | Exit evidence |
| --- | --- | --- | --- | --- |
| F01_evidence_inventory_20261113 | [Fresh inventory and evidence-grade conformance](tracks/frontier_01_evidence_inventory_20261113/index.md) | P0 | none | exact-commit receipt, canary evidence, reviewed findings |
| F02_enforcement_20261113 | [Risk-tiered enforcement and privacy rollout](tracks/frontier_02_enforcement_20261113/index.md) | P0 | frontier_01_evidence_inventory_20261113, privacy_secrets_rollout_20261110 | exact-commit receipt, canary evidence, reviewed findings |
| F03_managed_remediation_20261113 | [Bounded GitHub App remediation control plane](tracks/frontier_03_managed_remediation_20261113/index.md) | P0 | frontier_01_evidence_inventory_20261113, frontier_02_enforcement_20261113 | exact-commit receipt, canary evidence, reviewed findings |
| F04_verification_harness_20261113 | [Archetype-based verification and scientific reproducibility](tracks/frontier_04_verification_harness_20261113/index.md) | P1 | frontier_01_evidence_inventory_20261113, bounded_execution_merkle_lineage_20261110 | exact-commit receipt, canary evidence, reviewed findings |
| F05_release_supplychain_20261113 | [Reproducible release and supply-chain evidence](tracks/frontier_05_release_supplychain_20261113/index.md) | P1 | frontier_03_managed_remediation_20261113, frontier_04_verification_harness_20261113 | exact-commit receipt, canary evidence, reviewed findings |
| F06_agent_assurance_20261113 | [Agent harness, context and change safety](tracks/frontier_06_agent_assurance_20261113/index.md) | P1 | frontier_03_managed_remediation_20261113, frontier_04_verification_harness_20261113 | exact-commit receipt, canary evidence, reviewed findings |
| F07_observability_certification_20261113 | [Continuous assurance scorecard and frontier certification](tracks/frontier_07_observability_certification_20261113/index.md) | P1 | frontier_01_evidence_inventory_20261113, frontier_02_enforcement_20261113, frontier_03_managed_remediation_20261113, frontier_04_verification_harness_20261113, frontier_05_release_supplychain_20261113, frontier_06_agent_assurance_20261113 | exact-commit receipt, canary evidence, reviewed findings |

Parallelism: initiate F01 and existing privacy rollout immediately; advance F02 once scope is verified. F03 can be developed behind fail-closed switches, but never enabled before ruleset canaries. F04 can prototype alongside F02/F03. F05/F06 follow their prerequisites; F07 is the independent assurance sign-off. Roll out with small per-archetype canary cohorts before broad installation.

## MoSCoW
**Must**: inventory/freshness; explicit unknown; non-bypassable CI; no human-review requirement; privacy and secrets execution; bounded PR remediation; immutable action pins; evidence to exact commit; verified rollback and adverse canaries; privacy-safe public aggregates.
**Should**: profile-specific property/metamorphic tests, mutation/fuzzing budgets, SLSA-style verifier, risk-weighted assurance metrics, AI-agent injection evaluation, evidence time series.
**Could**: OPA policy bundles, reproducible-build comparisons, CHAOSS metrics, independent external assessment.
**Won't (this programme)**: force-push or mass rewrite; auto-archive; silently weaken protections; auto-publish scientific outputs; paywalled tools as mandatory standards; unnecessary multi-person approval for a solo maintainer.

## Non-negotiable contracts
1. **Evidence truthfulness**: configured != run != passed != enforced; unknown/blocked != pass. Every statement carries scope, source SHA, observed time and run/result where available.
2. **Change safety**: canary -> typed impact/diff -> PR -> exact-head required checks -> low-risk automerge; idempotent, revertible, least privilege, no direct branch writes.
3. **Test assurance**: failing fixture first, positive and negative controls, property tests as relevant, security/policy review, repeatable exact-commit verification.
4. **Scientific correctness**: numeric and empirical validity remain consumer-owned; central gates test reproducibility/invariants but cannot establish domain truth.
5. **Privacy/security**: redact private identities and matches in public evidence; preserve existing repository protections; hold on executed scanner failures.
6. **Single-maintainer efficiency**: prefer existing tools and language-native ecosystems; specify CI cost/runtime ceilings and exception expiry; zero mandatory second-person approval.

## Definition of frontier / no-go criteria
Required: (a) dated near-complete classified inventory with exceptions rather than missing identities, (b) executable enforceable policy on each supported canary and justified live rollout, (c) successful required exact-commit CI plus negative tests, (d) safe auto-remediation demonstrated, (e) risk-appropriate verified release/provenance where applicable, (f) continuous false-green detection and expiry-driven reassessment. Any hard-blocker or stale critical evidence changes status to **not verified**. Certification does not require every archived or unsupported repository to run identical tools.

## Review loop
Use Conductor implementation and review: spec -> tests that initially fail -> implementation -> focused tests -> full policy suite -> adversarial/agent security review -> hosted canaries -> reconcile code and track metadata -> archive only after evidence. Report exact failed/queued/skipped and blocked steps; do not claim an unexecuted run passed.
