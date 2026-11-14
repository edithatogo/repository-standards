# Sequential PR reconciliation — second batch, 2026-11-14

This continues the [first reconciliation](merge-reconciliation-20261114.md).
The batch contains three sequential code/test merges, one superseded closure,
three explicitly not-adopted closures, and a separate documentation PR.
It does not complete the PR backlog, F01, estate deployment or frontier qualification.

## Receiving baseline and preservation

Starting main was `ace139de05a8520eb98e7fcb0bf0db4952a67437`, not the older
first-batch head. Its newer Python 3.15.2 guidance, scanner qualifications,
workflow repairs and previously merged tests were retained. This batch did not
change the runtime, scanner policy, repository permissions or branch protection.

The candidate branches were held in draft while refreshed and verified. Their
original history was retained with additive commits and no force-push. The
candidates were stacked to exercise their combined code, but merges were performed
one at a time with the repository's squash method and an expected-head guard.

## Merged source changes

| PR | Scope | Verified head | Merge commit |
| --- | --- | --- | --- |
| [#80](https://github.com/edithatogo/repository-standards/pull/80) | Per-invocation profile cache with five qualification tests | `26626c222579b491cc79a4a89461cba205941c92` | `c5d242d0be40fe5db23c98a2b621cf66e71e58ba` |
| [#92](https://github.com/edithatogo/repository-standards/pull/92) | Separate manifest extraction from citation drift without changing outputs | `d512b1ab1bf6c551c0bab79f27976e2b0ebff819` | `b4f26f6bd216a455ac8b5f69a422c9c4d210e720` |
| [#107](https://github.com/edithatogo/repository-standards/pull/107) | Eight complementary metadata tests, retaining distinct #102 cases | `9e87a192372fb2042c3238362c36362925983954` | `bcd1a6e117c7b6c23474dd389e4d063da6ab116c` |

The #80 merge tree was `76b432fc151fd1a086a7c84f4d08e42ca0b1ecf6`, exactly
#92's construction base. The #92 merge tree was
`ddf1a38891ddde421c6a387cc46f6b5ba25086a5`, exactly #107's construction base.
The #107 merge tree was `f62989d83e6896ebe75c55eae34d9cdc146521ae`.
These read-backs confirm the sequential results preserve the tested combined
source, rather than relying only on stale PR base or synthetic-merge metadata.

#92 reused its reviewed source blob only after verifying its original base blob
`0ff840eb8b110c86445a608ba2f520cd9f988154` was identical to receiving main's
metadata source. No newer metadata implementation was overwritten.

## Hosted verification

All latest check runs were inspected: seven for #80 and eight each for #92/#107.
They completed successfully before merging, including policy, privacy, workflow
lint, both CodeQL language analyses and the separate CodeQL/Zizmor alert gates.
The additional metadata-audit workflow passed for #92/#107. A transient neutral
CodeQL result on #80 was not treated as success; it was rechecked after the Python
analysis finished. No inline review threads were returned for these three PRs.

| PR | Policy run | Privacy run | Workflow-security run | CodeQL analysis run |
| --- | --- | --- | --- | --- |
| #80 | 43543912651 | 43543912525 | 43543912551 | 43543907913 |
| #92 | 43544195928 | 43544196134 | 43544196053 | 43544191835 |
| #107 | 43544384177 | 43544384184 | 43544384119 | 43544378583 |

The inspected [#107 policy job](https://github.com/edithatogo/repository-standards/actions/runs/43544384177/job/132292103234)
checked out `3eff82dcdcf75d1e224b0c20de04ce9b76060895` and used **Python 3.15.2**.
JSON validation, scientific policy validation, compileall and documented unittest
discovery succeeded. Result: **152 tests discovered; 118 passed; 34 skipped;
zero failures**. The skips are 24 Presidio and 10 Gitleaks capability-dependent
integration tests in that policy lane. They are not counted as passes, and a
separate successful privacy scan does not prove that those skipped tests ran.
The existing HTTPError ResourceWarning remains visible; warning-free execution
is not claimed. These receipts concern the source candidates, not a fresh estate
inventory or the later documentation PR's own checks.

## Focused local qualification

The available local interpreter was Python 3.13.5, not the qualified 3.15.2 runtime.
A complete local repository checkout/suite was not available.

For #80, the original source copied from the connector matched Git blob
`d1caf167b921a4d36df9af3d66f62a69725b04ca`. The new cache-count test failed
against it (four resolutions, expected two), then all five tests passed with the
cache. The tests also cover per-repository findings, inherited overrides,
nonmutation, empty requirements/snapshots and reset on a later invocation.
No new wall-clock performance claim is made.

For #107, eight focused tests passed against extracted production pure functions.
This is deliberately narrower than full-module or hosted-runtime qualification.
The new module supplements the existing badge/archetype/version test modules:
Go/package markers, dynamic build requirements, quoted citation drift, realistic
badge URLs, mixed badge flags, text-only keywords and Markdown summaries remain
covered without replacing or duplicating the canonical modules.

## Closed without merge

[#102](https://github.com/edithatogo/repository-standards/pull/102) is **superseded**
by #107 plus the existing #77 empty-string coverage. Its distinct cases were
retained before closing; its extra *.pyc ignore is already covered by *.py[cod].

[#97](https://github.com/edithatogo/repository-standards/pull/97),
[#105](https://github.com/edithatogo/repository-standards/pull/105) and
[#106](https://github.com/edithatogo/repository-standards/pull/106) are **not adopted**,
not merged and not labelled as implemented. The audit modules directly use
urllib.error.HTTPError and urllib.error.URLError. Removing the explicit import
would merely rely on another module's import side effect, not correct an unused
dependency. #106 additionally proposed three generated bytecode files. Full
patches were reviewed and the rationale was recorded on each PR. Original
branches and history were preserved for all four closures.

## Remaining work and track state

The observed open-PR count after these seven dispositions, before creating this
documentation PR, was **25**. The queue still requires individual semantic review;
no remaining PR is assumed mergeable merely because another change passed.

The first batch's explicit holds on #126 and #129 remain unresolved by this batch.
The offline security profile still needs its real qualification gates; GraphQL
errors-only/partial-data handling still needs negative tests and fail-closed
handling before that repair is promoted. Metadata optimisation/refactoring PRs
must now preserve the #92 helper and the complementary #107 test module.

F01 remains **in progress**. None of F02–F07 is completed or archived by these
supporting changes. Managed remediation remains plan-only. There was no estate
rollout, publication, ruleset change, token-permission change or frontier
certification. This separate documentation PR must pass its own fresh checks.
