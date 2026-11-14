# UniMelb LaTeX: executable components and release applicability

Assessment date: 15 November 2026 (Australia/Brisbane).
Central base: `e195af3b0f46db74e797c5bf2e177b7882085186`.
Consumer evidence revision: `dbfe80897a0616babeaa41341b54ffcbea79c867`.
Owners: [LaTeX #8][governance], [integration #9][integration], and
[central typesetting #5][typesetting].

This assessment corrects the LaTeX registry entry's stale applicability claims.
It preserves the `typesetting-template` archetype and `latex` profile, the
existing Typst entry and assessment, and the separate [UMTHESIS work][contract].
It does not activate repository settings or certify release artifacts.

## Registry decisions

| Field | Corrected state and evidence boundary |
| --- | --- |
| `renovate.current` | `hosted_app_verified`: the bot-owned [Dashboard #10][renovate-dashboard] and merged [PR #11][renovate-pr] establish hosted operation with the shared preset. |
| `codecov.current` | `active_oidc_upload_verified`: upload and actual provider processing succeeded for the exact consumer revision above. This is dated evidence, not qualification of subsequent commits. |
| `codecov.warranted` | `true`: executable Python helpers have real tests and measured coverage. |
| `codecov.target` | `active_oidc_upload_with_real_coverage`: retain actual measurement, OIDC upload and provider acceptance evidence. |
| `supply_chain_profile` | `published`: a public release contains a PDF, making published-artifact controls applicable. This does not assert that those controls pass. |

Support remains `active`. Maintenance tier, release maturity and canonical status
remain `review_required`; recent activity and an old release do not determine
those owner declarations. Zero mandatory approvals and `exceptions: []` remain
unchanged. No missing control is waived or certification flag promoted.

## Executable coverage and provider processing

The current measured component consists of three Python helpers:

- `scripts/check_codeql.py`;
- `scripts/verify.py`;
- `scripts/verify_science.py`.

The [receiving-main measurement job][coverage-job] ran all **53 tests** and
reported **86% combined coverage** with coverage.py: 321 statements, 47 missed
statements, 112 branches and 10 partial branches. This is a combined metric for
the selected helpers, not a whole-repository or document-correctness percentage.

The separate [OIDC upload job][upload-job] succeeded. The [exact-commit Codecov
API report][codecov-api] records `state: complete`, a populated three-file report,
and totals of 321 lines, 264 hits, 47 misses, 10 partials and **82.24%** coverage.
The repository API also reported `active: true` and `activated: true`; GitHub
recorded a successful `codecov/patch` status targeting that [commit report][codecov-report].
Provider processing is therefore observed, not inferred from configuration or
an upload exit status alone. Codecov's percentage and coverage.py's combined
percentage are distinct measurements and must not be interchanged.

TeX sources, template styles and generated PDFs remain outside executable Python
coverage. Thesis compilation, reference/structure checks and visual review are
separate obligations. The profile's inherited `executable: false` still limits
the legacy central collector; this registry correction does not implement a
component-aware collector. That work remains with [F04][f04] and its owners.

## CodeQL and governance

Python helpers and GitHub Actions are applicable CodeQL components. The
[native Python analysis job][native-python] for the same receiving revision
scanned six of six Python files, uploaded SARIF successfully and recorded
completed server processing. This establishes executed native Python analysis
at that revision; it does not claim an administrative configuration API read or
qualification of future revisions. Preserve the existing repository-owned
findings gates and native setup rather than introducing a competing scanner.

[LaTeX #8][governance] remains open for actual ruleset activation and read-back.
The observed live inventory was empty and main unprotected. The desired rule
requires conversation resolution, stable app-bound checks and blocked
force-push/deletion, with zero mandatory human approvals and owner recovery.
A committed ruleset file is not live enforcement. Existing authenticated
administration limitations remain explicit.

## Published artifacts and remaining controls

[Release v1.2.0][release], published 11 September 2025, contains `Thesis.pdf`
(11,752 bytes). The [current release workflow][release-workflow] separates
verification from tag-triggered publication and publishes the verified PDF.
That source configuration is distinct from proof of a newly executed release,
a declared stable support policy, or artifact-bound supply-chain evidence.

The existing `published` profile selects dependency review, Scorecard, SBOM,
provenance and checksums; the public-repository audit also selects Security
Insights and SLSA verification. Dependency review has existing qualified
consumer evidence. The following gaps remain recorded without suppressing them:

| Outstanding item | Existing owner | Review by |
| --- | --- | --- |
| Ruleset activation/read-back and maintenance/release/canonical declarations | LaTeX #8/#9 and central #5 | 22 November 2026 |
| Scorecard and Security Insights evidence | Central #20 assurance work | 22 November 2026 |
| SBOM, provenance and checksums bound to the shipped PDF; consumer SLSA verification | Central #20/[F05][f05] and [LaTeX #18][adapter] | 22 November 2026 |

Review earlier before activation, release qualification or issue closure. A
checksum used to download a CI tool does not supply a checksum for the released
PDF. A source-tree SBOM or a reusable workflow declaration does not establish
the artifact/source/builder chain. No SLSA level, deterministic-PDF guarantee or
whole-estate conformance is claimed. Central F04/F05/[F07][f07] status flags and
the conditional offline-security rollout remain unchanged.

[governance]: https://github.com/edithatogo/unimelb-thesis-template-latex/issues/8
[integration]: https://github.com/edithatogo/unimelb-thesis-template-latex/issues/9
[typesetting]: https://github.com/edithatogo/repository-standards/issues/5
[contract]: https://github.com/edithatogo/unimelb-thesis-template-typst/issues/13
[renovate-dashboard]: https://github.com/edithatogo/unimelb-thesis-template-latex/issues/10
[renovate-pr]: https://github.com/edithatogo/unimelb-thesis-template-latex/pull/11
[coverage-job]: https://github.com/edithatogo/unimelb-thesis-template-latex/actions/runs/43641749972/job/132590627335
[upload-job]: https://github.com/edithatogo/unimelb-thesis-template-latex/actions/runs/43641749972/job/132590758974
[codecov-api]: https://api.codecov.io/api/v2/github/edithatogo/repos/unimelb-thesis-template-latex/commits/dbfe80897a0616babeaa41341b54ffcbea79c867/
[codecov-report]: https://app.codecov.io/gh/edithatogo/unimelb-thesis-template-latex/commit/dbfe80897a0616babeaa41341b54ffcbea79c867
[native-python]: https://github.com/edithatogo/unimelb-thesis-template-latex/actions/runs/43641749723/job/132590628000
[release]: https://github.com/edithatogo/unimelb-thesis-template-latex/releases/tag/v1.2.0
[release-workflow]: https://github.com/edithatogo/unimelb-thesis-template-latex/blob/dbfe80897a0616babeaa41341b54ffcbea79c867/.github/workflows/release.yml
[adapter]: https://github.com/edithatogo/unimelb-thesis-template-latex/issues/18
[f04]: ../conductor/tracks/frontier_04_verification_harness_20261113/spec.md
[f05]: ../conductor/tracks/frontier_05_release_supplychain_20261113/spec.md
[f07]: ../conductor/tracks/frontier_07_observability_certification_20261113/spec.md
