# UniMelb Typst: executable components and release applicability

Assessment date: 15 November 2026 (Australia/Brisbane).
Central baseline: `10e59936e132f28597cb7d2f10efa27629dc4837`.
Consumer: [edithatogo/unimelb-thesis-template-typst][consumer].
Owners: [consumer #5][consumer-governance] and [central typesetting #5][typesetting].

This assessment corrects a July registry classification. It does not activate
settings, certify the latest consumer revision, implement a new collector, or
complete the separate [UMTHESIS document programme][contract]. The existing
`typesetting-template` archetype and `typst` profile are retained.

## Registry decision and qualification boundary

| Field | Decision | Evidence boundary |
| --- | --- | --- |
| `archetype` / `profile` | Retain `typesetting-template` / `typst`. | Typst compilation and document-output checks remain required; Python helpers do not replace the document profile. |
| `codecov.warranted` | `true`. | Executable Python validation/policy helpers have measured unit-test coverage. The previous no-executable-coverage exclusion is stale. |
| `codecov.current` | `active`, scoped by `evidence_revision`. | Actual upload and Codecov-owned `codecov/patch` success exist for `66beec5cd7b78a9cdc1aad37dd288350184ef14d`. This is service activity on that candidate, not current-main qualification. |
| `codecov.target` | `active_oidc_upload_with_real_coverage`. | Preserve OIDC upload and actual producer-check verification on each final candidate and receiving revision. |
| `codecov.receiving_main_qualified` | `false`. | No passing receiving-main coverage result is asserted by this central change. Refresh only after exact-revision execution and provider evidence. |
| `supply_chain_profile` | `published`. | Published source releases exist, and the tag-only release workflow is configured to publish a PDF. This selects applicable controls; it does not claim those controls are implemented or passed. |

The consumer's latest candidate considered here is
`7e2d09c934c3c9805a222f39c6fd073885196b48` in [PR #12][maintenance-pr].
Its quality, privacy, Python coverage and CodeQL checks passed. The Codecov
upload is still queued at the 2026-11-14T15:51:12Z observation, so external
provider and receiving-main qualification remain open. Historical service
activity must not be carried forward as its pass.
The main migration from PR #10 was integrated as
`b947d5ea0ad1a9c118a9c3670bcb82200052c9a2`; it is not a substitute for
qualification of PR #12's additional executable code.

## Executable helpers and document checks

The measured coverage component consists of exactly:

- `scripts/preflight.py`;
- `scripts/validate_template.py`;
- `scripts/check_repository_policy.py`.

The [published policy-fix receipt][policy-fix-receipt] records local Python
3.15.1 and coverage.py 7.17.3 results for the source published at
`b1b465c74324f75c815cf199ef45d7ff631d20d5`: 59 unit tests and
97.72329246935202% combined line/branch coverage (372/381 statements,
186/190 branches, zero excluded lines). It records source SHA-256 hashes,
10 properties / 640 iterations, and real thesis/sample PDF checks.
These are revision-specific results; the later governance delta is not
certified by them.

The current candidate's [hosted coverage job][current-coverage] independently
ran Python 3.15.1 and all 61 maintenance tests, reporting 97.74% combined
coverage. Its exact local coverage.py 7.17.3 measurement is
97.73913043478261%: 374/383 statements and 188/192 branches, with zero
excluded lines. The retained hosted artifact is `14120206858`, with digest
`sha256:1e90c3a5af3591a32ba8543e6c21aeaeedbd4f4546691dc3de0d8c01eb2a3a50`.
The upload/provider boundary remains separate from successful measurement.

The earlier [hosted maintenance run][maintenance-run] at `66beec5` executed
the then-current 54 tests with 97.59% combined coverage. Its upload succeeded,
and the actual [producer check][codecov-checks], app ID 254, reported
98.80% of the diff hit against an 80% target. The [Codecov PR view][codecov-pr]
identifies this repository and PR. An upload job alone would not establish
successful provider processing.

The 80% floor applies to the declared three-file component. It is not a
whole-repository coverage claim. Other Python helpers, including the term and
abbreviation management utilities, are outside this denominator; generated
property tests exercise some of their contracts separately. Shell scripts and
Typst sources are not measured by coverage.py. Zero excluded lines refers to
the selected component, not to all executable files in the repository.
Typst compilation, four profile builds, PDF structure/text checks and visual
inspection remain separate evidence; none is represented as document line
coverage or proof of institutional compliance.

If these results are wrapped in the [central receipt schema][receipt-schema],
put separate line and branch percentages in their named metric fields. Keep
the combined percentage, denominators, source hashes and exclusions in the
native coverage sidecar. Do not add unsupported top-level fields or place a
combined percentage in `line_coverage_percent`. The complete adapter remains
owned by [consumer #22][consumer-evidence] and [central #19][receipt-owner].

## CodeQL applicability and collector limits

Python helpers and GitHub Actions are applicable CodeQL analysis components.
The consumer uses default setup; adding a competing advanced configuration
is unnecessary. [Baseline analysis][baseline-codeql] passed Python and Actions
at `6d4652936b4eabaac29462ab8caf86e248c0f96a`, and
[PR #10 analysis][candidate-codeql] passed at
`0f2f2ecc4b4a0ba3e99a1bb2f84bf5cec5ee5068`. These source identities must remain
attached to their results. Obtain applicable analysis on the changed final
candidate and its receiving revision; the historical analyses do not qualify
the newer policy checker. The [current candidate analysis][current-codeql]
passed both languages and the CodeQL-owned aggregate check on `7e2d09c`.
Receiving-main analysis remains open. No CodeQL analysis of Typst layout is
claimed.

The current central [`typst` profile][profiles] inherits `executable: false`
and `coverage: not_applicable` from `documentation`. The legacy
[`audit_estate_conformance.py`][collector] also detects CodeQL from committed
workflow paths/text and does not establish default-setup execution from those
heuristics. The registry's component evidence corrects the stale classification
but does not change these implementation limits or make new enforcement
claims. Component-aware collector/profile semantics belong to the existing
[F04 verification track][f04] and its inventory owners. Do not globally change
all typesetting repositories to executable software to resolve this consumer.

## Published-artifact supply-chain applicability

The release API records published `v0.2.1`, `v0.1.1` and `v0.1` releases. Their
attached asset lists are empty at this assessment; see [release inventory][releases]
and [v0.2.1][release]. Source releases therefore exist, but no release PDF
attachment is claimed. The [current tag-only workflow][release-workflow]
checks tag/version agreement, compiles and validates `build/thesis.pdf`, then
is configured to publish that PDF. It does not currently establish an executed,
artifact-bound SBOM/provenance/consumer-verification chain.

The existing `published` profile requires dependency review, Scorecard, SBOM,
provenance and checksums. The public-repository audit also selects Security
Insights and SLSA verification for this profile. The consumer has executed
dependency-review evidence in its [qualified PR #10 quality run][quality-run].
This assessment does not claim completion of the other selected controls;
changing the registry may correctly surface additional conformance gaps.
No blanket exception is introduced to hide them.

Release evidence should bind the exact source, build/tool/input identities
and final artifact digest, and downstream verification should reject mismatched
artifacts or provenance. A workflow declaration or an SBOM for the source tree
alone is not that proof; no SLSA level or reproducible-PDF claim is made here.
Implementation stays with [central supply-chain #20][supply-chain-owner],
[F05][f05] and consumer release/replay [#20][consumer-release], packaging #21,
and evidence #22. The foundation's GOV-03 obligation is this truthful
applicability/evidence reconciliation, not completion of all later document
outputs. [F07][f07] remains responsible for dated, scoped assurance claims.

## Remaining integration and ownership

Before qualifying the changed consumer, record its exact final-head and
receiving-main verification, declared coverage, CodeQL, actual provider check
and live governance read-back under consumer #5/#6. The desired policy alone
does not activate a ruleset. Preserve zero required approvals, conversation
resolution and owner recovery; this central patch changes no settings.

The full live ruleset inventory read back at 2026-11-14T15:51:12Z contains
one active [ruleset, 27266891][live-ruleset]. The candidate's checker returned
MATCH / exit 0: all eight intended status contexts are bound to GitHub Actions
app ID 15368, conversation resolution is required, approval count is zero,
and the only recovery actor is repository owner `edithatogo`. The consumer's
integration receipt is being refreshed to retain the full snapshot and its
observation boundary; this settings result does not qualify queued provider
execution.

This change owns only the Typst registry entry and this assessment. Central
[PR #119][registry-overlap] edits the same registry file for genomics, and
[PR #141][latex-overlap] updates the LaTeX classification; preserve those
entries and reconcile the current central main before integration. No
LaTeX, Quarto or other repository classification is changed by this assessment.
Existing Renovate ownership is retained. The separately held offline-security
rollout is unaffected. Full programme acceptance remains with #13 and its
existing leaf owners; it is not added to the historical #6 child count.

[consumer]: https://github.com/edithatogo/unimelb-thesis-template-typst
[consumer-governance]: https://github.com/edithatogo/unimelb-thesis-template-typst/issues/5
[typesetting]: https://github.com/edithatogo/repository-standards/issues/5
[contract]: https://github.com/edithatogo/unimelb-thesis-template-typst/issues/13
[maintenance-pr]: https://github.com/edithatogo/unimelb-thesis-template-typst/pull/12
[policy-fix-receipt]: https://github.com/edithatogo/unimelb-thesis-template-typst/blob/b1b465c74324f75c815cf199ef45d7ff631d20d5/docs/maintenance/issue-5-receipt.json
[maintenance-run]: https://github.com/edithatogo/unimelb-thesis-template-typst/actions/runs/43606355606
[current-coverage]: https://github.com/edithatogo/unimelb-thesis-template-typst/actions/runs/43609602102/job/132491525752
[codecov-checks]: https://api.github.com/repos/edithatogo/unimelb-thesis-template-typst/commits/66beec5cd7b78a9cdc1aad37dd288350184ef14d/check-runs?per_page=100
[codecov-pr]: https://app.codecov.io/gh/edithatogo/unimelb-thesis-template-typst/pull/12
[receipt-schema]: ../schemas/verification-receipt.schema.json
[consumer-evidence]: https://github.com/edithatogo/unimelb-thesis-template-typst/issues/22
[receipt-owner]: https://github.com/edithatogo/repository-standards/issues/19
[baseline-codeql]: https://github.com/edithatogo/unimelb-thesis-template-typst/actions/runs/43604503605
[candidate-codeql]: https://github.com/edithatogo/unimelb-thesis-template-typst/actions/runs/43608078096
[current-codeql]: https://github.com/edithatogo/unimelb-thesis-template-typst/actions/runs/43609599167
[live-ruleset]: https://github.com/edithatogo/unimelb-thesis-template-typst/rules/27266891
[profiles]: ../profiles/archetype-profiles.json
[collector]: ../scripts/audit_estate_conformance.py
[f04]: ../conductor/tracks/frontier_04_verification_harness_20261113/spec.md
[releases]: https://api.github.com/repos/edithatogo/unimelb-thesis-template-typst/releases?per_page=20
[release]: https://github.com/edithatogo/unimelb-thesis-template-typst/releases/tag/v0.2.1
[release-workflow]: https://github.com/edithatogo/unimelb-thesis-template-typst/blob/7e2d09c934c3c9805a222f39c6fd073885196b48/.github/workflows/release.yml
[quality-run]: https://github.com/edithatogo/unimelb-thesis-template-typst/actions/runs/43608082998
[supply-chain-owner]: https://github.com/edithatogo/repository-standards/issues/20
[f05]: ../conductor/tracks/frontier_05_release_supplychain_20261113/spec.md
[consumer-release]: https://github.com/edithatogo/unimelb-thesis-template-typst/issues/20
[f07]: ../conductor/tracks/frontier_07_observability_certification_20261113/spec.md
[registry-overlap]: https://github.com/edithatogo/repository-standards/pull/119
[latex-overlap]: https://github.com/edithatogo/repository-standards/pull/141
