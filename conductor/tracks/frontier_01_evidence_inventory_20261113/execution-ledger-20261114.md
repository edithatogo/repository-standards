# F01 execution ledger — 2026-11-14

Binding scope: the existing F01 specification and plan. Work is isolated from the
main branch; existing acceptance criteria are not weakened.

## Decisions

- Implement one bounded read-only live-evidence module and retain the older
  structural scanner for explicit private analysis. Replace the scheduled public
  detailed upload path with strictly schema-validated aggregates.
- No cron inference from API silence: missing scheduled execution remains unknown.
  The collector qualifies per-workflow API history, not a YAML-parser capability.
- Preserve historical audit files and compare explicit scopes rather than
  comparing 163 and 303 as though they had identical denominators.
- Keep private hosted rows ephemeral rather than placing them in publicly
  downloadable artifacts. Durable private retention requires a private store;
  the CLI supports an explicit private file for an operator-controlled run.
- No second-person approval, token creation, ruleset change or consumer rollout.

## Observed implementation verification

Local focused tests use Python 3.13.5; this environment cannot fetch a complete
Git checkout or install the repository's 3.15.2 toolchain. Only the newly authored
files are present locally. A full local repository-suite claim is not made.

Initial acceptance import failed before implementation. The first 37 tests then
passed. Review added failing counterexamples for unregistered exception policy,
malformed positive protection replies, duplicate unavailable IDs, stale inner
observations, baseline redaction and expiry across midnight; the fixes passed.
A final adversarial pass exposed and fixed stable-ID/name reuse, ambiguous
empty-repository conflicts, future run claims, owner/name disagreement, calendar
overflow and migration of the legacy generated issue section. Transport tests
verify bounded rate-limit retries and no off-origin credential redirects.
Current focused result: 62 tests passed, no skips. Separate schema/pipeline
qualification: four tests passed, no skips, using fastjsonschema 2.21.2.
Hosted full-suite and real inventory results remain separate acceptance gates.

## External evidence prerequisite

The previously inspected scheduled conformance run 42528581448 passed source
validation but failed at "Require an estate-readable token"; collection never
executed. The updated workflow retains ESTATE_AUDIT_TOKEN as the explicit credential
boundary. The proposed automatic installation-wide App fallback was removed
after the hosted Zizmor alert gate correctly flagged its scope. There is no
linter suppression, token creation or repository-token fallback. Credential
availability is not inferred merely from the workflow definition. F01 must remain open if current live
execution cannot enumerate the authenticated scope.

## Remaining acceptance at this checkpoint

Publish source and schema changes in a PR, inspect exact-head CI/security results,
merge only after they pass, execute/read the main-branch live collection and public
publication, then reconcile the track using actual receipts. No full-track
completion or archive is claimed by this source checkpoint.

## Hosted review repair

At initial head 486bd46c56a3d00140b4f05c642869caebe707f6 the workflow jobs
succeeded, but the separate Zizmor alert gate failed for an implicit
installation-wide App token. The fallback was withdrawn, not suppressed. Two
credential-boundary regression tests first failed, then passed after removal.
The updated local focused suite contains 64 passing tests; the four explicit
schema/pipeline tests also pass. Fresh hosted checks are required for this repair.
