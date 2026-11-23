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
