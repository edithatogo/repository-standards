# Specification: community and repository bootstrap

## Problem and intended result

Repository standards previously covered automation more thoroughly than
collaboration and initial project setup. The approved increment gives every
requested checklist item an explicit required, conditional or optional policy,
usable shared defaults and language-appropriate starter guidance.

## Scope and ownership

- Central policy, schemas, auditor, tests, docs and track:
  `edithatogo/repository-standards`.
- Shared issue forms, chooser, PR template, contribution, conduct, security and
  support guidance: public `edithatogo/.github`.
- Local bootstrap, README, contribution, agent, security, ignore/editor and
  applicability files: `template-solo-python`, `template-solo-rust`,
  `template-solo-node`, `template-solo-data`, `template-solo-docs`,
  `template-solo-latex` and `template-solo-typst`.

Each path has one writer. Concurrent central PR #143 and docs starter PR #5 own
their local PR templates and remain separate. Previously merged local PR
templates remain authoritative.

## Acceptance criteria

1. A versioned contract covers README, contributing, conduct, security, support,
   issue forms, chooser, PR templates, agent context, workflows, dependency
   updates, ignore/editor files, environment examples, development containers,
   discussion forms and the GitHub template setting.
2. The auditor resolves actual supported public defaults and local precedence,
   including issue-group replacement and per-category discussion forms.
3. Missing or unknown applicable evidence cannot pass. Local applicability
   cannot weaken explicit central requirements. Invalid YAML/JSON and unsafe
   snapshot paths are bounded and rejected without executing repository code.
4. Meaningful negative fixtures prove these boundaries. Policy and declaration
   schemas agree with committed data and the runtime contract.
5. Shared forms cover bug, feature and documentation requests. Community
   guidance provides safe reporting and help without invented contacts or SLAs.
6. All seven starters have useful setup and verification instructions, scoped
   ignore rules and editor settings, with actual template flags observed.
7. Current-head checks, independent review and actual merge/deployment receipts
   determine status. A candidate audit is not estate-wide conformance.

## Preserved boundaries

Renovate remains the dependency-update provider. Mandatory human approvals stay
zero, CODEOWNERS stays optional, and existing stronger local controls survive.
No new licence is assigned where none exists. Environment examples and custom
containers are conditional, and useful existing source directories do not need
empty `.gitkeep` placeholders.

Consumer product source, dependencies, locks, runtime pins, citation identity and
workflows are outside the starter edits. F01 credentials/live acceptance, F03
apply mode, supply-chain certification and unrelated offline-security drafts
retain their own gates. Existing issues are reconciled without claiming complete
estate rollout.
