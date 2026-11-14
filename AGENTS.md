# AGENTS.md

## Operating model

This repository is maintained by one developer. Automated review, tests, and security gates replace mandatory human approvals. Do not add CODEOWNERS approval requirements, team assignments, or a second-maintainer dependency.

## Required evidence

Before proposing a merge, run the documented one-command validation target, preserve deterministic failure artefacts, and identify any release, data, credential, or human-review gate that remains open.

## Boundaries

Never commit credentials or sensitive data. Keep generated files reproducible. Prefer one authoritative configuration and link to it from tool-specific files.

## Architecture and ownership

- `profiles/` and `schemas/` define central policy and versioned contracts.
- `scripts/` implements policy evaluation; `tests/` proves behavior and failure modes.
- `registry/` records observed repository classifications and explicit unknowns.
- `managed-files/` describes delivery ownership; consumer-specific content is preserved.
- `conductor/` records scope, acceptance evidence, open gates and concurrent work.
- Shared community defaults belong to `edithatogo/.github`; runtime and build
  guidance belongs to each `template-solo-*` starter.

Read the relevant track before editing owned paths. Use one writer for each path,
reconcile the actual current base, and never overwrite another active branch's
changes. Keep private inputs and reports out of public artifacts.

## Development and validation

Install the hash-verified policy tooling using the Python 3.15.2 commands in
[README.md](README.md#installation-and-development). From the repository root run:

```sh
PYTHONPATH=scripts .venv/bin/python -m unittest discover -s tests -v
```

For evidence schema changes also run:

```sh
PYTHONPATH=scripts:tests .venv/bin/python tests/evidence_schema_acceptance.py -v
```

Record failures, capability skips, runtime, source commit and hosted check URLs.
After source reconstruction or a changed head, rerun the applicable qualification;
historical successful tests are not evidence for different bytes.

## Community and bootstrap changes

Use [the community/bootstrap contract](docs/community-bootstrap-standard.md).
Resolve supported public account defaults before calling an inherited file
missing. A local issue template or chooser replaces the entire default issue
group; local Markdown and agent instructions remain authoritative. Declarations
may explain applicability but cannot weaken explicit central requirements.

Validate inputs without executing repository content. Never follow snapshot
symlinks outside the declared root, overwrite source with reports, or treat
unknown settings as success. Retain the Renovate provider and zero mandatory
human approvals. Keep F01 live acceptance, F03 apply mode and unrelated
offline-security drafts gated until their own evidence is complete.
