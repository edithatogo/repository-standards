# Execution plan — public fuzz and property rollout

## Scope and writer reservation

The rollout coordinator owns only:

- `conductor/tracks/fuzz_property_rollout_20261120/spec.md`
- `conductor/tracks/fuzz_property_rollout_20261120/plan.md`
- `conductor/tracks/fuzz_property_rollout_20261120/metadata.json`
- `conductor/tracks/fuzz_property_rollout_20261120/ledger.md`
- The additive rollout link in `conductor/tracks.md`.

No central profile, schema, implementation, managed-file manifest, index or
consumer branch is changed by this coordinating PR. Existing concurrent PRs and
track owners retain their work.

## Delivery checklist

- [x] Read the actual current base, agent instructions, workflow and F04 scope.
- [x] Inspect public candidate PRs and retain exact source revisions.
- [x] Separate implemented candidates, observed targeted runs, pending receipts,
  already adequate approaches and legitimate owner holds.
- [x] Record known full-gate failures without lowering their requirements.
- [ ] Reconcile the remaining public implementation receipts and any repaired
  candidate heads, then re-read their actual workflow outcomes.
- [x] Run the repository's Python 3.15.2 one-command policy suite: 296 tests
  discovered, 258 passed and 38 optional scanner capability skips, no failures.
  Those skips do not establish scanner execution; final-byte checks are recorded
  in the coordinating PR.
- [ ] Publish the coordinating draft and observe its exact-head hosted checks.
- [ ] Reconcile consumer full gates, branch integration and receiving-main
  receipts before any rollout-acceptance claim or archival.

## Admission and handoff

Use the existing repository-owned gates; no new second-maintainer dependency is
introduced. Every ledger status is scoped to the linked revision and command.
Update a moving PR head as a new observation, retaining the distinction between
an old successful campaign and an untested replacement. Preserve failing
reproducers and classify environment restrictions separately from product bugs.
A contributor may remediate their owned paths; scientific/core-owner work and
frozen dependency stacks are not reassigned by this ledger.

The single policy command is:

```sh
PYTHONPATH=scripts .venv/bin/python -m unittest discover -s tests -v
```

Use the README's hash-verified tooling on the verified local Python 3.15.2
interpreter. Capability skips are explicit missing scanner evidence. No evidence
schema or executable-policy change is part of this leaf, so schema acceptance is
not claimed from these documentation edits.
