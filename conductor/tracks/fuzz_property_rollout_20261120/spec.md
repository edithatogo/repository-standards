# Public fuzz and property-test rollout

## Purpose

Track the approved, bounded fuzz/property work in the public consumer repositories.
Record the actual candidate revisions, executed controls, hosted receipts and
remaining admission gates in [the execution ledger](ledger.md). This is a
coordination leaf under the existing verification programme, not a new central
runtime, shared test framework or estate certification.

## Authority and ownership

Consumer repositories own their input semantics, native implementation, compiler
and dependency pins, independent numerical oracles, data provenance and release
acceptance. This track owns only its four documents and the additive entry in
`conductor/tracks.md`. Existing F01/F03/F04 work, shared policy/schema/workflow
files, community defaults, offline-security drafts and Grype delivery retain
their current owners. The coordinator does not merge or activate consumer PRs.

## Acceptance assertions

1. Each published candidate names its repository, PR, exact observed head and
   applicable compiler/interpreter profile. A changed head needs fresh evidence.
2. The ledger distinguishes source implementation, local execution, hosted
   execution, full repository gates and acceptance on the default branch.
3. Meaningful valid inputs reach the real implementation; negative and
   metamorphic controls exercise an explicit contract. No generated oracle is
   silently promoted as independent scientific truth.
4. Campaigns have explicit input/case/time/resource budgets and failure retention
   appropriate to the consumer. A queued, skipped, compile-only or zero-test run
   is not counted as executed fuzz/property coverage.
5. Stable property/corpus execution, coverage-guided native mutation, sanitizer
   execution and model checking remain separate claims. Stable-only policies
   cannot be bypassed to obtain a green sanitizer badge.
6. Existing full lint, test, privacy, supply-chain, independent-method and release
   gates remain intact. A targeted pass does not waive an unrelated failure.
7. Only synthetic or appropriately public/rights-clear inputs enter committed
   corpora and retained public evidence. Secrets and source snapshots are not
   copied into this ledger.
8. Repositories with an already adequate approach or an active owner hold retain
   that disposition; forks follow upstream alignment without parallel machinery.

## Completion boundary

The coordinating candidate remains in progress until the scoped implementation
receipts and unresolved dispositions are reviewed and the relevant repository
checks have their own revision-bound receipts. This track does not assert full
estate rollout, release qualification, memory safety or scientific validity.
See [the plan](plan.md) for open work; an open consumer PR remains an unmerged
candidate even when its targeted campaign passes.
