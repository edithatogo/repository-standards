# Plan and evidence

## 1. Inventory and design

- [x] Enumerate the owner's accessible repository inventory.
  Evidence: 303 total, 277 active, 26 archived, 101 private as observed 2026-11-10.
  These counts do not establish deployment or execution.
- [x] Inspect existing shared standards, security workflows and root instructions.
  Preserve existing controls and private evidence; do not publish the inventory.
- [x] Select one shared immutable-pinned action with upstream Gitleaks and Presidio.
  The standard states the Python 3.12 tooling compatibility exception and coverage.

## 2. Implement and verify shared tooling

- [x] Implement the trusted scanner wrappers, isolated environment, hashed lock,
  verified binary installer and safe reporting.
- [x] Pin the managed consumer workflow to shared action `985503bc8eae58e7d6ef36a6e5427d0077e0193c`.
- [x] Prove actual detection and failure behavior: staged/index content,
  introduced/deleted secrets, identifiers, malformed Git ranges, import/path
  isolation, invalid checksums, unavailable tools and safe output.
- [x] Document profiles, coverage gaps, hook commands, maintenance and rollback.
- [x] Run the relevant local behavioral suite and workflow/static checks.
  Evidence: 84 unittest tests passed on Python 3.12.14 with real Presidio 2.2.366
  and Gitleaks 8.30.1; Ruff and targeted Zizmor passed. Staged guard results
  are recorded in verification.md.
- [x] Publish the shared implementation and verify its hosted test result.
  PR #122 merged after hosted canary, behavioral tests, policy-gate, CodeQL,
  Analyze (Python/actions) and Zizmor all passed on commit `992a80791c7debab851a684ba314734a843052e7`.

## 3. Canary and rollout

- [x] Verify the full shared composite action in the hosted source canary.
- [~] Verify receiving repositories using the immutable published action pin.
- [x] Prepare additive consumer changes against fresh branch heads.
  Evidence: all 277 active repositories have an initial workflow commit, PR,
  or prepared branch with an explicit PR-permission refusal.
- [~] Open scoped PRs and install the qualified baseline where existing required
  checks and repository instructions permit it. Source tests, hosted canaries and
  exact workflow review qualify installation when a receiving job is queued or
  refused before runner startup; record that execution as unverified. Executed
  privacy failures and binding CI/security/review/local-validation gates remain
  holds. Resolve genuine rollout faults without weakening those gates.
- [ ] Verify each receiving default-branch file and its shared-action pin.
- [ ] Record execution results separately from configured workflows, including
  disabled Actions, fork restrictions, quota refusal and schedule suspension.
- [ ] Reconcile every active repository to deployed or an explicit blocker.
- [ ] Record archived repositories as pending separate handling; preserve state.

## 4. Review and reconciliation

- [ ] Review final diff, trusted/untrusted boundaries and public evidence hygiene.
- [ ] Record aggregate configured/executed/blocked counts with immutable commit
  evidence. Keep private names, paths, PR URLs and source content out of this repo.
- [ ] Update metadata and registry without calling unexecuted scans successful.
- [ ] Complete this implementation track only after acceptance criteria are met;
  unresolved external execution gates remain explicit, not silently closed.

## Current evidence limits

The published shared implementation and its managed consumer both passed their
hosted checks and are merged. All active repositories have a prepared change;
receiving repository installation and execution remain in progress. See
[the dated rollout checkpoint](rollout-status.md) for aggregate evidence.
Prepared changes, successful scans and installed default-branch workflows are
separate states. The full repository audit remains private.

## Python 3.15.1 action maintenance snapshot — 16 November 2026

Owner: chat `01a1aa8f-ba44-78f1-a79b-e14bd3e07236`; isolated checkout
`/Users/doughnut/.codex/worktrees/gma-privacy-standards-20261116`, branch
`codex/privacy-action-3151-notice`, based on the qualified Python 3.15.1 action
commit `a5e25796939e43b81141f5cd0b55400377421a58`. Scope is the shared action
and its build evidence for a Global Medicines Atlas CI repair; it does not
change this repository's current default branch or publish a release.

- [x] Backport the Presidio MIT notice retention and reproducible build inputs
  from the later qualified Python 3.15.2 implementation in PR #148, preserving
  the 3.15.1 runtime, scanner logic, dependency locks and detection policy.
- [x] Build and install the real scanners on Python 3.15.1. Verify the notice
  digest inside both rebuilt Presidio wheels and run 35 privacy and 35 Gitleaks
  tests, including four focused notice regressions. An advisory lookup covered
  all 55 installed identities after mapping the two compatibility versions to
  their exact upstream sources; no known vulnerabilities were reported. The
  first lookup skipped those two due to name normalization and was repeated.
- [~] Verify the exact source commit in the hosted action canary and retain a
  receiving-repository audit without suppressions. A version tag and any public
  release remain a separate maintainer decision.

Only the action subpath and its pinned source dependencies are proposed for this
maintenance snapshot; inherited rollout templates are historical and do not
authorize the older Python 3.12 tooling in a new consumer. No participant or
cohort-derived data, data acquisition, dataset publication or messages are in
scope.
