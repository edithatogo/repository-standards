# F01 acceptance record — 2026-11-14

## Decision

**Source implemented and validated; full track remains in progress.**
The first real main-branch execution failed at the explicit audit-credential
boundary. It is not evidence of an empty estate or a completed inventory.
No acceptance requirement has been waived, and the track is not archived.

## Delivered source

[PR #138](https://github.com/edithatogo/repository-standards/pull/138) merged
`cd2d527a776256c095c81969f98bb343428ba63f` as
`598730dbe4b3e3053f5538f74824a147f3e18b72`.
Tree: `da7f2f75dc6ae920243ff268fa0fa0e403ae8e5a`.

The collector covers stable-ID/name reconciliation, two-pass paginated scope
inventory, private/fork/archive/disabled/empty classifications, explicit unknown
states, exact-head checks, latest per-workflow scheduled history, protection
configuration, exception expiry, freshness, strict private/public schemas and
historical input hashes. The publisher accepts only fresh complete aggregate
receipts and updates one bounded existing issue section. Private rows are not
uploaded to public artifacts; missing credentials fail closed.

| Requirement | Source/fixture evidence | Live acceptance |
| --- | --- | --- |
| Account for accessible repositories exactly once | Pagination/duplicate/stable-ID/name-reuse tests passed | Not executed: credential unavailable |
| Explicit scope and historical denominator differences | 163/303 baseline fixtures, hashes and preserved inputs | Current totals not collected |
| Unavailable/failed/stale evidence cannot be passed | Permission, partial-response, head-change, forged-run and expiry tests passed | Not yet measured across estate |
| Typed, reproducible evidence and redacted public output | Both schemas, mode-0600 private file, aggregate allowlist, checksum and CLI pipeline tests passed | No live receipt produced |
| Bounded repeatable publication | Idempotency, stale/partial refusal and legacy-section migration tests passed | Attestation/publication skipped |

## Hosted source qualification

[Estate conformance run 43551028491](https://github.com/edithatogo/repository-standards/actions/runs/43551028491)
job `132313266066` checked out synthetic merge
`e75c1cca3e9459c8f15c5be46f91065a920d8b9c` using Python **3.15.2**.
Hash-pinned schema tooling, JSON checks, compileall and full unittest discovery
passed: **216 discovered, 182 passed, 34 skipped, zero failures**. The skips are
24 Presidio and 10 Gitleaks capability-dependent integration tests in this lane,
not passes. The four explicit schema/pipeline cases also passed without skips.
An existing HTTPError ResourceWarning was visible; warning-free execution is not
claimed. The separate privacy workflow passed, not a substitute for skipped tests.

All ten current-head check records were inspected: eight successful source/security
checks and two intentionally skipped main-only live jobs. CodeQL Python/Actions
analyses and separate CodeQL/Zizmor alert gates passed. The initial App-token
scope alert was repaired by removing automatic installation-wide token minting;
no rule suppression or default repository-token fallback was added.

Local new-code-only verification used Python 3.13.5: 64 focused tests plus four
schema/pipeline cases passed. This local result is not a full checkout or the
qualified 3.15.2 runtime. Red/green counterexamples and review repairs are detailed
in [the execution ledger](execution-ledger-20261114.md).

## Actual main-branch execution and blocker

[Live run 43551271365](https://github.com/edithatogo/repository-standards/actions/runs/43551271365)
used source `598730dbe4b3e3053f5538f74824a147f3e18b72`.
Validation job `132314027287` passed. Collection job `132314093289` received an
empty ESTATE_AUDIT_TOKEN and emitted the fixed error code
`estate_credential_unavailable`, exiting **2** at **2026-11-14T03:22:31Z**.
Collection stopped before API enumeration. Attestation and issue-publication jobs
were skipped. The upload step warned that no files existed; an artifact listing
confirmed **zero artifacts**. Existing issue contents were not replaced.

This observation establishes credential unavailability to this workflow, not
whether a secret with that name exists elsewhere or why access is unavailable.
No secret value was retrieved or requested through chat.

## Unblocking and final acceptance

The repository owner must securely make a dedicated estate-readable credential
available to this main-branch Actions job under `ESTATE_AUDIT_TOKEN`. Select the
intended owned-repository scope, including private repositories where applicable;
read-only metadata/content, Actions, Checks and Commit statuses are needed for
the respective evidence endpoints. Branch-protection reads additionally need
Administration read permission; unavailable protection reads remain unknown,
not silently certified. The collector requires no repository write permission.
Do not grant write access merely to turn an unavailable read green.

After secure configuration, run **Estate conformance** on main, inspect the
credential-scope completeness and unavailable-identity accounting, validate the
public receipt and its source/run/input hashes, verify actual artifact attestation
and bounded issue publication, and reconcile these receipts into track metadata.
Only then mark full acceptance and archive F01. Until then, source qualification
is true but live inventory, hosted live canary, publication and track completion
remain false. F02-F07 are unaffected.

Permission references: GitHub REST documentation for [check runs](https://docs.github.com/en/rest/checks/runs),
[commit statuses](https://docs.github.com/en/rest/commits/statuses), and
[protected branches](https://docs.github.com/en/rest/branches/branch-protection).
