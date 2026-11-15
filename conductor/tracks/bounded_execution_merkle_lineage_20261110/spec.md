# Specification — Bounded process-group execution, two-tier Merkle lineage and metamorphic property gates

## Purpose

Codify reusable estate-wide engineering and scientific-integrity standards validated in `edithatogo/tobac` (`F00`, `H2`, PR #147 and PR #155) so scientific Python/Rust repositories share one consistent contract for bounded macOS/POSIX execution, non-circular two-tier Merkle provenance attestation, and deterministic Hypothesis/proptest metamorphic invariant suites.

## Scope

1. **PGID-scoped bounded process-group execution (`B01`)**:
   - Require heavy test, calibration, audit, and mutation runners on macOS and POSIX hosts to launch child processes in an isolated process group (`start_new_session=True`), sample whole-group RSS (`ps -o pid=,rss= -g <pgid>`), enforce explicit memory and wall-clock ceilings (default 4 GiB RSS and 40 minutes for single-developer macOS research workstations), stream logs to disk, and terminate the owned process group cleanly on budget breach or exit without automatic retries.
2. **Two-tier Merkle scientific lineage attestation (`B02`)**:
   - Separate the **runner/code closure digest** (`runner_closure_sha256` over executable scripts, lockfiles, and schemas) from the **candidate evidence/data registry Merkle root** (`evidence_registry_merkle_root` over immutable raw inputs and generated outputs) so provenance sidecars never introduce self-referential hash cycles when audited by `tobac` or `archive-govt-nz`.
3. **Deterministic metamorphic property testing (`B03`)**:
   - Require scientific numerical kernels (competing-risks semigroups, cohort conservation, partial-identification interval monotonicity, and Blackwell information ordering) to pair analytical reference oracles with derandomized property-based suites (`@settings(derandomize=True, deadline=None)` in Hypothesis / deterministic seeds in `proptest`).

## Claim boundary

Policy definitions and estate-audit checks verify structural conformance only; they do not establish that a consumer repository's numerical methods or empirical calibrations have been executed.
