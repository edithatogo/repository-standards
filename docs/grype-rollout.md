# Grype dependency and release scanning

The shared actions add vulnerability evidence to selected release pipelines.
They complement existing Cargo, Python and Node audits and preserve each
consumer's release, privacy, scientific and publication gates.

## Policy

Use advisory mode for dependency and packaging pull requests. Findings remain
visible without blocking on their severity. Use enforce mode with a `critical`
threshold before production image tags, package publication or release assets
are promoted. Raise a mature consumer to `high` only after its baseline has been
reviewed. A scanner error, stale database, malformed report, empty inventory or
missing release asset always fails, including in advisory mode.

No blanket ignore rules, fixed-version-only filtering or VEX suppressions are
enabled. A future exception must identify the affected package/advisory, reason,
review evidence and expiry; adding such a policy requires separate validation.
This increment intentionally supplies no bypass input.

## Shared scan action

Pin `edithatogo/repository-standards/.github/actions/grype-scan` to the reviewed
40-character implementation commit. It runs on Linux amd64 or arm64 with
Python 3.11 or newer. Existing repository Python choices remain unchanged.

| Input | Contract |
| --- | --- |
| `sbom` | Resolved CycloneDX, SPDX or Syft JSON; mutually exclusive with `image`. |
| `image` | Registry reference at a platform manifest `@sha256:…` digest. A multiarchitecture index must be expanded by the caller and every published architecture scanned. |
| `platform` | Expected `linux/amd64` or `linux/arm64`, optionally with variant. |
| `go-main-module` | Exact caller module (defaults to `github.com/` plus the caller repository). An explicitly marked UNKNOWN binary main module remains in the raw SBOM and an unmatchable-component receipt; it does not count as dependency coverage. |
| `mode` | `advisory` (default) or `enforce`. |
| `severity-cutoff` | `critical` by default; other supported severity thresholds are explicit. |
| `source-sha` | Exact Git commit associated with the scan; does not establish provenance by itself. |
| `source-role` | `build-source` by default; `monitor-workflow` for a monitor's code or `observed-release-tag` for a tag resolved during a released-asset rescan. |
| `output-directory` | Required new or empty directory; old evidence cannot be reused. |
| `artifact-name` | Required unique Actions artifact name. |
| `upload-artifact` | `true` by default. Set `false` only when a consumer retains the directory using its separately qualified storage, including on failure. |

The scanner verifies the upstream release archive checksums for Grype 0.122.1
and, for images, Syft 1.57.2. It records binary hashes and versions. It generates
an inventory from the requested image and verifies the catalogued manifest
digest and platform before scanning. Standard Docker registry credential
discovery remains available. No registry credentials are accepted in image URLs.

Each scan uses a fresh, isolated vulnerability database, requires its update to
succeed, validates its age (at most 120 hours), and records the database hash,
schema, origin and build time. Explicit configuration and a neutral working
directory prevent repository ignore files or scanner environment overrides
from silently changing the common policy.

The evidence directory contains the scanned SBOM, Grype JSON report when
available, database and tool metadata, diagnostic logs, a policy result and
SHA-256 checksums. Results distinguish `pass`, `findings`, `blocked` and `error`.
A passed threshold can still have findings below the threshold. Operational
failure is never classified as a clean result. Reports are retained in the
consumer's own artifact storage; private reports must not be copied into this
public control repository.

## Inventory scope

A metadata-only project document or a one-package byte inventory is insufficient.
The shared scanner requires versioned package identifiers and rejects dependency
ranges. This is a minimum validity control, not proof of dependency completeness.
Each consumer remains responsible for documenting what the inventory includes.
Exact Debian backport and RPM snapshot version separators are accepted. Go's
`go1.x` standard-library version is compared with its normalized purl version.
Unknown third-party dependency versions are not accepted by the main-module
exception, and an unversioned main module alone cannot satisfy inventory coverage.

The companion `.github/actions/cargo-lock-sbom` action accepts `lockfile`,
`output`, `name` and `source-sha`. It reads committed Cargo.lock bytes without
resolving dependencies and emits CycloneDX 1.6 with exact versions, registry
checksums, source identities, the locked dependency graph and a lockfile hash.
Its scope includes **all locked development, build, optional and target-specific
packages**. It does not assert that all packages are linked into a released
binary. Git and local path components remain in the inventory without falsely
assigning crates.io identities. Their vulnerability matching is limited.
OS libraries, separately resolved bindings and downloaded build-script inputs
need their own inventory. Keep artifact byte inventories and provenance alongside
this separate dependency evidence.

For Python, generate the inventory from the frozen, hash-locked runtime
environment and the exact built wheel. For other bindings, use the resolved
inventory for the package actually being published. An inventory resolved anew
after a release is not evidence about the original released dependency set.

## Publication ordering and monitoring

Build once, scan the candidate, then promote the same bytes. Container callers
may upload a uniquely named candidate to their registry, inspect its immutable
index, scan each platform manifest and promote only after every scan succeeds.
Verify the resulting production reference has the original index digest. Never
rescan one build and publish a subsequent rebuild. PR workflows do not need
registry write credentials: build an OCI archive and inventory that archive.

The released-SBOM rescan workflow accepts one exact `sbom-asset` JSON filename
and an `artifact-name`. The caller schedules it weekly. It resolves the latest
published stable release once, selects an immutable asset ID, verifies the
download against its GitHub-provided SHA-256 and size, then scans in advisory
mode with the current database. The download metadata records the observed tag
commit separately; this does not substitute for build provenance or attestation.
Missing assets, legacy assets without a supplied digest, and unavailable releases
fail explicitly. Enable this monitor when the publisher retains the qualified
SBOM. A scheduled source-lock scan has a different scope and must be labelled
accordingly.

## Rollout and verification

The first wave targets active container publishers and repositories with mature
release or SBOM paths. Follow-up candidates stay staged until these integrations
have hosted execution evidence. Do not extend the workflow to archived projects,
upstream forks or documentation-only repositories without a concrete artifact.

Run the repository's one-command policy suite and the Grype behavior controls.
The controls cover advisory versus enforced findings, operational failure,
stale/future database timestamps, unresolved/empty inventories, suppressed
matches, stale evidence and exact release-asset selection. Real scanner canaries
must demonstrate a known-vulnerable dependency blocks enforce mode and remains
visible in advisory mode. Hosted image and publication paths need their own
evidence; YAML validation cannot establish that they executed.

This increment is separate from ongoing offline-security qualification work.
It does not approve an offline runner, scanner image, source findings, scientific
release or publication. Unmerged PRs and unobserved hosted checks remain open.

## Upstream contracts

- [Grype 0.122.1 release](https://github.com/anchore/grype/releases/tag/v0.122.1)
- [Syft 1.57.2 release](https://github.com/anchore/syft/releases/tag/v1.57.2)
- [Grype database validation](https://oss.anchore.com/docs/guides/vulnerability/database/)
- [Grype exit-code and severity behavior](https://oss.anchore.com/docs/guides/vulnerability/filter-results/)
- [GitHub release asset API](https://docs.github.com/en/rest/releases/assets)
