# OpenGrep SAST pilot standard (20 November 2026)

This is a **provisional reusable GitHub Actions workflow**, not a universal mandatory check. It supports Python only at present. The tested standalone OpenGrep v1.33.1 Linux binary is pinned by upstream published SHA-256. The workflow checks that the scan directory is inside the checkout, runs synthetic positive and safe controls, and scans the complete selected tracked source directory using `--strict --error --config p/python --severity WARNING`.

## Usage

Consumers should pin the **full accepted commit SHA** of `.github/workflows/reusable-opengrep-sast.yml` in `edithatogo/repository-standards`. The caller uses `workflow_call` with `source_path` pointing at a relative directory; for example `tools` in a Python CLI repository. No external tokens or additional source uploads are needed. The workflow runs in the caller's read-only GitHub runner, retains findings locally in an ephemeral temp file, and prints only aggregate scan counts on success.

## Qualification limitations

The `p/python` alias remains a dynamic remote rule pack, exactly as in the prior Semgrep configurations. It is *not* a cryptographically frozen ruleset. Before making this a required check, independently reconcile rule IDs, parser/skip inventory, findings and rule redistribution rights. Scanner exit status, nonempty file inventory and JSON errors fail closed; it cannot establish that every semantic data-flow vulnerability is detected. Maintain CodeQL, Bandit, Gitleaks, dependency security and privacy gates. Do not treat this reusable workflow alone as evidence of runtime execution or full repository coverage.

Full-estate adoption, branch-protection changes and Rust/JS/TS profiles require separate qualified PRs. Existing CareOps and Neocam implementations are not overwritten. Semgrep migrations in `aegisarchive` PR #93 and `nlp-policy-nz` PR #368 remain independent until their exact-head checks and source provenance have been accepted.
