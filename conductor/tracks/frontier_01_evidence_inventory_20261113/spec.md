# Specification — Fresh inventory and evidence-grade conformance

## Requirement and contract
Establish an authoritative dated inventory of accessible owned, active, forked, archived, disabled, public/private, and newly-created repositories. Reconcile 2026-07-31 163-repository committed audit against 2026-11-10 303-total/277-active privacy checkpoint without assuming identical scope. Distinguish missing permissions from nonconformance, stale evidence from failed checks, and configured controls from executed and enforced controls. Capture exact commit, run, ruleset, exception and generated timestamp. Publish aggregate public results only.

## Acceptance criteria
Every in-scope accessible repo is accounted for once; unavailable identities are counted separately. No undocumented scope mismatch; no inferred branch protection from forbidden API responses; reproducible snapshot schema and redacted public aggregate; stale/missing evidence cannot count as pass; tests prove all counterexamples.

## Boundaries and dependencies
- No upstream Conductor track.

## Policy ownership
Central standards controls and evidence contracts only; consumer repositories retain their own product behavior, scientific correctness, and stronger controls. Write authority is separately gated. Never count scheduled/queued/unobserved checks as passed.
