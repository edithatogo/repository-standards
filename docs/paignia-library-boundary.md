# Paignia: reusable strategic-interaction library

Decision date: 2026-11-08. Status: working project identity and implementation direction; extraction, package publication and runtime acceptance remain pending. This document supplements the innovation-native policy and does not close any provider or consumer gate.

## Identity

Use **Paignia** as the working public name for the domain-neutral Rust game-theory capability currently incubated in `edithatogo/new-drug-reimbursement-game`. Keep the policy capability ID `game-runtime` as a compatibility alias. The intended repository slug is `paignia`; it is a target, not a repository claimed to exist. Package namespaces and any relevant naming/rights checks must be completed before publication; no namespace is reserved by this decision.

| Current implementation | Intended extracted package | Rule |
|---|---|---|
| `crates/uogto-game-core` | `paignia-core` | Typed game/strategy/information/payoff/result contracts; no scheduler. |
| `crates/uogto-game-solve` | `paignia-solve` | Qualified equilibrium, learning and strategic algorithms with explicit supported scope. |
| Planned execution adapter | `paignia-kairos` | Optional dependency on Kairos and Paignia; never required for static solving. |
| Semantic adapter | `paignia-uogto` | Versioned UOGTO mappings and conformance; preserve experimental semantic-profile boundaries. |
| Interchange adapter | `paignia-arrow` | Optional Arrow/Polars interchange; do not force dataframe dependencies into minimal solvers. |

These are planned names. Existing Cargo package IDs, commands, locks, published versions and historical receipts retain their names until a separately tested migration. Do not replace strings globally or claim a rename is extraction.

## Responsibility and dependency direction

- UOGTO owns vocabulary, identifiers, profiles and semantic conformance. It is not a numerical engine. Generic execution traces must not be relabelled as games or ontology-equivalent without an accepted semantic mapping.
- Kairos owns execution time, event order, resources, state, simulation RNG and replay. It does not acquire a mandatory dependency on Paignia, Innovate or Voiage.
- Paignia owns reusable strategic-interaction representation and algorithms. It does not own reimbursement policy, disease models, innovation trajectories, valuation, a second scheduler or general VOI.
- Innovate constructs and estimates innovation-specific games and dynamics, including diffusion, competition, substitution, hype effects and medicines repeat-use observations. It may consume Paignia and Kairos through qualified optional adapters.
- Voiage owns generic decision uncertainty, value of perspective/equity and VOI. It may consume valued joint outcomes from Innovate/Paignia/application models. A payoff or utilisation count is not automatically a decision utility.
- Applications retain institutions, payoff construction, evidence, clinical pathways and local calibration. Generic methods demonstrated by applications move to their existing authoritative provider after verification.

Runtime arrows are consumer -> provider. Paignia static core -> no simulator; `paignia-kairos` -> Paignia + Kairos; Innovate application adapter -> Paignia; Voiage optional input adapter -> versioned valued outcomes. Feedback to Innovate/Paignia is a versioned strategy or study-design artefact through application orchestration, not a reverse core import. UOGTO semantic alignment is not permission to load an unqualified ontology runtime in the static core.

## Existing work to reconcile, not duplicate

The extraction owner is reimbursement-game Track T17, with existing issue #100. Preserve its T17.01-T17.12 leaves, the two-real-consumer requirement and inherited Kairos S01-S04 obligations. The four inherited obligations include declared RK4 replicator dynamics, actual mixed-Nash methods, correlated-equilibrium incentive constraints/objective and general supported information-set CFR/CFR+. Unsupported or unverified methods remain explicitly unsupported.

Innovate PR #570 retains its 52 implementation packets. Kairos Tracks 108 and 109-115 retain provider/native/scientific responsibilities. Voiage's `simulation_outcome_boundary_20261107` and issue #1286 own decision-input integration and VOP promotion. New supplements must map to those owners rather than manufacture duplicate completion tracks.

## Proof-of-concept and application promotion

`vop_poc_nz` is a proof of concept, not a competing general library. Its reusable decision, perspective, equity and VOI capability belongs in Voiage after independent verification; NZ data, scenarios and interpretation stay in the POC. Do not copy every POC implementation blindly or move application-specific valuation into a generic solver.

`tobac`, `careops-sim`, the reimbursement game and other applications retain domain models. Classify reusable work by responsibility: adoption/competition/hype -> Innovate; execution -> Kairos; game algorithms -> Paignia; decision uncertainty/VOI -> Voiage; spline/surrogate functionality -> MARS when qualified. Preserve existing application baselines and migrate only after the provider and installed consumer pass. Source acquisition/terminology remains with the existing evidence/Atlas repositories.

## Native, dependencies and validation

Paignia's scientific execution is Rust-only with no Python subprocess fallback. Polars/Arrow is the ecosystem data boundary; pandas/xarray are not supported runtime dependencies of the new native capability. Host languages remain bindings/tooling. Independent Gambit/OpenSpiel/R/Python references may be used in isolated oracle environments, never silently loaded into production.

New dependency candidates follow the shared newest-candidate-first policy, but exact versions require security, build, numerical, installed-consumer and resource evidence. This decision changes no pin and invents no universal version baseline. Check direct and transitive resolved graphs, required root patches, licences and packaging. Actual native results and failures take precedence over manifest declarations.

First acceptance: static core/solver runs with Python and Kairos absent; invalid inputs/unsupported games fail; independent analytic and reference-game tests pass with declared residual tolerances; two distinct real applications consume the same package artefacts; optional Kairos integration proves a single clock/state/RNG and native replay. Record exact source, dependency closure, seeds, commands, nonzero test counts, package hashes, algorithm identity and equilibrium-selection assumptions.

Repository extraction eligibility does not itself publish packages. Preserve provenance/licences, compatibility, rollbacks, ABI/schema versions and scientific limitations through beta, release candidate and hardened release. No new repository, model implementation, automatic consumer migration, external submission or public release is claimed here.
