# Evidence-grade estate inventory (F01)

The live evidence collector is `scripts/estate_evidence.py`. It is not a policy
writer or an enforcement certificate. A successful collection means the reported
credential-visible inventory was enumerated consistently; it does not mean all
repositories passed all controls.

## Scope and identity

Discovery includes owned public/private, forked, archived, disabled and empty
repositories. Two paginated enumerations must agree on stable IDs and scope
metadata. This is an observation window, not an atomic GitHub database snapshot;
`generated_at` is the collection start and its conservative freshness origin. The collector detects duplicate/conflicting identities, missing totals,
partial API responses, repeated pages, page/request budgets and inventory drift.
It records the credential surface: authenticated-owned, installation-accessible
owned, or public-only fallback. A public-only fallback is always partial. The
number of repositories invisible to the credential remains unknown, never zero.

The historical registry is reconciled by repository ID where available, then name
and same-origin alias resolution. Renames do not create a new identity; a recreated name cannot inherit a known
older repository ID or its exception policy; a 403 or
ambiguous 404 is unavailable, not proof of deletion. Newly registered and newly
created are separate quantities. No lifecycle or visibility setting is changed.

## Evidence semantics

Every private observation records state, assurance level, observation time,
source commit, run/check identity when available, evidence time and bounded
structured details. States are pass, fail, unknown, stale and not_applicable.
Configuration presence, execution evidence and enforcement are separate. This
collector never emits a successful enforcement claim.

The exact default-branch head is read before and after collection. If it moves or
becomes unreadable, current-commit claims are revoked. Latest check runs and
legacy statuses are reconciled per producer/context; incomplete collections,
missing required contexts and nonterminal/neutral/skipped/cancelled results cannot
pass. The current-CI result is limited to observed checks, not all possible merge
requirements or downstream consumers.

Scheduled execution is queried separately for every active workflow, on the
default branch, without filtering to completed or successful runs. The latest
scheduled run is bound to its own source commit and run ID. A missing run is
unknown, not evidence that a schedule is absent. This API-history contract does
not parse YAML or assert that every configured cron has been enumerated.

Run evidence expires after eight days. Snapshot freshness is at most 24 hours and
is shortened when an active policy exception reaches its expiry boundary.
Exception dates are evaluated at observation time, not module import. Unregistered
exception policy is unknown, not an empty clean policy. Expired/invalid exceptions
are reported; no exception suppresses an observation.

## Privacy, schemas and provenance

`schemas/estate-evidence.schema.json` describes private evidence.
`schemas/estate-evidence-public.schema.json` rejects identities, arbitrary
properties and raw API errors in public output. Both use draft-07. The isolated
validator wheel is hash-pinned in `tooling/estate-evidence-requirements.txt`;
consumer product dependencies are unaffected. Semantic validators additionally
reject duplicate IDs, stale/future envelopes, unsupported execution claims,
wrong-commit claims and inconsistent aggregate denominators.

Private output is an explicit mode-0600 exclusive-create file outside the public
output directory. It is never logged or uploaded by hosted CI, and is removed at
job exit. Operators needing durable private evidence can retain that file in an
access-controlled local evidence store. Hosted public artifacts retain only the
allowlisted aggregate JSON/Markdown and checksums for 90 days; no private
per-repository hashes or paths are published. A digest binds the full private
snapshot without exposing its rows. Source commit/run, interpreter and input
hashes identify the implementation and registry actually used. The aggregate
artifact receives GitHub provenance; a checksum alone is not an authenticity claim.

## Historical reconciliation

The July 2026 audit's 163-repository active/non-fork scope and November privacy
checkpoint's 303 total repositories have different denominators. The original
files remain untouched. Their timestamps, counts and input hashes are carried as
historical evidence, alongside current scope-aligned totals. No cross-scope
compliance trend or deployment percentage is inferred from them.

## Execution and publication

The scheduled Estate conformance workflow now runs the evidence collector, not a
static-registry-only report with detailed public uploads. Existing structural
policy scanner, impact simulation, remediation planner and bundle exporter remain
available for explicit private analysis; they are not silently presented as fresh
live-estate evidence. Managed remediation remains separately gated and plan-only.

The workflow uses Python 3.15.2. Credentialed collection runs only from main, never
from a pull request. It accepts the existing `ESTATE_AUDIT_TOKEN`, or the configured
short-lived estate App (`ESTATE_AUTOMATION_APP_ID` and its private-key secret).
Missing credentials fail closed; the repository-scoped default token is not used
as a substitute for estate access. No token value is printed or persisted.

A separate least-privilege publisher validates the fresh, complete public receipt
and updates one bounded section of existing issue 16 (or the configured issue
number). Partial/stale evidence cannot replace that section. It creates no new
issues, preserves surrounding notes, rejects ambiguous markers and is idempotent
for an identical receipt. Live workflows are serialized. An existing bounded legacy generated section is replaced with the aggregate
section; owner notes outside generated sections are not rewritten.

## Verification and rollout

The ordinary unittest suite includes F01 pagination, scope, identity, freshness,
protection, exception, privacy and publication counterexamples. The workflow also
executes `tests/evidence_schema_acceptance.py` with the isolated validator: schemas,
private-field rejection, historical preservation and a complete synthetic pipeline.
Synthetic qualification is not live-estate acceptance. Close F01 only after the
source PR, hosted canary and authenticated inventory/publication evidence are
verified at their actual source revisions. No completion flag is inferred from a
queued job or a passing fixture suite.
