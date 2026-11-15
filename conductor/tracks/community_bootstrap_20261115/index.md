# Community and repository bootstrap

Status: **source locally qualified; hosted qualification and integration in progress**.
Created: 2026-11-15 (Australia/Brisbane).

- [Specification](spec.md)
- [Execution plan and evidence boundaries](plan.md)
- [Track metadata](metadata.json)
- [Published candidates and outstanding acceptance](publication-20261115.md)
- [Community/bootstrap standard](../../../docs/community-bootstrap-standard.md)

This bounded increment covers the central standards repository, public account
defaults and seven language/document starters. It supports existing issues
[#10](https://github.com/edithatogo/repository-standards/issues/10),
[#18](https://github.com/edithatogo/repository-standards/issues/18) and
[#40](https://github.com/edithatogo/repository-standards/issues/40);
their broader estate acceptance remains open.

The shared-default candidate is preserved in
[edithatogo/.github PR #9](https://github.com/edithatogo/.github/pull/9).
Final source was partly reconstructed after a temporary executor interruption.
After recovery, the exact validator/test blobs passed the full Python 3.15.2
suite: **274 selected, 240 passed, 34 pre-existing scanner capability skips**.
All 50 new behavioral and 8 contract tests executed; four separate
schema/pipeline acceptance tests passed. Central and shared-default snapshot
audits passed. Current-head hosted checks still gate integration.
