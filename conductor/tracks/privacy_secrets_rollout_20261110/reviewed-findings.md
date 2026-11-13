# Bounded reviewed-finding follow-through

Status: implementation and local verification; publication and consumer adoption pending.

The initial rollout exposed two false positives in a public repository's exact
workflow-publication inventory. Independent review established that both matched
values are Git blob identifiers, recomputed from public object bytes, for the
qualified privacy workflow. The [registry](../../../privacy/reviewed-findings.json)
records the immutable finding identities and public evidence. Native repository
scanner handling remains separate.

Owned paths: `scripts/secrets_scan.py`, `tests/test_secrets_scan.py`,
`privacy/reviewed-findings.json`, `privacy/reviewed-findings.md`, the shared
privacy standard, and this track's index/follow-through note. This slice changes
no Presidio recognizer, upstream Gitleaks rule, consumer pin, target ignore
configuration or rollout status.

The [review process](../../../privacy/reviewed-findings.md) requires exact
commit/path/rule/line/value-digest matching and a trusted-source registry.
Malformed or ambiguous metadata fails closed. Staged and unmatched findings
continue blocking. Raw match processing is confined to private temporary files;
public summaries expose counts and safe locations only.

Verification must include exact admission, every identity mismatch, malformed
and duplicate registry data, untrusted overrides, additional real findings,
actual CLI behavior, post-write file permissions and cleanup on failure. Run the
complete existing policy/privacy suites and preserve their actual outcomes.
Independent review is required before proposing publication; fresh hosted gates
and an explicit consuming pin change remain necessary before adoption.

## Local qualification

- The complete suite passed all 99 tests on Python 3.12.14 with real Presidio
  2.2.366 and Gitleaks 8.30.1, with no skips. This retains the existing 84 cases
  and adds 15 admission/privacy-boundary cases with further negative subcases.
- The repository's Python 3.15.1 policy suite passed 99 tests with 24 explicitly
  skipped Presidio cases; the separate supported tooling run supplies those results.
- Ruff check/format and Git whitespace checks passed. The previous pinned guard
  found zero secrets or supported personal identifiers in the staged source patch.
- Independent review accepted the exact-match model and public-object evidence.
  A separate seven-case harness verified actual error/timeout handling, malformed
  reports, unsafe modes/links, real Gitleaks permissions, safe output and cleanup.
- A real full-history scan of the affected public repository admitted exactly
  the two reviewed findings and still blocked an additional historical finding.
  That finding was not automatically imported from its native scanner policy.

These results qualify the local change only. Publication, new-head hosted checks,
consumer pin adoption and resolution of unrelated findings remain unclaimed.

## Native capsule follow-through — 14 November 2026

Chat `01a1d426-0c2d-7ed2-b91a-fa5f2e2c5372` owns the bounded public `tobac`
capsule finding repair in the isolated Git clone
`/Users/doughnut/Documents/repository-standards-privacy-20261114`, branch
`codex/tobac-privacy-fingerprint-20261114`, based on `592903c`.
The managed-worktree request stalled and Git readback showed this clean clone.
Owned paths are the reviewed-finding registry, its review note, the focused real
Gitleaks regression and this handoff. Next, reproduce the historical fingerprint,
verify its public source bytes, exercise a nearby credential control and publish
through the existing hosted gates. The consuming pin and signed receipt update
belong to this chat's separate `tobac` checkout.

The full-history secret scan reproduced six unmatched coordinates. Source review
verified the capsule workflow SHA-256, four `data-sitekey` occurrences in one
immutable HTML blob across two commits, and the release-scanner log digest.
Both retained original logs reproduce that digest. The trusted registry now
contains those six exact identities alongside its two previous entries. The
real full-history scanner reports six detected, six reviewed and zero blocking
findings. The qualified-hash regression still blocks a nearby hexadecimal API
credential, and both SHA-1 and SHA-256 admission controls pass.

Repo-local Python 3.15.2 passed the documented complete policy command, 109 tests
with 24 Presidio capability skips. The real Gitleaks cases executed. The shared
hosted scanner suite supplies supported Presidio execution. Active policy-tool
workflow defaults and current runtime guidance now select the qualified 3.15.2
patch. Those workflow declarations, `conductor/workflow.md` and
`conductor/tech-stack.md` are also owned by this slice. Hosted publication and
the consuming immutable pin are pending.
