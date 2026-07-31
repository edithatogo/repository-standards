# Continuous repository conformance

The estate registry is executable policy. Every active repository declares an
archetype profile, sole-maintainer posture, support/maintenance/release state,
canonicalisation status, and time-bounded exceptions.

## Safe rollout order

1. Measure live repository and hosted workflow state.
2. Stabilise harness commands and required check names.
3. Materialise repository-specific agent and community-health context.
4. Introduce managed-file pull requests or issues.
5. Apply archetype rulesets with zero human approvals.
6. Add risk-driven supply-chain and release controls.
7. Enable low-risk automated merging only after required checks are reliable.

Rulesets must block force-push and branch deletion, require stable automated
validation and conversation resolution, and retain an explicit owner recovery
path. They must not require a second reviewer, CODEOWNERS approval, team
membership, or another human approval.

## Policy-as-code

The scheduled conformance scanner measures:

- CI presence, explicit permissions, concurrency/cancellation, timeouts,
  immutable action pins, and successful scheduled-run evidence;
- branch protection/ruleset presence without treating configuration as proof of
  a passing gate;
- one-command harnesses, deterministic seed controls, generated-file drift,
  security checks, and verification receipts;
- repository-specific `AGENTS.md` and managed-file drift;
- CodeQL, dependency review, Scorecard, SBOM, provenance, checksums, and signed
  release evidence by risk profile;
- changelog, build/publish separation, rollback instructions, and immutable
  release artefacts;
- data schemas, rights, source manifests, privacy classification, deterministic
  regeneration, and publication receipts;
- lifecycle/canonicalisation status before archive, merge, rename, or deletion;
- flaky-test retries, quarantine expiry, benchmark baselines, regression
  budgets, and longitudinal coverage/mutation evidence.

The scanner updates a bounded central issue section. It does not mutate
repositories, rulesets, releases, or lifecycle state.

## Upgradeable scaffolding

Templates are bootstrap snapshots. Existing repositories receive later
standards through:

- immutable reusable workflow calls updated by Renovate;
- a canonical Renovate preset and custom managers for nonstandard tool
  versions;
- a managed-file manifest that detects missing/drifting context;
- pull requests for low-risk exact-source updates;
- issues for semantic conflicts, legal choices, repository-local extensions, or
  unsupported profiles.

Cross-repository writes require an explicitly authorised fine-grained token.
The default scanner is read-only.

## Harness and receipt

Executable profiles should expose one command that performs formatting, lint,
unit/integration tests, generated drift, security checks, and deterministic
seed capture. It writes a machine-readable receipt containing:

- repository and exact commit;
- runtime/toolchain versions;
- commands and exit status;
- seed and retry/quarantine state;
- coverage/mutation/benchmark evidence when warranted;
- generated-artifact hashes;
- known exceptions and evidence timestamps.

Retries are bounded and classified. Quarantines have an owner and expiry.
Benchmarks have comparable environments and explicit regression budgets.

## Release and publication

Build and publish are separate jobs/workflows. Publication requires an explicit
tag or manual gate, immutable artefacts, checksums, SBOM/provenance according to
risk, changelog/release notes, and rollback instructions. A successful build is
not evidence that a package, dataset, site, DOI deposit, or release was
published.

## Lifecycle

Similar names and empty repositories are triage signals only. The registry must
record canonical, historical, superseded, duplicate-candidate, and empty roles
with evidence before any archive or consolidation decision. Unique history,
releases, branches, provider integrations, rights, and publication records are
preserved until an explicit migration is verified.

