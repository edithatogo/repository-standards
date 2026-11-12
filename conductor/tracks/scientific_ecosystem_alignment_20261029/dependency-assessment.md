# Dependency roles and first-wave decisions

The source inventory captures manifest declarations, locks and hashes at explicit
revisions. Cargo edges carry runtime/build/test roles; Python declarations retain
runtime/optional/development/build grouping. This is not a resolved feature graph.

- Kairos internal crates own simulation primitives. Arrow/Polars are interchange
  backends; Python is a binding, and conformance fixtures are test oracles. Resolve
  actual feature closure through the existing integrator before promoting pins.
- Innovate's NumPy/SciPy/statsmodels/JitCDDE/PyTensor support diffusion fitting and
  diagnostics. PyArrow is its current interchange runtime; Polars and Bayesian/JAX
  extras are optional backends. Seven Kairos crates form its simulation provider
  edge. Keep application adapters here; do not move fitting into Kairos.
- MARS's serde/serde_json/anyhow/rayon are native runtime dependencies. PyO3 is a
  binding dependency incorrectly mandatory in the baseline; PR235 makes it
  optional. Criterion is development benchmarking. scikit-learn provides the
  existing Python model API and reference behavior; equivalence must precede
  replacement. Matplotlib currently remains a Python runtime dependency and
  needs a later separability change with import/API tests.
- Voiage's domain/estimators/numerical diagnostics remain its core. Its Arrow and
  Polars provider work and HPC build tools retain existing delivery ownership.
  Compiler bootstrap dependencies are build-only and need packaging justification.
- CareOps retains pathways/profiles and Kairos adapters. tobac/VOP retain economic
  assumptions, evidence, units, weights and policy. Their Voiage edges need real
  installed-consumer proof before updated pins are accepted.

Necessary differences: separate Arrow/PyArrow/Polars version lines, application
numerical oracles, and language binding toolchains. Accidental drift candidates:
older Python runners, unconditional PyO3 in MARS, mixed development/runtime
requirements, and stale sibling pins. No generic numerical implementation is
approved for extraction yet: a second consumer with equivalent semantics has not
been demonstrated. No catch-all dependency package was introduced.

Resolved optional-feature closure, actual imports and per-capability numerical
coverage remain implementation work. Lock resolution alone does not qualify an
optional backend or establish a truthful Rust MSRV.
