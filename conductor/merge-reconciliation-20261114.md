# Sequential PR reconciliation — 2026-11-14

## Scope and claim boundary

This checkpoint records seven code/test PRs merged sequentially, followed by a
separate documentation reconciliation PR. It is not completion of the PR backlog,
a fresh estate inventory, consumer deployment, or frontier certification.

Starting main: `592903c99291b5efe08f4134517914f4ee1a262e`.
Main after the seven merges, before this documentation change:
`5c4881b2cb146ec3e55e9a90fbc3116407da96f5`.

The already-merged programme (#127), F01 protection-evidence fix (#128), and Rust
dependency inventory (#131) were preserved. #128 was not merged again in this batch.

## Merged changes

Each merge used the repository's squash method and an expected-head guard.
Branch reconciliation retained original ancestry without force-push. The observed
policy/privacy/workflow-security runs and the separate CodeQL alert gate passed
at each listed head; review comments record the checked scope and limitations.

| PR | Change | Verified head | Merge commit |
| --- | --- | --- | --- |
| [#130](https://github.com/edithatogo/repository-standards/pull/130) | Readable container-produced LaTeX PDF before existing validation | `4cf702201b70b5ee8a9f6ed1939cbdfe131aa78a` | `6e2d5e55f7b1af8d6a0e7ccc34202661573dac58` |
| [#77](https://github.com/edithatogo/repository-standards/pull/77) | Badge-state regression tests | `834a402af3463cfa006b2e071bcc94f987edea7f` | `b91e8d4c51f59eb6813e35b65e6fcdd58904f8ef` |
| [#78](https://github.com/edithatogo/repository-standards/pull/78) | Missing/malformed exception-date expiry tests | `4a64fc2e44a72467ec37d94f8bbbe14197258a70` | `e136074e394efcafa7c5f5559a4fe7bd67db0505` |
| [#84](https://github.com/edithatogo/repository-standards/pull/84) | Invalid exceptions cannot become active | `46ed80452e2d169f5ae340744ab17f11eef3f4e5` | `b56ac69789cea7450367ccb0e7eda395f14776ee` |
| [#87](https://github.com/edithatogo/repository-standards/pull/87) | Pass candidate_limit as quoted environment data, not shell source | `587f486c53fe797dd407b719ddaad9c4192e037c` | `3b2932c66488feb2b5e0380587be0adbefa740f1` |
| [#79](https://github.com/edithatogo/repository-standards/pull/79) | Archetype tests, incorporating distinct #83 cases without replacing badge tests | `c2f5fdbf85b60b4b992e76d25b859e96ecf26582` | `367ee2f8c055eaa293ab6a37320aa5b5ba4dca87` |
| [#99](https://github.com/edithatogo/repository-standards/pull/99) | Version/citation-drift regressions in a separate test module | `7809f61aed3a0ddb9e098874b0cb0312b91fcbaa` | `5c4881b2cb146ec3e55e9a90fbc3116407da96f5` |

Policy run identifiers, in the same order: `43342294342`, `43315450637`,
`43530368927`, `43530739498`, `43531136418`, `43531835426`, `43532285196`.
Complete seven-check listings were additionally inspected for #130 and #99,
including both CodeQL language analyses and the Zizmor/CodeQL alert results.
A successful analysis job is not substituted for a successful alert gate.

## Integration evidence and limits

The [#99 policy job](https://github.com/edithatogo/repository-standards/actions/runs/43532285196/job/132252691170)
checked out merge ref `5c81b38198c69a39e485896948a19871d791d7ee`, combining the
listed head with main `367ee2f8c055eaa293ab6a37320aa5b5ba4dca87`.
It used Python 3.15.1 and ran JSON validation, scientific policy validation,
compileall, and the documented unittest discovery command.

Observed result: **137 tests discovered; 105 passed, 32 skipped, zero failures**.
The 32 skips are the existing isolated Presidio/Gitleaks integration cases in the
policy lane. They are not counted as passes. The separate Privacy and secrets
workflow passed, but that does not mean these skipped integration tests executed.
An existing HTTPError ResourceWarning was visible; warning-free execution is not
claimed. Full local repository tests were not run during this reconciliation.

A targeted local Bash canary for #87 reproduced command substitution under direct
interpolation, then verified literal preservation of a normal value and two
adversarial scalar values with quoted environment expansion. This is not a live
GitHub App or estate-remediation run. The apply=true refusal remains unchanged.
Moving an arbitrary command into an environment variable and evaluating it does
not create a safe data boundary; command-valued workflow inputs need their own
explicit trust contract.

For #130 the Codex review bot was quota-blocked. That was not counted as a
successful independent review: the separate diff review and automated security
checks were recorded instead. No downstream LaTeX consumer build is claimed here.

## Reconciliation repairs

- Removed three generated .pyc files from #84's proposed tree.
- Excluded incidental pr_description.md from #87 and diff.txt from #99.
- Preserved #77's badge module while moving archetype and version tests to
  tests/test_metadata_archetype.py and tests/test_metadata_version.py.
- Retained #128's protection-state and fail-fast regression tests.
- Replaced #99's unused application fixture classification with actual
  software/typesetting classifications, and exercised all three nonsoftware
  fallback kinds. Its PR description no longer claims exhaustive coverage.

[#110](https://github.com/edithatogo/repository-standards/pull/110) was closed as
superseded after its patch became empty and #78 supplied the specified coverage.
[#83](https://github.com/edithatogo/repository-standards/pull/83) was closed after
its distinct cases were retained in #79; its extra *.pyc ignore was already covered
by *.py[cod]. These two PRs are **closed, not merged**. Their branches and history
were not deleted.

## Open gates and next work

[#126](https://github.com/edithatogo/repository-standards/pull/126) remains draft:
immutable tool-image qualification, models, actual scanner/agent integration,
Rust-rule coverage and immutable references remain prerequisites. Its existing
DO NOT MERGE boundary was preserved.

[#129](https://github.com/edithatogo/repository-standards/pull/129) remains draft.
Static review of head `61006adab16aa7b3f2994353841d8fe532689efe` found that
GraphQL errors-only responses can become empty metadata and partial data plus
errors can be consumed without an incomplete-evidence state. Add negative tests
and redacted fail-closed handling, reconcile the new test modules, and verify
exact-head security checks before promotion or transfer to #108. This finding
was recorded on the PR; no live estate reproduction is claimed.

Other older metadata/refactoring PRs remain subject to semantic-diff review,
non-duplicative test reconciliation and current-head checks. They are not assumed
safe or obsolete merely because another PR touches the same function.

## Conductor state

F01 is **in progress**: the first protection-evidence increment is merged and its
source CI has passed. Its complete inventory, evidence-schema/freshness,
partial-response, privacy-safe publication and estate acceptance gates remain
open. Track-level hosted-canary, estate-rollout and frontier-certification flags
remain false. F02–F07 are not marked complete by these supporting changes.

No branch protection, rulesets, token permissions, consumer deployments, releases
or archive settings were changed. Managed remediation remains plan-only. This
record's documentation PR requires its own fresh hosted checks before merging.
