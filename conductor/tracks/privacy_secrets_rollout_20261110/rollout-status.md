# Rollout checkpoint

Observed at 2026-11-10T08:09:07+00:00. This is a dated checkpoint, not a claim of completed
estate-wide deployment. Per-repository records and private identities are kept
out of this public repository.

## Verified shared implementation

- Source PR #122 merged at `985503bc8eae58e7d6ef36a6e5427d0077e0193c`.
- Managed consumer PR #123 merged at `5fd6efc1953ad18ff01a29e3da7597387253f114`.
- Source behavioral tests and hosted canary, CodeQL, policy and workflow lint
  passed before source merge. The managed consumer, policy-gate, validate-policy,
  Python/actions CodeQL and Zizmor checks passed before PR #123 merged.
- Real local detector/policy verification comprised 84 tests. Consumer-specific
  execution is tracked separately from those source tests.

## Repository reconciliation

| State | Count |
| --- | ---: |
| Inventoried | 303 |
| Active | 277 |
| Default-branch workflow installed and read back | 41 |
| Open consumer PR | 234 |
| Prepared branch, PR creation denied by integration | 2 |
| Archived, preserved unchanged | 26 |

Every active repository has a prepared workflow change. Two initially empty
repositories received an initial default-branch commit. The other installations
use PRs and the repository's merge rules. Prepared PRs are not counted as installed.
The two PR creation denials reported HTTP 403, Resource not accessible by
integration; prepared branches were retained and the denials were not bypassed.

## Execution and remaining gates

Successful new privacy jobs, queued jobs, and failed jobs are recorded separately.
At this checkpoint, 68 new privacy jobs were observed successful.
Private startup failures with an empty step list and no runner are classified as
not executed. The available metadata does not identify their underlying hosting
cause; no billing, quota or policy cause is asserted. Existing required CI and
security failures remain binding. No branch protection or approval requirement
was weakened.

After the source tests and dozens of successful receiving canaries, exact
baseline-only additions may be installed while a receiving job is queued or
refused before runner startup, provided no native or instruction-defined gate
blocks the merge. This qualifies the configuration, not its execution. The
actual job status is retained; no unexecuted scan is recorded as passed. A
privacy failure after scanner execution remains a hold pending diagnosis.

Repository-specific formatting, runtime-contract and logging incompatibilities
are repaired on their existing PRs. The supported scanner runtime exception is
limited to isolated tooling and preserves product interpreter requirements.
A history-policy mistake in one public receiving repository was repaired with
an additive merge preserving the original feature commit, the historical squash
and the unchanged tree; no history was rewritten or branch deleted.

## Coverage and acceptance limits

Installation PR checks scan the submitted change. They do not prove that all
existing files and historical commits are clear. Weekly and manual full audits
are configured after installation. Presidio coverage, unsupported files and
local hook installation limits are stated in the shared standard. Local hooks
were not installed in developers' separate clones. Existing branch settings were
preserved, so a failed workflow is a required merge gate only where native rules
require it.

The track remains in progress while receiving PRs, repository checks and external
execution gates remain unresolved. Later private reconciliation snapshots may
show additional deployments beyond this checkpoint.
