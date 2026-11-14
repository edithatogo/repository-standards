# Rust dependency rationalisation — repository-standards (2026-11-13)

**Status:** proposal and review contract; no code adoption, runtime verification or benchmark result is claimed here.

## Repository-specific decisions

- **Estate scope:** Rust source and generated bindings across repositories; inherited central standard is advisory until each local implementation and qualification receipt is accepted.
- **Preferred families:** Serde/Thiserror for versioned typed library boundaries; Anyhow for binaries; Clap for nontrivial CLIs; Tracing with privacy filtering; Reqwest+Tokio for asynchronous networking; SQLx when schema-checked RDBMS use is justified.
- **Specialised only:** Rayon on stable independent CPU partitions; Crossbeam for proven bounded synchronous channels; Polars for tabular analytics, retaining Arrow/Parquet interchange and provenance; Ratatui for interactive terminals; PyO3 for Python adapter crates; Bytes for proven binary I/O; Syn/Quote only for procedural macros.
- **Assurance:** Proptest for invariants and metamorphic relationships; Criterion for microbenchmarks with release-mode and locked fixtures; Insta for small reviewed/redacted snapshots; Regex for bounded text patterns, not domain parsers.
- **Decision ledger:** local adoption, retain, reject or defer with baseline/current dependency tree, MSRV, features, advisory and licence assessment, performance, public compatibility, deterministic execution and exact CI SHA.
- **Do not impose:** a universal dependency list, broad toolchain/MSRV upgrade, unnecessary approval rituals, or a new shared utility crate without demonstrated stable cross-repo semantics.
- **Cohort:** Mailweft, Paignia, CareOps-Sim, CiteLattice, FYI-CLI, Kairos, Searchright, FOI Process, Healthpoint-rs, Sourceright, Citeweft, Dapane, Voiage and Rust4PM; the template is advisory.

## Evidence and release gate
1. Discover actual source, package boundary, MSRV, lockfile, existing tests and Conductor ownership; avoid speculative dependencies.
2. For runtime behaviour, write failing contract tests before implementation, run targeted and full suites; preserve stable schemas, errors, CLI semantics and deterministic outputs.
3. Record `cargo tree -d`, feature selections, security/licensing/advisory reviews, transitive dependency cost and rollback before accepting an adoption.
4. For performance changes, benchmark identical inputs and correctness/invariance oracles; do not claim improvements without measurements.
5. This document is a planning entry, NOT proof of compilation, hosted CI or scientific validation; update status only after a revision-bound receipt.
