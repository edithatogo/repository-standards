# Published candidates and outstanding acceptance

Checkpoint: 2026-11-15, Australia/Brisbane. The Python starter has merged after current-head checks; the other eight
changes remain draft review candidates at this checkpoint.

| Repository | Pull request | Published candidate |
| --- | --- | --- |
| `edithatogo/repository-standards` | [#144](https://github.com/edithatogo/repository-standards/pull/144) | See the current PR head; this record is part of that change |
| `edithatogo/.github` | [#9](https://github.com/edithatogo/.github/pull/9) | `52987aa2a6d9904a15e62226a02e02b72bca4cbd` |
| `edithatogo/template-solo-python` | [#9](https://github.com/edithatogo/template-solo-python/pull/9) | `45ebd00f9a81fc304925d4bde5d253a5e449a4a7` |
| `edithatogo/template-solo-rust` | [#7](https://github.com/edithatogo/template-solo-rust/pull/7) | `7fdb6a608b31f1c1d6a6874ba0d54d554258cbff` |
| `edithatogo/template-solo-node` | [#9](https://github.com/edithatogo/template-solo-node/pull/9) | `36786d6bce3754e05a7c196a18173339ccb945be` |
| `edithatogo/template-solo-data` | [#9](https://github.com/edithatogo/template-solo-data/pull/9) | `21aa11074dac12bdff2a03933f28249eb394510a` |
| `edithatogo/template-solo-docs` | [#6](https://github.com/edithatogo/template-solo-docs/pull/6) | `76aac72dc1b6c45ff830c0d588177ae1f124041d` |
| `edithatogo/template-solo-latex` | [#7](https://github.com/edithatogo/template-solo-latex/pull/7) | `558bb523abf0e08fc9432908aff6caa1e93ae674` |
| `edithatogo/template-solo-typst` | [#8](https://github.com/edithatogo/template-solo-typst/pull/8) | `2882cf6e0898e5f3088ddaaa5866ff58282b0c4e` |

## Content preservation and review

The exact 15-file shared-default payload survived the executor interruption and
was published without reconstruction. Root and reviewer inspected the published
forms, policies and adoption guidance. Its
[privacy-and-secrets run](https://github.com/edithatogo/.github/actions/runs/43650401387/job/132617351209)
succeeded at the listed head.

The seven starter payloads were recovered from retained baselines and patch
records. All 56 published changed files were read back against the recovered
strings, and all 69 untouched baseline blobs were preserved. LaTeX and Typst then
received seven-line security-only follow-ups restoring existing typesetting
safeguards; the table records the superseding heads.

Current source inspection found valid applicability JSON, Makefile tab
indentation, balanced Markdown fences and 81 resolving repository-relative
document links. This inspection is separate from running Markdownlint, the
Python auditor, Git ignore matching or native toolchains.

The central root-owned contract/schema/documentation/CI files received independent
review. The validator's concrete malformed-input and instruction-fallback findings
are repaired with regression cases and the final 50-case behavioral suite has
executed successfully. Published content is read back after
changes; final head checks remain the integration gate.

## Outstanding execution

The recovered central source has now passed local Python 3.15.2 qualification
(274 selected, 240 passed, 34 existing optional capability skips) and four
schema/pipeline cases. Central and defaults snapshot audits passed. The final
hosted central checks remain required.

Python starter PR #9 passed both CI runs, privacy/secrets and Codecov's patch
check. Its PR job executed one test on Python 3.15.1, generated coverage and
completed an OIDC upload. It merged as `126d23c1f4c0e020fba87fb0ddfa5f3cbdb81d5d`.
The remaining starter heads still require their own current checks. The
[execution plan](plan.md) preserves earlier historical evidence separately.

Before merging, inspect each current head's required and applicable checks,
resolve any finding, re-read the PR head, and use an expected-head merge lease.
The account-default README relies on the central auditor, so integrate the
qualified central source before its shared guidance.

The current scope is nine repositories. Existing issue bodies
[#10](https://github.com/edithatogo/repository-standards/issues/10),
[#18](https://github.com/edithatogo/repository-standards/issues/18) and
[#40](https://github.com/edithatogo/repository-standards/issues/40) have bounded
reconciliation sections and remain open. In particular, #40's old missing-file
observation is historical: those root files already existed on inspected main;
this increment improves their substance.

Do not merge unrelated PRs, overwrite concurrent local PR templates, activate
F03 apply mode, or promote F01 live or whole-estate acceptance from these
candidate checks.
