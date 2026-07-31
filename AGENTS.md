# AGENTS.md

## Operating model

This repository is maintained by one developer. Automated review, tests, and security gates replace mandatory human approvals. Do not add CODEOWNERS approval requirements, team assignments, or a second-maintainer dependency.

## Required evidence

Before proposing a merge, run the documented one-command validation target, preserve deterministic failure artefacts, and identify any release, data, credential, or human-review gate that remains open.

## Boundaries

Never commit credentials or sensitive data. Keep generated files reproducible. Prefer one authoritative configuration and link to it from tool-specific files.