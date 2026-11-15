# Contributing

## Setup and development

Clone this repository and follow the Python 3.15.2 virtual-environment and
hash-verified dependency installation commands in [README.md](README.md#installation-and-development).
Use a focused branch with a short descriptive name such as
`feat/community-bootstrap` or `fix/issue-form-validation`. Read
[AGENTS.md](AGENTS.md) and the relevant [Conductor track](conductor/tracks.md)
before changing a policy contract.

Keep authoritative declarations in `profiles/` and `schemas/`; put executable
policy logic in `scripts/`, behavioral fixtures in `tests/`, and adoption
guidance in `docs/`. Preserve existing formatting and local repository
extensions. Describe an observable counterexample before changing validation
logic, then add the smallest useful test proving the intended behavior.

## Validation

Run the repository's one-command policy suite from its root:

```sh
PYTHONPATH=scripts .venv/bin/python -m unittest discover -s tests -v
```

For changes to evidence schemas, also run:

```sh
PYTHONPATH=scripts:tests .venv/bin/python tests/evidence_schema_acceptance.py -v
```

The hosted policy jobs validate JSON, compile Python and run these checks on
Python 3.15.2. Optional scanner capability skips must remain visible and cannot
stand in for privacy or secret-scanner execution. Follow
[privacy/local-hooks.md](privacy/local-hooks.md) when those components change.
Never include credentials, patient data, private repository identities or
unredacted scan findings in public fixtures or reports.

For community/bootstrap changes, validate both local overrides and public account
inheritance using the [snapshot audit](docs/community-bootstrap-standard.md#snapshot-audit-and-evidence).
Record the input commits only for clean, exact snapshots; edited candidates
must be labelled as candidates. A structural audit does not prove hosted
automation or provider activation.

## Pull requests and review

Explain the problem, resulting behavior, related issue, test evidence and any
compatibility or rollout risk. Update documentation when a contract changes.
Keep changes scoped, reconcile a moving base before integration, and preserve
work owned by concurrent pull requests.

Human approval is not required for this solo-maintainer estate. Required
automated checks, applicable security findings and independently reviewed
behavioral concerns must be resolved before merging. Do not add CODEOWNERS
approval requirements or introduce a second-maintainer dependency. A passing
test on an earlier commit does not qualify a changed head.

Lifecycle, licence, publication and canonicalisation decisions remain
`review_required` until supported by evidence. F01 live collection and F03
managed remediation retain their existing credential and acceptance gates.
Opening or merging a source pull request does not complete estate deployment.

## Security and community conduct

Use the private reporting route in [SECURITY.md](SECURITY.md) for vulnerabilities.
Use [SUPPORT.md](SUPPORT.md) for help, and follow
[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) in project spaces.
