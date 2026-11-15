# Bounded Execution, Merkle Lineage and Metamorphic Property Standards Plan

**Goal:** Codify PGID-scoped resource-bounded execution, two-tier Merkle provenance manifests, and deterministic metamorphic property gates across the scientific repository estate.

**Spec:** [spec.md](spec.md).

## B01 — PGID-scoped process-group resource guard standard

- [ ] Document the canonical `run_bounded.py` contract (isolated session/PGID, `ps -g <pgid>` RSS sampling, serial heavy-runner discipline, fail-closed budget breach diagnostics, and child-group cleanup) in `docs/` and `profiles/scientific-native.json`.
- [ ] Add unit tests in `tests/` verifying that estate conformance checks distinguish PGID-scoped group RSS sampling from single-PID polling.

## B02 — Two-tier Merkle lineage manifest policy

- [ ] Specify the two-tier Merkle lineage schema separating `runner_closure_sha256` from `evidence_registry_merkle_root`, aligned with `edithatogo/tobac` (`scripts/hosted_lineage.py`) and `edithatogo/archive-govt-nz` (`tobac_merkle_lineage_provenance_20261110`).
- [ ] Add cycle-detection and tamper-rejection fixture tests to the central policy test suite.

## B03 — Deterministic metamorphic property gate

- [ ] Record the scientific metamorphic property testing standard (semigroup subdivision, mass conservation, dominance monotonicity, and Blackwell garbling non-negativity under `derandomize=True`) and cross-reference `edithatogo/tobac` (`tests/engineering/test_properties.py`), `edithatogo/voiage`, `edithatogo/innovate`, and `edithatogo/kairos`.
