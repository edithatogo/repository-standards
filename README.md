# Repository standards

[![OpenSSF Scorecard](https://api.securityscorecards.dev/projects/github.com/edithatogo/repository-standards/badge)](https://securityscorecards.dev/viewer/?uri=github.com/edithatogo/repository-standards)

Executable CI/CD, security, dependency-management, coverage, release, research-governance, and solo-maintainer standards for the `edithatogo` repository estate.

## Operating model

- [`registry/repositories.json`](registry/repositories.json) declares each active, non-fork, non-archived repository's archetype, risk profile, lifecycle status, exceptions, and sole-developer contract.
- [`profiles/archetype-profiles.json`](profiles/archetype-profiles.json) defines inherited controls for software, data, documentation, typesetting, research and infrastructure profiles.
- [`managed-files/manifest.json`](managed-files/manifest.json) separates centrally managed material from repository-owned context.
- [`scripts/audit_estate_conformance.py`](scripts/audit_estate_conformance.py) measures live conformance and reconciles the bounded status section of the central issue.
- [`schemas/verification-receipt.schema.json`](schemas/verification-receipt.schema.json) defines evidence from a one-command validation harness.

The posture is deliberately compatible with one maintainer: zero mandatory human approvals, no CODEOWNERS dependency, automated low-risk dependency updates only after stable checks, and protection against deletion and non-fast-forward changes where supported.

## Safe rollout

The scanner reports drift before managed-file synchronisation or ruleset activation. Lifecycle, licence, publication and canonicalisation decisions stay `review_required` until evidence supports them. See [`docs/continuous-conformance-standard.md`](docs/continuous-conformance-standard.md).

## Scientific/native ecosystem

The [scientific/native profile](docs/scientific-native.md) coordinates ownership,
frontier dependency qualification and resource evidence without replacing local
numerical gates. Delivery is tracked in [Conductor](conductor/index.md).

## Privacy and secret scanning

The [privacy and secrets standard](docs/privacy-secrets-standard.md) defines a
shared pinned Gitleaks/Presidio action, isolated scanner dependencies and
value-free findings. It supplements existing repository controls and distinguishes
configured workflows, executed scans and unsupported content. The
[local commands](privacy/local-hooks.md) support checks before commit or push;
hooks require installation in each working clone.

The [rollout track](conductor/tracks/privacy_secrets_rollout_20261110/index.md)
records implementation and aggregate deployment evidence. Its inventory includes
active forks as well as owned projects; archived repositories remain separately
accounted for. Private repository details are not published here.

## Grype dependency and release scanning

The [Grype rollout](docs/grype-rollout.md) supplies checksum-pinned vulnerability
scanning for resolved SBOMs and immutable image candidates, with advisory PR
findings, critical release gates and retained tool/database evidence. Consumer
publication and existing qualification gates remain separate.

## Community and repository bootstrap

The [community/bootstrap standard](docs/community-bootstrap-standard.md) defines
versioned applicability, inherited account defaults, local overrides and starter
requirements. Its [policy](profiles/community-bootstrap.json),
[applicability schema](schemas/community-bootstrap-declaration.schema.json) and
[offline auditor](scripts/audit_community_bootstrap.py) are maintained here.
Shared forms and community policies live in
[edithatogo/.github](https://github.com/edithatogo/.github); language-specific
setup and working directories live in the seven `template-solo-*` repositories.

This increment has a [separate delivery track](conductor/tracks/community_bootstrap_20261115/index.md).
A valid file or successful snapshot audit does not establish a hosted run,
active provider, enabled setting or estate-wide rollout.

## Installation and development

Use the repository's qualified **Python 3.15.2** runtime. The commands below use
a POSIX shell; on Windows use the corresponding `.venv/Scripts/python.exe`
interpreter and set `PYYAML_FORCE_LIBYAML` in the shell environment.

```sh
python3.15 -c 'import sys; assert sys.version_info[:3] == (3, 15, 2), sys.version'
python3.15 -m venv .venv
.venv/bin/python -m pip install --disable-pip-version-check --only-binary=:all: --require-hashes \
  -r tooling/estate-evidence-requirements.txt \
  -r tooling/community-bootstrap-build-requirements.txt
PYYAML_FORCE_LIBYAML=0 .venv/bin/python -m pip install --disable-pip-version-check \
  --no-build-isolation --no-deps --no-binary=pyyaml --require-hashes \
  -r tooling/community-bootstrap-requirements.txt
```

The parser is built from a hash-verified source distribution with its native
extension disabled; its build tools are pinned separately. It changes policy
tooling only. Consumer language/runtime pins remain repository-owned.

Run the one-command policy test suite from the repository root:

```sh
PYTHONPATH=scripts .venv/bin/python -m unittest discover -s tests -v
```

The suite reports optional Presidio/Gitleaks capability skips when those isolated
tools are not installed. Such skips are not executed scanner evidence. See
[CONTRIBUTING.md](CONTRIBUTING.md) for the additional schema, privacy and hosted
checks applicable to a change.

## Usage: audit a repository snapshot

Supply a checkout of the consumer, an independently captured public account
defaults checkout, and JSON metadata describing observed GitHub settings:

```sh
.venv/bin/python scripts/audit_community_bootstrap.py \
  --repository-dir /path/to/consumer \
  --defaults-dir /path/to/account-defaults \
  --metadata /path/to/observed-settings.json \
  --policy profiles/community-bootstrap.json \
  --output /path/outside-checkouts/community-report.json
```

The [standard](docs/community-bootstrap-standard.md#snapshot-audit-and-evidence)
documents the metadata and result states. The auditor reads local snapshots,
does not fetch repositories or change GitHub settings, and keeps unavailable
evidence explicit. Keep reports concerning private repositories private.

## Security, support and rights

Report vulnerabilities through the affected repository's private route described
in [SECURITY.md](SECURITY.md). For help and contribution questions, see
[SUPPORT.md](SUPPORT.md), [CONTRIBUTING.md](CONTRIBUTING.md) and the
[Code of Conduct](CODE_OF_CONDUCT.md).

The repository is distributed under the existing [Apache-2.0 licence](LICENSE).
Use [CITATION.cff](CITATION.cff) for citation metadata. These statements do not
assign a licence or supported-version promise to other repositories.
