# Minimal Rust supply-chain policy (24 November 2026)

The estate's Rust CI contract is **reuse first**, after inspecting the actual
Cargo workspace and any existing release/security jobs. This is consistent with
[Ponytail](https://github.com/DietrichGebert/ponytail): the smallest complete
change without losing testing, integrity, security or error handling.

## Tools

1. **cargo-deny:** the normal PR dependency gate. Check RustSec advisories,
   SPDX licences, crate bans and sources against a repository-owned `deny.toml`.
   The [reusable workflow](../.github/workflows/rust-dependency-policy.yml) uses
   the upstream action pinned by commit. Call it at an immutable commit SHA.
2. **cargo-audit:** retain the separate scheduled/release RustSec scan if already
   present. It uses the same RustSec advisory data; do not add a redundant full
   compile/install job solely for a second view of the same database.
3. **cargo-vet:** adopt selectively where owners can maintain a real audit ledger,
   criteria and independently reviewed exemptions. Preserve existing imported
   ledgers in Searchright and Fe-reader; never manufacture audit attestations.
4. **cargo-quality:** do not mandate. Use existing `cargo fmt` and Clippy,
   plus project-specific tests.

Do not put any of these Cargo CLI tools in runtime `[dependencies]`.
Keep `deny.toml` beside the workspace manifest, or use an existing root policy.
For nested workspaces, pass `manifest-path` and confirm that deny locates the
correct policy. For unpublished crates explicitly marked `publish = false`,
`[licenses.private] ignore = true` avoids treating proprietary internal source
as an unlicensed **third-party** dependency; it does not waive transitive
licence scanning. Never set that flag without verifying the package manifests.

## Consumer example

```yaml
name: Rust dependency policy
on:
  pull_request:
    paths: ['**/Cargo.toml', '**/Cargo.lock', '**/deny.toml', '.github/workflows/rust-dependency-policy.yml']
  push:
    branches: [main]
    paths: ['**/Cargo.toml', '**/Cargo.lock', '**/deny.toml', '.github/workflows/rust-dependency-policy.yml']
  schedule:
    - cron: '23 3 * * 1'
  workflow_dispatch:
permissions:
  contents: read
jobs:
  policy:
    uses: edithatogo/repository-standards/.github/workflows/rust-dependency-policy.yml@<PINNED_COMMIT_SHA>
    with:
      manifest-path: ./Cargo.toml
      rust-version: stable
```

This is a *reference*, not an automatic estate deployment. Never add this call
where existing CI already covers all four categories to an equivalent standard.
An advisory discovered after a PR must be triaged as a concrete finding, not
suppressed in perpetuity. Merge needs exact-head hosted checks, and separate
local tests/Conductor acceptance remain authoritative for runtime behavior.

The cross-repository rollout is tracked in
[the GitHub issue](https://github.com/edithatogo/.github/issues/11); two
pilot proposals are [Dioryx #12](https://github.com/edithatogo/dioryx/pull/12)
and [Mailweft #28](https://github.com/edithatogo/mailweft/pull/28).
