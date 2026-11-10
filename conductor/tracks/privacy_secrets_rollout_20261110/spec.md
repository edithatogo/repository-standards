# Specification: privacy and secrets across owned repositories

## Goal and authority

The owner requested Microsoft Presidio or a suitable privacy framework, plus
Gitleaks, across all owned GitHub repositories. Implement a maintainable source
control baseline using upstream scanners and one shared pinned action. The request
authorises the additive workflow rollout; it does not authorise public disclosure
of private repository details, secret values, source data or history rewriting.

## Repository boundaries

`repository-standards` owns scanner wrappers, trusted baseline configuration,
dependency hashes, verified binary installation, tests, documentation and the
managed workflow template. Consumers own application dependencies, existing
scanner policy, optional stronger privacy profiles and branch protection.

No scanner runtime enters a consumer's production package. Python 3.12 is an
isolated tooling compatibility exception because Presidio 2.2.366 excludes Python
3.15; preserve consumer interpreter pins and environments. Consumer workflows use
an immutable shared-action commit and minimal read-only permissions.

## Acceptance criteria

1. Enumerate accessible owned repositories and distinguish active, archived,
   empty, private and execution-blocked cases. The 2026-11-10 snapshot is 303 total,
   277 active, 26 archived and 101 private. Public evidence uses aggregates only.
2. Preserve existing Gitleaks/PII controls. The shared Gitleaks gate retains all
   default rules and resists consumer configuration, environment and inline
   suppression overrides; verified canaries establish failure behavior.
3. Presidio detects the documented AU/financial/contact identifiers from Git text
   blobs without NLP downloads or an additional detector service. Evidence
   records advisory findings and unsupported content explicitly.
4. Secret scans cover submitted commit ranges and full locally reachable history
   when requested. The PII scan accurately states changed/current/index scope.
   No claim extends coverage to application data, all history, binary documents,
   names, NHI, IRD, medical record identifiers or re-identification risk.
5. Unsafe or incomplete inputs never produce a claimed complete clean assessment.
   Logs and any retained evidence exclude matched values and raw scanner output.
6. Workflow actions and shared implementation are immutable-pinned; binaries and
   dependencies are hash-verified. Untrusted repository paths do not execute
   application code, import shadow modules or follow symlinks outside the target.
7. The shared implementation passes behavioral tests and hosted canary execution
   before broad deployment. Merge consumer PRs only when the new scanner check
   passes and existing required checks allow it; preserve all existing gates.
8. Every eligible repository has a verified default-branch workflow or a precise
   unresolved blocker. Prepared branches, configured workflows and actual
   successful executions are counted separately. Archived projects are pending
   separate handling; no automatic unarchive or history rewrite occurs.
9. Local staged/full commands are documented with hook-installation limits. CI
   after upload is never described as preventing initial disclosure to GitHub.

## Migration and rollback

Publish and verify the shared action first, pin canary consumers to that commit,
then roll out in bounded batches. Refresh each branch head before creating its
commit; preserve concurrent changes. Update the central track with aggregate
receipts and keep private per-repository evidence separately. Upgrade shared
dependencies through the same checks and explicit consumer-pin changes.

Revert only the bounded rollout commit to roll back a consumer. Keep pre-existing
security workflows intact. A failed scan is a finding or an execution problem;
it is never a reason to disable an unrelated required check.
