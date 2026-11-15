# Specification — Agent harness, context and change safety

## Requirement and contract
Establish a single-developer agent engineering profile: least privilege, data minimisation, untrusted text separation, explicit owned-file scope, independent behavioral and security verification, bounded tools and traceable change provenance without unnecessary approvals.

## Acceptance criteria
Attacks do not cause prohibited actions; test suite catches forged receipts and instructions; no secret values in logs; artifact can be reproduced at a declared commit; no second human required by default.

## Boundaries and dependencies
- frontier_03_managed_remediation_20261113
- frontier_04_verification_harness_20261113

## Policy ownership
Central standards controls and evidence contracts only; consumer repositories retain their own product behavior, scientific correctness, and stronger controls. Write authority is separately gated. Never count scheduled/queued/unobserved checks as passed.
