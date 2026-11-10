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
