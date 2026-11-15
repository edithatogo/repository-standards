# Paignia: reusable strategic-interaction library

Decision date: 2026-11-08. Status: chosen project identity, standalone repository created and seed transferred but unqualified; package publication and runtime acceptance remain pending. This document supplements the innovation-native policy and does not close any provider or consumer gate.

## Identity

**Paignia** is the chosen public name for the domain-neutral Rust game-theory library at [edithatogo/paignia](https://github.com/edithatogo/paignia). Its initial source transfer from `edithatogo/new-drug-reimbursement-game` is merged at [12b22ce](https://github.com/edithatogo/paignia/commit/12b22ce7571b9c590405bf53c2c1c5862b49cd64). Keep the policy capability ID `game-runtime` stable as a compatibility alias. No registry package publication or provider qualification is claimed. Check package namespace availability and any relevant naming/rights requirements before registry publication; creating the GitHub repository does not reserve package names.

| Seed or planned source | Package | Rule |
|---|---|---|
| `crates/paignia-core` (Paignia seed) | `paignia-core` | Typed game/player/action/payoff contracts; general information sets remain pending in T17.17; no scheduler. |
| `crates/paignia-solve` (Paignia seed) | `paignia-solve` | Qualify each supported algorithm independently; the existing seed is not a general equilibrium solver. |
| Planned execution adapter | `paignia-kairos` | Optional dependency on Kairos and Paignia; never required for static solving. |
| Semantic adapter | `paignia-uogto` | Versioned UOGTO mappings and conformance; preserve experimental semantic-profile boundaries. |
| Interchange adapter | `paignia-arrow` | Optional Arrow/Polars interchange; do not force dataframe dependencies into minimal solvers. |

The renamed core/solver seed has transferred from the reimbursement incubator to Paignia. Its historical source paths were `crates/uogto-game-core` and `crates/uogto-game-solve`. The [provider manifest at the merged revision](https://github.com/edithatogo/paignia/blob/12b22ce7571b9c590405bf53c2c1c5862b49cd64/extraction-manifest.json) records package/source provenance and `docs/architecture/paignia-transfer-map.md` records source dispositions. Qualify the selected immutable provider revision before acceptance; the reimbursement application consumes that revision rather than retaining a second authoritative implementation. The adapter packages remain planned. Historical commands, versions and receipts retain their tested names; source transfer does not establish publication, general solver support or numerical validity.

## Responsibility and dependency direction

- UOGTO owns vocabulary, identifiers, profiles and semantic conformance. It is not a numerical engine. Generic execution traces must not be relabelled as games or ontology-equivalent without an accepted semantic mapping.
- Kairos owns execution time, event order, resources, state, simulation RNG and replay. It does not acquire a mandatory dependency on Paignia, Innovate or Voiage.
- Paignia owns reusable strategic-interaction representation and algorithms. It does not own reimbursement policy, disease models, innovation trajectories, valuation, a second scheduler or general VOI.
- Innovate constructs and estimates innovation-specific games and dynamics, including diffusion, competition, substitution, hype effects and medicines repeat-use observations. It may consume Paignia and Kairos through qualified optional adapters.
- Voiage owns generic decision uncertainty, value of perspective/equity and VOI. It may consume valued joint outcomes from Innovate/Paignia/application models. A payoff or utilisation count is not automatically a decision utility.
- Applications retain institutions, payoff construction, evidence, clinical pathways and local calibration. Generic methods demonstrated by applications move to their existing authoritative provider after verification.

Runtime arrows are consumer -> provider. Paignia static core -> no simulator; `paignia-kairos` -> Paignia + Kairos; Innovate application adapter -> Paignia; Voiage optional input adapter -> versioned valued outcomes. Feedback to Innovate/Paignia is a versioned strategy or study-design artefact through application orchestration, not a reverse core import. UOGTO semantic alignment is not permission to load an unqualified ontology runtime in the static core.

## Existing work to reconcile, not duplicate

The provider authority is Paignia's `conductor/tracks/t17_game_runtime_ecosystem_20261107`, transferred with its existing T17.01-T17.17 IDs and reimbursement-game issue #100 history. Paignia owns T17.01-T17.08/T17.12-T17.17. T17.09 is the first actual application-consumer handoff, T17.10 the second distinct application/Innovate handoff, and T17.11 reimbursement-specific valuation; those implementations and completion receipts remain with their application owners. Preserve the two-real-consumer qualification and inherited Kairos S01-S04 obligations. The four inherited obligations include declared RK4 replicator dynamics, actual mixed-Nash methods, correlated-equilibrium incentive constraints/objective and general supported information-set CFR/CFR+. Unsupported or unverified methods remain explicitly unsupported and individually pending; they do not all gate a smaller supported core/static release.

Static package qualification follows T17.01-T17.03, two actual consumer receipts T17.09/T17.10, and T17.12. Reimbursement and Innovate can be the first pair; CareOps is another candidate, not a mandatory first consumer. Optional dynamic execution uses T17.08 and T17.14-T17.16 for lawful observations, RNG isolation and checkpoints. T17.13 qualifies semantic/identifier conversion where needed, including static UOGTO mappings. T17.17 supplies runtime-independent information sets for general imperfect-information methods such as CFR; it is a prerequisite for those claims, not for the minimal perfect-information static slice. Neither the reimbursement-specific valuation task nor all unimplemented algorithms are prerequisites for a scoped static claim.

Innovate PR #570 retains its 52 implementation packets. Kairos Tracks 108 and 109-115 retain provider/native/scientific responsibilities. Voiage's `simulation_outcome_boundary_20261107` and issue #1286 own decision-input integration and VOP promotion. New supplements must map to those owners rather than manufacture duplicate completion tracks.

## Proof-of-concept and application promotion

`vop_poc_nz` is a proof of concept, not a competing general library. Its reusable decision, perspective, equity and VOI capability belongs in Voiage after independent verification; NZ data, scenarios and interpretation stay in the POC. Do not copy every POC implementation blindly or move application-specific valuation into a generic solver.

`tobac`, `careops-sim`, the reimbursement game and other applications retain domain models. Classify reusable work by responsibility: adoption/competition/hype -> Innovate; execution -> Kairos; game algorithms -> Paignia; decision uncertainty/VOI -> Voiage; spline/surrogate functionality -> MARS when qualified. Preserve existing application baselines and migrate only after the provider and installed consumer pass. Source acquisition/terminology remains with the existing evidence/Atlas repositories.

## Native, dependencies and validation

Paignia's scientific execution is Rust-only with no Python subprocess fallback. Polars/Arrow is the ecosystem data boundary; pandas/xarray are not supported runtime dependencies of the new native capability. Host languages remain bindings/tooling. Independent Gambit/OpenSpiel/R/Python references may be used in isolated oracle environments, never silently loaded into production.

New dependency candidates follow the shared newest-candidate-first policy, but exact versions require security, build, numerical, installed-consumer and resource evidence. This decision changes no pin and invents no universal version baseline. Check direct and transitive resolved graphs, required root patches, licences and packaging. Actual native results and failures take precedence over manifest declarations.

Acceptance is scoped independently:

- **Core:** typed representation, identifiers, validation, packaging and compatibility are qualified without a solver or simulator prerequisite.
- **Static solver:** only named supported algorithms are qualified using invalid/unsupported inputs, independent analytic/reference games and applicable residual tolerances. Python and Kairos are absent from production dispatch. Two distinct real applications consume the same qualified artifacts for T17.12 acceptance; unfinished algorithms remain explicitly unsupported.
- **Dynamic adapter:** the optional Kairos adapter additionally proves one clock/state/RNG, lawful observations and native replay/checkpoint behavior. Its pending state does not block core/static acceptance or another application's native-runtime-only receipt.

Record exact source, dependency closure, commands, nonzero test counts and package hashes once for the applicable scope; add seeds, algorithm identity, residuals and equilibrium-selection assumptions where relevant. Reuse that evidence across the owning tracks rather than creating repeated approval or documentation gates.

Repository creation and seed transfer do not themselves publish or qualify packages. Preserve provenance/licences, compatibility, rollbacks, ABI/schema versions and scientific limitations through beta, release candidate and hardened release. This policy records the created repository; it claims no completed model, automatic consumer migration, external submission or public release.
