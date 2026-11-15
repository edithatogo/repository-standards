# Specification — Risk-tiered enforcement and privacy rollout

## Requirement and contract
Make policy effective at merge without human-approval dependency: canary-qualified rulesets/protection, stable required check names, least privilege, immutable pins, verified secrets/PII scans, bypass audit and owner recovery. Preserve repository-local stronger controls; never silently reduce protection. Explicitly address GitHub App administration permission limitations.

## Acceptance criteria
Canary ruleset tests show both deny and allow behavior; required gates cannot be bypassed by skipped/cancelled jobs; no human reviewer required; every eligible repository either has verified enforcement or a dated, owned exception/blocker.

## Boundaries and dependencies
- frontier_01_evidence_inventory_20261113
- privacy_secrets_rollout_20261110

## Policy ownership
Central standards controls and evidence contracts only; consumer repositories retain their own product behavior, scientific correctness, and stronger controls. Write authority is separately gated. Never count scheduled/queued/unobserved checks as passed.
