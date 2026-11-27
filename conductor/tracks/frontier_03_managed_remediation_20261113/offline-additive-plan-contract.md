# Offline additive plan contract — 27 November 2026

Refs [#192](https://github.com/edithatogo/repository-standards/issues/192) and
[#24](https://github.com/edithatogo/repository-standards/issues/24). Distinct
synthetic-only F03 source development. Do not alter the plan.md file owned by
open PR #196, the existing managed-remediation workflow, or the planner's
abstract candidate-discovery output. Keep apply mode disabled.

`scripts/remediation_plan_contract.py` specifies the decoded-object v1
contract for at most ten low-materiality additive changes, with no overwrite,
delete, rename, file execution or repository write. It binds exact SHA-1
source tree and target head, repository and owner, canonical UTC issue/expiry
times (24-hour maximum), and ordered target path/source blob pairs to the
SHA-256 digest of the canonical body excluding the key itself. The digest is
an exact-body idempotency key, not a signature. A reissued plan with a different
expiry requires future operation-level deduplication; no persistent ledger,
lock, actual retry or apply operation is implemented.

Independently supplied context must bind the target's complete leaf-path
inventory and allowlisted paths/exact source blob identities to the stated
tree/head. Missing completeness, stale identity, unauthorized path/blob,
modified key, invalid scope or expiry, existing target path and file-directory
or case-insensitive directory collisions hold. The combined inventory is
limited to 10,000 paths and conservative portable ASCII names of at most 240
characters; unsupported names fail closed rather than disappearing. Previously
recorded identical keys yield already_recorded only after current validation.
No live object acquisition, raw JSON trust-boundary parser, provenance
verification or permission checks are included. Caller-supplied context is not
a proof that a live snapshot was verified. Every result denies write authority.

Local TDD: initial missing-module failure; ten focused synthetic test methods
passed in Python 3.13.5. Three additional directory-spelling collision subcases
first reproduced false accepts, then passed after validating every prefix
spelling in the combined inventory. Hosted policy suite and independent review
remain required. No consumer canary, F01/F02 acceptance, live conflict replay,
new model inference, GitHub App write, merge automation or estate rollout.

The next safe engineering slice after source qualification is binding trusted
snapshot provenance, parser integrity and deduplication across independently
issued plans. Do not enable any writer or mark F03 complete from these tests.
