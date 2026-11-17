# Plan and evidence

## Innovate alert 44 review candidate — 17 November 2026

Chat `01a1e448-3a28-7653-a681-cd3fdb41f498` owns the isolated clone
`/Volumes/PortableSSD/GitHub/repository-standards-innovate44`, branch
`codex/innovate-alert44-privacy`, based on
`dd3a6d89a89a59fd1fcb231382a0dddbb868d363`. Its bounded candidate may change
the exact privacy-review registry and review note, focused scanner tests and this
plan. Native and authentication scope: none. Shared-repository integration and
Innovate promotion remain with their existing integrators. The next operation is
to verify the three reported spans against the immutable upstream matrix fixture,
test a nearby unreviewed financial identifier with the real recognizer, and run
the policy and hosted scanner gates. A registry entry or local result alone does
not establish a clean receiving scan or close the release and offline gates.

The source fixture's Git blob and SHA-256 were checked against Innovate commit
`3337f6f3c4efbe534be6edebbe34bcee0580dc51` and the original faer revision.
Each recognized span crosses the sign between real and imaginary coefficient
components. The real Presidio recognizer finds three blocking matches before
the exact reviews and three reviewed matches afterward; the sensitive profile
continues to block. A neighboring synthetic payment-test value still blocks.
On the Innovate changed-file range, the candidate scanner examined 760 of 760
selected files, with zero blocking, three reviewed and 1,145 advisory matches;
no files were skipped. The separate Gitleaks range scan reported zero findings.
These are local candidate results, not a receiving hosted scan.

The repo-local Python 3.15.2 policy suite passed 293 tests with 26 Presidio
capability skips; the separate real-Presidio suite passed 46 tests with no skips,
and the real-Gitleaks suite passed 39. The first policy run failed on macOS's
symlinked default temporary path (83 errors, two failures); 50 affected tests and
the complete suite passed after selecting a real repo-local temporary directory.
Network timeouts prevented a fresh Gitleaks download and the policy wheel fetch.
The run used a retained checksum-verified Gitleaks 8.30.1 binary read-only
(current SHA-256 `ba52fb1bfabbcde42f032afad3d6e0b19dff8ed105229a16e7caa338bbc0e84f`),
17 RECORD-verified files from an earlier hash-locked fastjsonschema 2.21.2
installation, and the candidate's source-verified PyYAML wheel. No other
environment was modified. Hosted scanner and canary checks, independent review,
the Innovate pin update and its actual receiving scan remain open.

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
