# Repository product-metadata standard

This standard applies to active, non-fork, non-archived repositories. It is
designed for a sole maintainer: automated evidence is required, but no second
reviewer, team, CODEOWNERS approval, or mandatory human approval is introduced.

## 1. GitHub identity

Every substantive repository should have:

- a concise description stating what the repository provides, not its internal
  project codename;
- stable topics for its language, domain, artefact type, and `solo-maintainer`;
- a homepage only when a maintained documentation, package, dataset, or product
  URL exists;
- the GitHub template flag only when the repository is intentionally reusable.

Descriptions and topics are public metadata for public repositories. Do not
copy sensitive internal README text into them.

## 2. README contract

The root README is the operational landing page. In this order, it should
contain:

1. project name and one-sentence purpose;
2. a compact badge row;
3. status and scope, including important evidence limitations;
4. installation or access;
5. minimal usage;
6. development and verification commands;
7. security reporting;
8. citation, when warranted;
9. licence and third-party rights.

Recommended badges are limited to signals a maintainer can act on:

- required CI or readiness workflow;
- coverage only when real executable coverage is uploaded;
- licence only after a licence decision exists;
- citation/DOI only when the target exists;
- latest release only when releases are maintained.

Avoid decorative technology badges, stale quality grades, download counters,
and badges for services that are merely configured but not active. Relative
GitHub Actions badge links are preferred in repository templates so generated
repositories do not inherit the template repository's owner/name.

## 3. Citation

`CITATION.cff` is warranted for research software, datasets, scholarly
documents, reusable templates, and repositories that underpin a publication or
evidence product. It is optional for private operational configuration and
disposable prototypes.

The citation record should include:

- CFF 1.2.0;
- accurate title, type, authors, repository URL, and licence;
- DOI or preferred citation only when actually assigned;
- release date and version only when release automation keeps them aligned.

Do not invent ORCIDs, DOIs, affiliations, or publication status. A release
workflow should validate CFF and update release-specific fields from the
authoritative version source rather than maintaining duplicate versions by
hand.

## 4. Licensing and rights

Every repository requires an explicit decision:

- an SPDX-recognised `LICENSE` for repository-authored code and documentation;
- `LICENSES/` plus SPDX file headers when multiple licences are genuinely
  required; or
- a clearly documented `RIGHTS.md`/restricted-use statement where the
  maintainer cannot grant an open licence.

Never infer or bulk-apply a licence to existing content. Data, fonts, images,
archival records, model weights, and third-party templates must record their
own provenance and rights even when repository-authored code is MIT licensed.

Canonical greenfield templates use MIT for repository-authored starter
material. Users must replace it when their institution or source material
requires different terms.

## 5. Version authority

Each releasable artefact has exactly one authoritative version source.

- Python packages: derive the version from signed/release tags with
  `hatch-vcs`, `setuptools-scm`, or an equivalent PEP 621 dynamic version.
- Rust crates: `Cargo.toml` is authoritative; release automation updates it and
  verifies the matching tag.
- Node packages: `package.json` is authoritative; release automation updates it
  and the lockfile together.
- Typst packages: `typst.toml` is authoritative.
- LaTeX, documents, and datasets without a package manifest: immutable release
  tags and, where applicable, DOI deposits are authoritative.

`CITATION.cff`, package metadata, documentation, generated manifests, and
release notes must be checked for drift. Do not call a repository
“dynamically versioned” merely because a workflow creates tags.

## 6. Logging and observability

Structured logging is warranted for applications, APIs, CLIs, services,
scrapers, automation, and data pipelines. It is not required for code-free
documents or passive libraries.

Warranted implementations should:

- use the ecosystem logging facade (`logging`, `tracing`, `pino`, or
  equivalent), not scattered `print`/`console.log`;
- emit timestamp, severity, event name, component, correlation/run identifier,
  and safe contextual fields;
- write human-readable logs locally and machine-readable JSON in CI or
  production;
- redact secrets and direct personal, health, payment, and credential data;
- define retention and avoid logging full source records by default;
- expose metrics/traces only when there is an actual consumer.

Libraries should never configure global handlers or subscribers. They may emit
events and leave routing to the calling application.

## 7. Validation

The scheduled product-metadata audit records applicability separately from
presence. It must detect:

- missing README sections and actionable badges;
- absent descriptions and topics;
- missing licence decisions;
- missing citation metadata where warranted;
- duplicate or disagreeing versions;
- logging gaps where structured logging is warranted.

Repository-specific issues remain the authority for legal choices, publication
claims, package-release semantics, and logging fields. The audit is a triage
surface, not permission to guess them.

The scheduled workflow uses `ESTATE_AUDIT_TOKEN` when configured. Without that
read-only credential, its cross-repository result is public-only and must not be
represented as a whole-estate audit.
