# Execution plan — Bounded GitHub App remediation control plane

## Incremental deliverables
1. Formalise an immutable plan schema: source tree SHA, destination head SHA, allowlisted paths, owners, materiality tier, expected diff, TTL and idempotency key.
2. Implement preflight conflict detection, diff/collision tests, dry run as default, rate limits, bounded batches and per-repo locks.
3. Exercise a disposable canary repository with happy path, stale base, protected branch, token denial, runner unavailable, dependency check failure, 429, repeat apply and safe rollback.
4. Create PRs only for additive low-risk managed changes; preserve local context and route semantic conflicts to issues.
5. Gate auto-merge on exact-head required checks, immutable pins and permissions; do not bypass native policies; record receipts and deterministic recovery.

## Implementation loop and review
For every numbered increment: define fixtures and negative controls, demonstrate failing tests, implement the minimum coherent change, run focused and full policy checks, perform independent automated security/behavioral review, fix findings, then verify hosted canary and exact-commit evidence. Update track status only after evidence; archive only after documented acceptance. Use scoped PRs, never force-push or bypass required checks.

## Owned paths (initial candidates; reconcile before edits)
- `.github/workflows/managed-remediation.yml`
- `scripts/plan_managed_remediation.py`
- `managed-files/manifest.json`

## Release gate
Apply mode initially fails closed; canary acceptance proves no direct-to-main writes, no loss of local changes, no duplicate PRs, no privilege escalation and safe idempotent retry. Live rollout proceeds only after passing independent checks.

## Blockers and recovery
API forbidden, unsupported entitlement, unstarted runners, stale branch, unmerged consumer PR and nondeterministic test are explicit unresolved states. Maintain retry bounds and no-false-green accounting. Do not claim estate deployment when only central code passes.


## Pull-request integration lane — 26 November 2026

[Issue #192](https://github.com/edithatogo/repository-standards/issues/192) extends this
track, not a parallel control plane. Keep the existing F01/F02 dependencies and
managed-remediation apply refusal. Read-only development can proceed in parallel.

- **A — Observe:** schedule or manually dispatch the default-branch workflow in this
  repository. Use native GitHub CLI metadata, bounded to 100 open PRs; a 101st observation
  fails the scan rather than implying completeness. Retain only PR number, base/head SHAs,
  disposition, scanner revision and timestamp. The scan is advisory, not authorization:
  check rollups can be incomplete or stale. No branch checkout of PR heads, App token,
  model execution, CI retry or merge in this increment.
- **B — Deterministic baseline:** reuse Git merge/update operations, native protected
  auto-merge and exact-head merge API, existing per-archetype verification and bounded
  runner retries. Test disposable canaries and rollback before any writer is enabled.
  Use existing F03 writer, registry and policy; do not duplicate control-plane ownership.
- **C — Model qualification:** F06 evaluates local Hugging Face assets only, as
  incremental challengers against B. No external inference APIs.
- **D — Controlled repair:** one writer and one integration at a time. Isolated
  candidate generation without secrets or network, allowlisted diff, independent
  verification, fresh required checks on the candidate and current base, unresolved
  review/intentional holds respected, native rules never bypassed. Protect CI,
  security, tests, evidence and scientific contracts from model-authorized weakening.
  App writer remains disabled until the preceding F03 and F04 gates pass.
- **E — Promotion:** qualify repository-standards read-only first, then a disposable
  write canary and an opt-in standards_check pilot. Registry-based estate rollout
  follows observed canary and rollback receipts; never auto-activate all repositories.

Local development at base 26e3ce78016a753ea5fb10dfed0950674f026c41 observed 28 open PRs,
including 11 drafts; security runner and qualification drafts remain independently
owned and held. The new scanner's seven focused unittest cases passed in an isolated
Python 3.13.5 environment after the initial missing-module failure. This is not a
full policy suite or qualified Python 3.15.2 execution. Hosted exact-head and
default-branch scheduled/dispatch acceptance remain open. No operational state is
claimed complete. Rollback is a normal protected revert PR.

### Integration checkpoint — 26 November 2026

Issue #192: #193 merged at 2f5677f436bdc1f6cb9f41951fe65772676dcf6d; eight
observed exact-head checks passed and no review threads. Receiving-main observed
checks subsequently passed. A live connector-based read-only inventory (not the
scheduled workflow) observed 28 open PRs: 11 drafts (#178, #171, #160, #159, #157,
#155, #154, #129, #119, #108, #81), two additional stacked PRs (#152, #147),
five behind (#149, #143, #137, #126, #112), two dirty (#113, #111) and eight
unknown (#101, #100, #98, #96, #91, #89, #86, #82). These are transient metadata
observations, not acceptance. #143's only added template was byte-preserved in a
non-force refresh bf110a37b1cbdbede6501ea50319df3c79e44f1c; eight new checks
passed; subsequently observed merged at f05d2771f08aa5088afffb4eae126d10a948336a
with the expected tree. #137 is a candidate for additive historical documentation
reconciliation; #112 alters existing casefolded/suffix matching semantics and must
not be merged as a tests-only change. Security and stacked qualifications remain
separately gated; inspect the actual current diff before deciding supersession.

Native baseline: `scripts/integration_baseline.py` previews a Git three-way merge
using exact SHA objects in a caller-provisioned isolated bare store. No ref update,
checkout, push, or acceptance; non-overlapping edits yield a candidate tree, real
conflicts and merge attributes hold. No speculative ours/theirs or union resolution.
The independent pure retry classifier proposes inspection only for structured
startup_failure on an exact PR head and independently established fresh tested
base, up to two reruns; generic failure, cancellation, timeout, unknown metadata,
and stale revisions cannot authorize retries. It has no write access. Keep the
qualified runner and writer gates; wire into orchestration only after isolated
negative canaries and independent exact-revision verification.

Local focused tests: initial import failure, then 10 passed (Python 3.13.5,
Git 2.47.3, disposable repositories, final tested blob hashes recorded in PR).
Full qualified Python 3.15.2 suite and hosted acceptance remain to be checked.
Add path-limited main-push inventory triggering so scanner changes can be
qualified immediately without a manual dispatch API. First actual hosted run
remains unobserved; no write activation or actual CI retries are claimed.

### Hosted scan acceptance

#194 merged at 49b532a8cb5627fe904ae6fa7032b6814fb001f3 after all eight observed
exact-head checks succeeded. First hosted inventory run [45785120410](https://github.com/edithatogo/repository-standards/actions/runs/45785120410)
succeeded on that receiving main SHA. Downloaded artifact 15099572973 was independently
SHA-256 verified as b880e2f11754d22bcef578ca0ba07fc05b2fd568c8fabb1fa6c887890bd5f332.
The receipt dated 2026-11-26T08:41:16.527351+00:00 contains 27 PRs (13 hold,
14 wait), zero merge candidates, mode plan_only and write_authorized false.
The live inventory is accepted for observation only, not for automatic writes.
#192 A is accepted. B, actual CI reruns and writer qualification remain open.
