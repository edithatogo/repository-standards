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
- [~] Prepare additive consumer changes against fresh branch heads.
- [ ] Open scoped PRs and merge only after the new check succeeds and existing
  required checks allow it. Resolve genuine rollout faults without weakening gates.
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

The inventory and shared implementation are complete, and the published source
passed the hosted canary and all required checks. Receiving repository rollout
is in progress. Six receiving default branches have been merged and their files
read back with the expected pin at this checkpoint. Other PRs are pending checks,
repository permissions or rules. Some private-repository jobs fail before a runner
starts; this does not establish a scanner result or its cause. A configured check
and a qualified execution are different states. The authoritative per-repository
audit remains private; this public record contains aggregate evidence only.
