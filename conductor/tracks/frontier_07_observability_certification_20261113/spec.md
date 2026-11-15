# Specification — Continuous assurance scorecard and frontier certification

## Requirement and contract
Define falsifiable frontier status and sustain it through time-series assurance, not a static badge or self-declaration. Track coverage, evidence freshness, required-check execution, enforcement, escaped defects, remediation lead time, exceptions, flakiness and costs with explicit denominators and stratification.

## Acceptance criteria
Frontier designation is evidence-backed and dated, never permanent; all P0 hard gates demonstrated on applicable canaries; no unknown recorded as pass; audit regression reliably revokes designation; clear exceptions/owners/expiry and low-cost ongoing operation.

## Boundaries and dependencies
- frontier_01_evidence_inventory_20261113
- frontier_02_enforcement_20261113
- frontier_03_managed_remediation_20261113
- frontier_04_verification_harness_20261113
- frontier_05_release_supplychain_20261113
- frontier_06_agent_assurance_20261113

## Policy ownership
Central standards controls and evidence contracts only; consumer repositories retain their own product behavior, scientific correctness, and stronger controls. Write authority is separately gated. Never count scheduled/queued/unobserved checks as passed.
