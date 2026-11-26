# standards_check: observed updater and coverage operation

Assessment date: 23 November 2026 (UTC).
Central base: `a3cc8dccdb67e6f122c71cec713194cdec792d07`.
Consumer evidence revision: `12b7b00737124aa7c0feaead893c930124332489`
([PR #100][consumer-pr], source tree
`d78a8d83327a67172544f04a716e4eef5950a9aa`).
Owner: [standards_check #30][quality-issue].

This correction records observed hosted updater operation and coverage uploads.
The registered `node` profile, `baseline` supply-chain profile, owner declarations,
approval policy and updater removal gate retain their existing values.

## Registry decisions

| Field | Observed state and evidence boundary |
| --- | --- |
| `renovate.current` | `hosted_app_verified`: a bot-owned dashboard and merged bot dependency PR establish actual hosted operation. |
| `renovate.dependabot_detected` | `true`: the consumer retains a weekly GitHub Actions Dependabot manifest. |
| `codecov.current` | `active_oidc_upload_verified`: three component uploads and an actual Codecov App patch check succeeded for the exact evidence revision. |
| `codecov.evidence_revision` | The PR head above; the upload jobs explicitly supplied this SHA. |
| `codecov.receiving_main_qualified` | `false`: this evidence concerns a PR head, not qualification of receiving main. |

These descriptive fields follow the existing [LaTeX][latex-assessment] and
[Typst][typst-assessment] assessment conventions. They do not introduce a new
collector, policy exception or acceptance gate.

## Renovate and retained Dependabot

[Dashboard #76][renovate-dashboard] is authored by `renovate[bot]`. The observed
dashboard, updated at `2026-11-23T01:43:06Z`, detects the maintained Cargo,
submodule, GitHub Actions, npm, requirements, regex and Rust toolchain managers.
[PR #89][renovate-pr], also authored by `renovate[bot]`, updated the Rust `url`
crate to 2.5.9 for security and merged at `2026-11-22T21:12:30Z` as
`c3e386eed5edc39032fcf71d5b2468321cf69dfb`.

During this assessment the authenticated repository [installation
settings][installation-settings] also showed **Renovate**, developed by **mend**,
under **Installed GitHub Apps**. This is UI evidence of app presence, distinct
from the bot's executed update evidence.

The [Dependabot manifest][dependabot] exists at the consumer evidence revision
(Git blob `ca79ca5b4d5245d3dbcf49889b73d7fd0f076132`) and schedules weekly GitHub
Actions updates. It remains in place. The registry's
`removal_gate: "Renovate first successful run"` also remains unchanged.
Manager discovery and one merged update do not establish successful protected
update/merge operation for every maintained ecosystem.

## Coverage uploads and provider processing

[Assurance run 45096059220][assurance-run] measured real Python, Rust and API
coverage. The Python report includes all 24 maintained production modules,
including unexecuted modules at zero; its combined line/branch result is 75.82%.
The Rust measurement passed its 79% line floor. The API report includes the two
production modules present at this revision and reports 99.22% line coverage.
These component denominators and metrics are distinct.

| Component | Measurement job | Separate OIDC upload job |
| --- | --- | --- |
| Python | [137435997679][python-coverage] | [137436896235][python-upload] |
| Rust | [137435997766][rust-coverage] | [137436896229][rust-upload] |
| API | [137435997873][api-coverage] | [137436896212][api-upload] |

Each upload obtained a Codecov OIDC token, selected its single report with file
search disabled, and supplied the exact PR head SHA. All three uploads were
accepted and queued for processing. Upload completion alone was not the final
provider evidence: [check 137437302663][codecov-check], named `codecov/patch` and
owned by the Codecov App (ID 254), subsequently completed successfully at
`2026-11-23T01:46:54Z`. It reported **94.59% diff coverage against an 80% target**
for the same revision. The [commit report][codecov-report] is the provider view.

At the retained observation cutoff, `2026-11-23T01:48:26Z`, no Codecov project
check was observed, and the legacy commit-status endpoint contained zero
statuses; the provider evidence came from the Check Runs API. The first PR
head's boundary-mutation job failed because its isolated Python 3.12 setup
lacked a required dependency; the aggregate assurance job correctly failed too.
Successful uploads and patch processing do not qualify that whole candidate.
Corrected heads, project-check acceptance, receiving-main qualification and
live ruleset activation require their own evidence under the owner issue.

## Central correction validation

On Python 3.15.2, the required
`PYTHONPATH=scripts .venv/bin/python -m unittest discover -s tests -v` completed
successfully: 349 discovered tests, 311 passed and 38 capability skips (26
isolated Presidio and 12 verified Gitleaks tests). All 168 entries validate
against the existing repository-entry schema. The other 167 entries and bytes
outside this entry are unchanged, and the registry retains CRLF line endings.
The scientific policy check passes. Whitespace validation passes with Git's
`cr-at-eol` setting to recognize the preserved registry format. No schema,
collector, workflow or repository setting was changed by this correction.

[consumer-pr]: https://github.com/edithatogo/standards_check/pull/100
[quality-issue]: https://github.com/edithatogo/standards_check/issues/30
[renovate-dashboard]: https://github.com/edithatogo/standards_check/issues/76
[renovate-pr]: https://github.com/edithatogo/standards_check/pull/89
[installation-settings]: https://github.com/edithatogo/standards_check/settings/installations?page=3
[dependabot]: https://github.com/edithatogo/standards_check/blob/12b7b00737124aa7c0feaead893c930124332489/.github/dependabot.yml
[assurance-run]: https://github.com/edithatogo/standards_check/actions/runs/45096059220
[python-coverage]: https://github.com/edithatogo/standards_check/actions/runs/45096059220/job/137435997679
[rust-coverage]: https://github.com/edithatogo/standards_check/actions/runs/45096059220/job/137435997766
[api-coverage]: https://github.com/edithatogo/standards_check/actions/runs/45096059220/job/137435997873
[python-upload]: https://github.com/edithatogo/standards_check/actions/runs/45096059220/job/137436896235
[rust-upload]: https://github.com/edithatogo/standards_check/actions/runs/45096059220/job/137436896229
[api-upload]: https://github.com/edithatogo/standards_check/actions/runs/45096059220/job/137436896212
[codecov-check]: https://github.com/edithatogo/standards_check/runs/137437302663
[codecov-report]: https://app.codecov.io/gh/edithatogo/standards_check/commit/12b7b00737124aa7c0feaead893c930124332489
[latex-assessment]: typesetting-unimelb-latex-assessment.md
[typst-assessment]: typesetting-unimelb-typst-assessment.md

## Receiving-main follow-up — 23 November 2026

Central base: `2efdbd988064f6857795b9fa9ed4e1d08d18791d`. The preceding
assessment remains the historical record of its original PR head and cutoff.
This follow-up updates five descriptive fields in the same consumer entry.

### Qualified corrective receiving main

[PR #107][corrective-pr] merged normally as
[`dd3f995c473db0cc1cd6dad9d392b3744166958b`][corrective-main], tree
`3bdbebf0bb72a7f7edf9c90a7c4fc10412d98200`. Its parents are main
`8029b1a55fb4273878510681c1a5a7b5c02b57f0` and qualified PR head
`4e8e13a632777f2916b183101774cf2ff5389823`. The earlier main's coverage
qualification remains historical; it did not qualify this API repair.
[Assurance run 45106620582][corrective-assurance] measured the actual corrective
main and uploaded separately verified reports:

| Component | Actual main result | Measurement job | OIDC upload job |
| --- | --- | --- | --- |
| Python | 265 tests; 28 production modules; 76.68% combined coverage | [137469276587][corrective-python] | [137469891138][corrective-python-upload] |
| Rust | 72 tests; 2,742/3,430 lines, 79.94% | [137469276491][corrective-rust] | [137469891156][corrective-rust-upload] |
| API | 41 tests; 143/143 lines, 100%; 41/42 branches, 97.62% | [137469276443][corrective-api] | [137469891135][corrective-api-upload] |

All three uploads acquired OIDC tokens, verified the native report checksum and
selected one explicit report with its component flag and file search disabled.
These push jobs detected the checked-out main revision; `CC_SHA` was empty and
the CLI used no explicit `--sha` override. Every returned provider URL names
`dd3f995c473db0cc1cd6dad9d392b3744166958b`.

At `2026-11-23T03:37:59Z`, the [legacy status endpoint][corrective-status]
reported successful `codecov/patch` status **59621115216**, created at
`2026-11-23T03:35:37Z`, with description “Coverage not affected when comparing
4e8e13a...dd3f995” and the exact [main report][corrective-codecov]. No Codecov
App ID 254 check-run or project result was returned. The status payload did not
include creator attribution, so this legacy result is not attributed to that
App. Uploader execution, queue acceptance and provider processing remain
separate observations. The registry advances `codecov.evidence_revision` to
this corrective main and `codecov.receiving_main_qualified` to `true` for this
scoped coverage qualification; it does not claim a project check or universal
repository acceptance.

The ten hand-selected boundary mutations were killed by assertions, with no
survivors, unviable cases or timeouts. This is not a global mutation score.
The actual main Python job also passed the retained two authored PRISMA pairs
and checked two documented validation differences; full legacy semantic parity
remains separate.

### Protection and security observations

[Ruleset 27871801][receiving-ruleset] is active on the default branch, with
strict up-to-date checks, zero mandatory human approvals, resolved review
conversations, no bypass actors, and no deletion or non-fast-forward pushes.
All seven required contexts are bound to GitHub Actions App ID 15368:
`assurance`, `privacy-and-secrets`, `Maintained dependency inventories`, and
`Analyze (actions)`, `Analyze (javascript-typescript)`, `Analyze (python)` and
`Analyze (rust)`. The native CodeQL rule requires `high_or_higher` security
severity and ordinary alert threshold `errors`.

The receiving-main security readback at `2026-11-23T03:36:04Z` showed zero open
and four closed CodeQL alerts; [path-selection alerts #5][path-alert-five] and
[#6][path-alert-six] were fixed through PR #107. Privacy job **137469276069**
passed with zero Gitleaks findings, zero reviewed exceptions and zero blocking
Presidio findings; its seven advisory findings remain distinguished from
blocking findings. Saved protection, executed checks and actual protected
merge are separate evidence.

### Evidence-grounded classifications

The existing [entry schema][classification-schema] provides these descriptive
values; the [lifecycle standard][lifecycle-standard] requires evidence for
canonical roles. The user's explicit retention and continued-maintenance
instruction, together with the [receiving README][receiving-readme], supports:

| Field | Recorded value | Evidence boundary |
| --- | --- | --- |
| `maintenance_tier` | `maintained` | Ongoing authorized maintenance and accepted repairs in the retained repository. |
| `canonical_status` | `canonical` | The repository identifies itself as the primary adoption home; the source repository has been made private and archived after consolidation. |
| `release_maturity` | `experimental` | The README explicitly describes a platform being developed, operational legacy surfaces and future architecture. A `v0.1` tag exists; the GitHub releases collection returned no releases. This does not claim no external distribution, a stable release, full migration parity or source-rights acceptance. |

### Managed CI disposition

The registered `node` profile and explicit `baseline` supply-chain selection
remain unchanged. The [profile][receiving-profile] requires dependency review
and SBOM; the local workflows provide these, root/API npm tests, measured
Python/Rust/API coverage, and isolated source-bound uploads. No extra native
test type or baseline supply-chain capability was identified in the shared
Node workflow that is missing from this implementation.

The [managed-file manifest][receiving-managed] preserves local additions and
prohibits forced overwrite. The [continuous-conformance standard][conflict-route]
routes semantic conflicts and repository-local extensions to issues, while the
[enforcement track][stronger-controls] preserves stronger consumer controls.
This source-bound review and actual receiving evidence complete the narrow
local-CI specialization assessment requested by [issue #30][quality-issue].
No profile change, new exception or human approval dependency is introduced.

The manifest still describes `ci.yml` delivery as
`thin_immutable_reusable_workflow_call`; the actual consumer implements local
jobs. This is a reviewed specialization, not exact reusable-call conformance.
The [shared Node workflow][shared-node] executes repository tests and Codecov
OIDC upload in one job without explicit report selection. Blind substitution
would lose the consumer's stronger upload boundary. Future reusable adoption
requires a focused central adaptation preserving that boundary and stable
required checks, not a forced profile migration in this repair.

Portable [verification-receipt schema][portable-receipt] compatibility is
separate from the validity of the retained component evidence. The receiving
Conductor follow-up owns its aggregate export and exact-source binding.
The [one-command harness recommendation][quick-harness] remains an optional
integration improvement, not an added merge gate; no new generic harness is
introduced by this accepted implementation increment.

### Retained limits

All other registry fields and all other repository entries retain their values.
The existing profile, supply-chain selection, zero-approval policy and empty
exception list are preserved. Renovate installation and historical merged
updates do not establish a new updater completing the saved protection rules
or handover for every ecosystem. The GitHub Actions Dependabot manifest and
`removal_gate: "Renovate first successful run"` remain unchanged. No artificial
version bump is needed to manufacture lifecycle evidence.

The offline-security image, assigned runner and actual execution remain gated.
The prior failures and assessments, F01 live acceptance, F03 apply-mode limits,
source/methodology reviews, broader migration and release obligations remain
separate. Main's PR-only dependency review was skipped by applicability;
queued offline work is not counted as passing.

[corrective-pr]: https://github.com/edithatogo/standards_check/pull/107
[corrective-main]: https://github.com/edithatogo/standards_check/commit/dd3f995c473db0cc1cd6dad9d392b3744166958b
[corrective-assurance]: https://github.com/edithatogo/standards_check/actions/runs/45106620582
[corrective-python]: https://github.com/edithatogo/standards_check/actions/runs/45106620582/job/137469276587
[corrective-rust]: https://github.com/edithatogo/standards_check/actions/runs/45106620582/job/137469276491
[corrective-api]: https://github.com/edithatogo/standards_check/actions/runs/45106620582/job/137469276443
[corrective-python-upload]: https://github.com/edithatogo/standards_check/actions/runs/45106620582/job/137469891138
[corrective-rust-upload]: https://github.com/edithatogo/standards_check/actions/runs/45106620582/job/137469891156
[corrective-api-upload]: https://github.com/edithatogo/standards_check/actions/runs/45106620582/job/137469891135
[corrective-status]: https://api.github.com/repos/edithatogo/standards_check/commits/dd3f995c473db0cc1cd6dad9d392b3744166958b/status
[corrective-codecov]: https://app.codecov.io/gh/edithatogo/standards_check/commit/dd3f995c473db0cc1cd6dad9d392b3744166958b
[receiving-ruleset]: https://github.com/edithatogo/standards_check/rules/27871801
[path-alert-five]: https://github.com/edithatogo/standards_check/security/code-scanning/5
[path-alert-six]: https://github.com/edithatogo/standards_check/security/code-scanning/6
[classification-schema]: https://github.com/edithatogo/repository-standards/blob/2efdbd988064f6857795b9fa9ed4e1d08d18791d/schemas/repository-entry.schema.json#L57
[lifecycle-standard]: https://github.com/edithatogo/repository-standards/blob/2efdbd988064f6857795b9fa9ed4e1d08d18791d/docs/continuous-conformance-standard.md#L87
[receiving-readme]: https://github.com/edithatogo/standards_check/blob/dd3f995c473db0cc1cd6dad9d392b3744166958b/README.md
[receiving-profile]: https://github.com/edithatogo/repository-standards/blob/2efdbd988064f6857795b9fa9ed4e1d08d18791d/profiles/archetype-profiles.json#L81
[receiving-managed]: https://github.com/edithatogo/repository-standards/blob/2efdbd988064f6857795b9fa9ed4e1d08d18791d/managed-files/manifest.json#L91
[conflict-route]: https://github.com/edithatogo/repository-standards/blob/2efdbd988064f6857795b9fa9ed4e1d08d18791d/docs/continuous-conformance-standard.md#L46
[stronger-controls]: https://github.com/edithatogo/repository-standards/blob/2efdbd988064f6857795b9fa9ed4e1d08d18791d/conductor/tracks/frontier_02_enforcement_20261113/spec.md#L4
[shared-node]: https://github.com/edithatogo/repository-standards/blob/2efdbd988064f6857795b9fa9ed4e1d08d18791d/.github/workflows/node-ci.yml
[portable-receipt]: https://github.com/edithatogo/repository-standards/blob/2efdbd988064f6857795b9fa9ed4e1d08d18791d/schemas/verification-receipt.schema.json
[quick-harness]: https://github.com/edithatogo/repository-standards/blob/2efdbd988064f6857795b9fa9ed4e1d08d18791d/docs/continuous-conformance-standard.md#L62
