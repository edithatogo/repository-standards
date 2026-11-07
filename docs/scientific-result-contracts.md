# Scientific result contracts and independent release units

Policy date: 2026-11-08. These requirements amend existing work, not runtime acceptance. The machine-readable policy is `profiles/scientific-native.json`; `tests/test_innovation_scope_policy.py` checks policy assertions only. Providers retain their existing public types and versioned migrations; this document does not create a universal runtime schema.

## Ownership and release

Paignia's actual home is https://github.com/edithatogo/paignia. Preserve the `game-runtime` capability ID and T17 leaf IDs. Incubator provenance remains `new-drug-reimbursement-game`; source transfer and installed consumers still need evidence. Static Paignia does not require Kairos or UOGTO tooling. Innovate's deterministic core does not require Kairos, Paignia or Voiage. Optional adapters own those relationships; no reverse core imports.

Qualify native-core, data-bindings and optional-integrations separately. Every advertised capability keeps all applicable scientific, native, security and consumer requirements. An unfinished optional feature remains unavailable or experimental and its obligation stays open; it does not block an unrelated core release. Static strategic examples do not require dynamic replay. General hype evaluation does not require a medicines cohort. A core Innovate release does not require Voiage integration. Native performance tests and dynamic-integration performance tests have separate prerequisites and receipts.

## Game result and observation contracts

A result records game class, information structure, solution concept, algorithm/version, status, numerical tolerance, residuals/exploitability, selection rule and completeness claim. `one_solution`, `enumerated_within_declared_scope` and `approximate` must not be conflated. Do not report all equilibria because one was found. Correlated distributions, Nash solutions, noisy-choice models and learned policies keep distinct semantics.

An offline solver can inspect the mathematical game. A live policy receives only its lawful observation, legal actions and identity/revision. Two hidden states with identical lawful observations must produce equal policy inputs and, conditional on equal policy randomness, equal actions. Do not expose world-state references, opponent-private fields, future events or leaked action masks. For supported stochastic behavioural models, preserve independent solver/policy randomness without importing Kairos into static solving. State unsupported information structures explicitly.

## Information-value estimands

Distinguish conventional EVPI/EVSI, net benefit of research, strategic information value and social information value. Conventional non-negativity relies on the stated decision assumptions, including the ability to ignore costless information. Strategic information changes who knows what and can change opponents' behaviour and equilibrium; signed values must not be zero-clipped or relabelled conventional EVPI.

Record recipient, timing, public/private disclosure, feasible commitments, observation model, solution concept, equilibrium selection and perspective/welfare aggregation. Reuse Voiage's signed-information contract and preserve/version legacy semantics. A valuation mapping is mandatory: scripts, adoption counts and arbitrary strategic payoffs are not automatically decision utilities.

## Nested uncertainty and simulation noise

Keep parameter, structural, simulation, measurement, strategic and numerical uncertainty distinguishable. Joint records identify parameter draw, model, equilibrium/selection, simulation replicate, strategy, scenario and measurement/valuation versions. These labels preserve meaning; they do not assert independence. Propagate shared latent draws and measurement error coherently.

For a decision about uncertain parameters, first estimate conditional expected net benefit over the simulation randomness appropriate to the estimand, then perform decision maximisation. Passing each noisy simulation as a distinct parameter draw changes the information question and can bias nested estimates. Report Monte Carlo standard errors/bias diagnostics and the inner/outer budgets. Common random numbers are an explicit coupling policy, not a shared seed assumption. If process outcomes are themselves learnable before action, define that different information problem explicitly.

Required finite regression: with one parameter state, two equally weighted simulation replicates A=[-1,1], B=[1,-1], both conditional means are zero and conventional parameter EVPI is zero. Naively treating replicate rows as parameter states yields 1 and must fail. Also test unequal-mean/heteroscedastic cases, strategy permutations and increasing numerical effort. Approximate finite-sample noise is reported with numerical uncertainty rather than concealed by clipping.

## Scientific validity dimensions and adversarial tests

Record execution validity, convergence, identification, predictive evidence and causal assumptions separately. A weakly identified parameter does not automatically invalidate all predictive output; a numerically valid fit does not establish causality. Failed execution cannot expose posterior-labelled samples.

Simulation-based calibration must include a deliberately prior-only algorithm that ignores observations, data-dependent quantities such as joint/pointwise log likelihood, omitted data and shuffled-group controls. Parameter ranks alone are insufficient as the sole safeguard. Use a conjugate reference and predeclared Monte Carlo error/false-alarm limits; no finite non-rejection is universal calibration proof.

Add justified invariants: product-label permutation; consistent time/rate transformations; declared positive affine utility changes; partition/recombination where the estimator permits it; and numerical-effort/error checks. State tolerances and assumptions before inspection. Do not demand invariance for operations that change the scientific problem.

## Hype and utilisation measurement

In joint hype/adoption models, the transformation h*=c*h and beta*=beta/c leaves beta*h unchanged when the hype scale is unconstrained. Anchor scale/sign/location through an explicit reference indicator or constraint; record it. Bayesian priors regularise but do not create data identification. Multiple indicators use a declared measurement model; weak component identification and model-family uncertainty survive export. Hype means impact of expectations/attention, not a mandatory judgement about exaggerated claims.

Medicines and other repeat-use data require a separate observation process. Synthetic acceptance includes unchanged treated stock under a doubled supply interval, code/coverage/reporting changes, changing eligible market M(t), and demand-versus-access ambiguity. Represent payer, prescriber, patient and dispensing decisions where relevant; aggregate records need not identify them. Preserve effective time and known-at time with as-of joins. Do not infer patient counts, causality or utility from transaction totals.

## Data/dependency boundaries

Accept lazy Polars plans with explicit materialisation/resource boundaries and compare them with eager/partitioned execution. Arrow/Parquet is interchange, not a requirement for dataframe objects in every numerical kernel. Stable domain/FFI contracts avoid leaking changing third-party Rust types; adapters may expose documented Polars versions.

Inspect resolved normal/build dependencies and enabled features in standalone consumers, not only provider manifests or workspace-wide all-features builds. Test minimal/static/default/declared-extra profiles and a seeded transitive violation. Newest candidate qualification and reproducible release locks are separate lanes. No policy check alone qualifies a dependency, package release or native implementation.

## Existing task ownership

Innovate: I04, R02-R04/R08-R10, A05/A06, H02-H06, M03-M05, G02-G04, E02/E03, V01-V04 and Q05. Paignia: T17.01/.02/.03/.05-.07/.08/.12/.14/.15/.17. Kairos: Track 114 K01/KP consumer checks and existing observation/RNG contracts. Voiage: simulation-outcome boundary VP01/VP02/VP04, reconciled with signed-social information work. Do not add duplicate completion ledgers.

Research priorities are model-discriminating measurements and information acquisition/disclosure that changes strategic response. They remain experiments against established alternatives, not frontier-superiority claims.
