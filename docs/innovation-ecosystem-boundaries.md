# Innovation/native ecosystem boundaries — 7 November 2026

The maintainer requires Innovate to remain a general library for modelling/predicting innovation: policy diffusion, adoption, competition, substitution, complements, hype effects and strategic innovation. Medicines utilisation is a flagship application, not a scope restriction. Hype concerns expectations/attention and their effects, not a mandatory test of exaggerated claims.

## One owner for each reusable capability

| Capability | Owner | What must not be duplicated |
|---|---|---|
| Innovation dynamics, observation models, fit/predict and innovation-specific games | Innovate | No second simulator, general game solver, VOI library or medicines data lake. |
| Native simulation clock/state/events/resources/RNG/replay | Kairos | No host-language preview engine or per-application scheduler. |
| Generic game representation and algorithms | Paignia (`game-runtime` policy key) | Transfer the renamed `paignia-core`/`paignia-solve` seed to its created repository; reconcile Kairos solver overlap while preserving per-method qualification. Static solving does not require a simulator. |
| Game semantics/conformance | UOGTO | Ontology is not an algorithm implementation. |
| VOI, generic decision/perspective/equity and reusable VOP capability | Voiage | `vop_poc_nz` is a proof of concept, not a competing framework. |
| Generic spline surrogate | MARS | Promote only with measured accuracy/cost and decision-preservation evidence. |
| Source acquisition, medicine identity/funding/regulatory evidence | Global Medicines Atlas and Reimbursement Atlas | Consumers use qualified, revision-pinned projections and retain source meanings. |
| Clinical, tobacco, NZ and reimbursement scenarios | Domain applications | Keep institutional assumptions, empirical parameters and application validation here. |

The stable `game-runtime` profile records [Paignia's chosen identity and merged source transfer](paignia-library-boundary.md), with the former reimbursement incubator retained as provenance. The seed is transferred; packages remain unpublished and unqualified. T17.01–T17.17 retains its IDs: Paignia owns provider implementation while application-consumer and valuation handoffs stay with their respective owners. Static qualification requires two real consumers, independent tests for the claimed algorithms, immutable delivery and dispositions for Kairos's S01–S04 obligations. Core, supported static solvers and the optional dynamic adapter qualify independently; unfinished methods and dynamic execution do not block a smaller supported scope. Keeping old API adapters is allowed; keeping two authoritative implementations is not the target.

## Directed integration

Innovate consumes Kairos through an optional native adapter. Voiage may consume Innovate joint forecasts through an optional adapter with explicit strategy/utility/economic mapping. Neither core imports the other both ways. Voiage-selected designs/policies can return as versioned artefacts through application orchestration. This is feedback in the scientific workflow, not a package dependency cycle.

Preserve joint draw identity/dependence, units, time basis, population/denominator, perspective, discount basis, scenario/strategy/product/region IDs, fit status and source provenance. Transaction counts are not patient counts or utilities. Unsupported mappings fail explicitly.

## Native/Polars support contract

Innovate's new supported release uses Rust scientific execution and Polars/Arrow. Pandas/xarray inputs, conversions, runtime imports and transitive supported extras are retired; historical releases do not become a continuing alternate engine. Isolated independent oracle environments may use established packages, but production dispatch cannot reach them. Host languages configure, marshal and present native results.

Kairos already declares native-only execution. Minimal simulation/numerical crates need not depend on Polars unless data operations require it. Voiage's current hybrid scope remains explicit; this policy does not falsely certify every interface as native.

The central `runtime_accepted: false` means this policy does not grant blanket runtime acceptance; it does not revoke separately verified per-capability receipts.

## Dependency standards

The default scientific interface/tooling candidate is Python 3.15.2; Rust 1.99.1 is the dated native starting candidate. Inspect newer releases/prereleases and exact development commits at each qualification cut. Pin only after security, build, numerical, installed-consumer and resource checks. No rolling main or silent replay/schema changes.

Kairos's current Polars closure is Git revision `96439685eb2f95108f51087d2b76091917f2593c` with the `pola-rs/hashbrown` root patch `d76a6f81abd8f388676aff15068236a8d21c7e1a`. Its manifest marks the crate non-publishable on crates.io until a separately qualified route exists. This is an observed integration constraint, not proof that every consumer has passed. Native Arrow/PyArrow/Polars have independent version lines; qualify exchange and lifetime semantics, not matching major numbers.

Keep core, optional adapter, binding, build, test-oracle and developer dependencies separate. Prefer maintained building blocks when they reduce custom implementation and pass independent references. Domain frameworks such as Gambit/OpenSpiel/PyBLP/DIMORA are valuable isolated comparators; they are not automatically added to the production graph.

## Application promotion

For each useful application method, record source/provenance, intended generic semantics, independent oracle, destination library, public API, accepted provider revision and consumer migration. Verify before copying. Promote decision/perspective/VOI methods from VOP into Voiage; adoption into Innovate; simulation into Kairos. `tobac` and other applications follow the same rule. A method's folder name alone is not sufficient evidence of ownership—for example, screening recall/work-saved metrics are not automatically VOI.

## Execution and release

Innovate PR 570 contains the granular 52-packet programme. Each task has named paths, target interfaces, failing assertions, commands, dependencies and receipts. The shared controls here remain additive: no automatic estate-wide migration, ruleset change, mandatory second human reviewer or publication.

The new policy tests verify central policy contents only. Consumer conformance still requires actual source/dependency scans, Python-absent native execution, clean supported installations, independent numerical/uncertainty validation, FFI safety and exact-artifact release checks.
