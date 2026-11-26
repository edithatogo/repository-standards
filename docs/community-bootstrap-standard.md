# Community and repository bootstrap standard

Version: **1**. The central contract covers collaboration templates, community
guidance, automation configuration and project startup. It applies through
archetype defaults and explicit applicability; it does not require every possible
GitHub feature in every repository.

## Ownership and authority

| Material | Authority | Delivery |
| --- | --- | --- |
| Required controls and conditional applicability | `profiles/community-bootstrap.json` and the policy schema | Reviewed changes in this repository |
| Local applicability and rationale | Consumer `.github/community-bootstrap.json` and the declaration schema | Repository-owned, unable to weaken explicit central requirements |
| Shared issue forms, chooser, PR template and community policies | Public `edithatogo/.github` repository | GitHub-supported account defaults, subject to local precedence |
| Runtime setup, ignore/editor rules, agent context and working source directories | Seven `template-solo-*` repositories | Included in newly generated repositories; existing repositories require focused adoption |
| Structural evaluation | `scripts/audit_community_bootstrap.py` | Offline, read-only snapshot audit |
| Live evidence, protection and managed rollout | Existing F01/F03 contracts | Their independent credentials and acceptance gates remain in effect |

The managed-file manifest links this contract separately. Its legacy `files`
array still drives presence checks; that scanner is not silently reclassified as
an inheritance-aware or content-aware audit. The standalone bootstrap auditor
must be invoked with the consumer and default snapshots. Estate-wide integration
and adoption need their own receipts.

## Required and conditional controls

| Control | Requirement and evidence boundary |
| --- | --- |
| README | Local project purpose, setup/access, usage, development/validation, security and licence guidance. An account README is not the project's README. |
| Contribution guidance | Local or inherited instructions on setup, validation and pull requests. Repository-specific commands stay local. |
| Code of Conduct | Local or inherited behavioral expectations, reporting route and enforcement process. No invented contact or response promise. |
| Security policy | Local or inherited supported-version policy, private reporting instructions and response expectations. A file does not enable private vulnerability reporting. |
| Support | Local or inherited help route, useful report context and availability expectations. |
| Issue templates | Effective bug, feature and documentation forms or Markdown templates. YAML forms use `.yml`; required structure, unique IDs and meaningful fields are checked. |
| Issue chooser | Effective `.github/ISSUE_TEMPLATE/config.yml`, with valid blank-issue choice and complete contact links. |
| Pull request template | Effective summary, related work, test evidence, compatibility/rollout and documentation prompts. Local project requirements are preserved. |
| Agent context | Local `AGENTS.md` or `.github/copilot-instructions.md` with project structure, boundaries and validation. These files are not inherited community health files. |
| Workflows | Local GitHub Actions YAML with meaningful trigger and jobs/steps or reusable-workflow calls. Structural validity is separate from hosted execution and required-check settings. |
| Dependency updates | Valid local Renovate or Dependabot configuration. The estate uses Renovate; a missing `dependabot.yml` is not a gap when Renovate covers the requirement. Provider installation and executed updates require separate evidence. |
| Ignore rules | Local `.gitignore` covering the project's generated, cached and secret-bearing files without hiding source, examples or dependency locks. |
| Editor rules | Local `.editorconfig` with explicit formatting; preserve Makefile tabs, language indentation and intentional Markdown line breaks. |
| Environment example | Required when environment-based application configuration is declared. Use a safe `.env.example`; never commit real secrets. A documented false declaration makes this not applicable. Unknown applicability stays unknown. |
| Development container | Required only by explicit policy or local opt-in. Otherwise optional, with rationale. A present configuration must name a meaningful image, Dockerfile/build or Compose backend. |
| Discussion templates | Applicable when Discussions is observed enabled. Match eligible non-poll category slugs; disabled is not applicable and unobserved settings/categories stay unknown. |
| Template repository | Required for designated starter repositories, verified using the actual GitHub `is_template` setting. An ordinary standards or defaults repository does not need this flag. |

CODEOWNERS is deliberately optional in the solo-maintainer model. Do not create
mandatory CODEOWNERS or human approvals. Review requests and protection
requirements are separate features.

Directory scaffolding should contain useful source, tests and documentation for
the archetype. Git does not require a file named `.gitkeep`; no empty placeholder
directory is required where real files already establish the structure. Template
generation copies files; later edits to a starter are not automatic updates to
existing consumers.

## GitHub inheritance and precedence

GitHub default community files must come from the account's **public** repository
named `.github`. They apply only to supported file types when a consumer has no
local equivalent. This works for personal accounts as well as organizations.
Default files shown by GitHub are not copied into a clone or generated project.

For ordinary supported Markdown community files, the auditor searches the
consumer's `.github/`, root and `docs/` locations in GitHub's documented order.
It then considers the public defaults snapshot. A local override is evaluated on
its own content; it does not silently pass because a better default exists.

Issue-template inheritance is a group rule. A local issue template or
`config.yml` causes GitHub to use that repository's issue configuration instead
of the entire default group. Copy all desired forms and chooser entries when
introducing a local group. Do not assume missing local forms are filled from
account defaults. Invalid local attempts are reported rather than hidden.

Discussion category forms are evaluated by matching category slug; a local form
can coexist with a default form for another eligible category. Do not apply the
issue-directory override rule to Discussions.

README, AGENTS, workflows, Renovate/Dependabot, editor rules, environment examples,
development containers and source scaffolding need explicit repository delivery.
Creating a new repository under a different owner also breaks reliance on
`edithatogo/.github`; the starter's `BOOTSTRAP.md` explains materialisation.

## Snapshot audit and evidence

Use Python 3.15.2 and the hash-verified parser/schema tooling described in
[README.md](../README.md#installation-and-development). The auditor executes no
repository code and makes no network or write calls to GitHub.

```sh
.venv/bin/python scripts/audit_community_bootstrap.py \
  --repository-dir /path/to/consumer \
  --defaults-dir /path/to/account-defaults \
  --metadata /path/to/observed-settings.json \
  --policy profiles/community-bootstrap.json \
  --output /path/outside-checkouts/community-report.json
```

Metadata is an explicit observation, not an assumption from filenames. For
example, a freshly observed standards-repository snapshot may use:

```json
{
  "repository": "edithatogo/repository-standards",
  "defaults_repository": "edithatogo/.github",
  "defaults_visibility": "public",
  "has_discussions": false,
  "discussion_categories": [],
  "is_template": false
}
```

Use actual observations for the audited snapshot. `has_discussions` and
`is_template` may be null when unavailable; `defaults_visibility` may be
`public`, `private`, `absent` or `unknown`. For enabled Discussions,
`discussion_categories` contains the eligible non-poll category slugs; null
means unobserved. Optional `revision` and `defaults_revision` identify exact
clean snapshots only. Do not attach a base commit to edited candidate bytes.

Each result reports `pass`, `fail`, `unknown` or `not_applicable`, plus
whether evidence is local, inherited, mixed, missing, unavailable or setting
metadata. Required failures and unknowns return exit 1; malformed inputs return
exit 2; an applicable conformant snapshot returns exit 0. Not applicable is an
explicit applicability result, not a missing-file pass.

Reports are written atomically with private permissions, outside both input
roots. The reader bounds file size/count and YAML complexity, rejects unsafe
YAML constructions and refuses symlink traversal and non-regular files. Treat
reports from private repositories as private; this tool is not the F01 public
aggregate publisher.

Snapshot file access currently requires descriptor-relative, no-follow filesystem
support (`O_NOFOLLOW` and `O_DIRECTORY`), as available on the qualified Linux
runner. On Windows, use a suitable Linux/WSL environment for this auditor;
unavailable safe-read capabilities remain unknown rather than weakening the
filesystem boundary.

The checks deliberately establish bounded structural properties. They do not
certify every upstream schema feature, prose accuracy, valid external links,
valid action revisions, container builds, successful tests, active providers,
private reporting enablement or protection enforcement. Unsupported JSON5/JSONC
configuration remains unknown rather than being called valid JSON.

## Delivery and acceptance

1. Reconcile current heads, setting observations and concurrent owners.
2. Review central contract and behavioral counterexamples; validate on the
   repository's qualified runtime.
3. Complete the public shared defaults and scoped starter files through focused
   PRs. Preserve local PR templates and product/runtime changes owned elsewhere.
4. Require actual checks for each final PR head before integration. Re-run
   qualification after a changed or reconstructed source tree.
5. Record merged commits and bounded adoption evidence. Existing consumers need
   separately reviewed adoption; the whole estate remains unverified until its
   own collection and rollout gates pass.

Rollback uses an ordinary reviewed revert of the affected change. Do not
force-overwrite local extensions. The existing F01 credential gate, F03 apply
gate, unrelated offline-security drafts and zero mandatory human approvals stay
unchanged.

## Continuous community file gate

The shared [Community Standards action](../.github/actions/community-standards/action.yml)
uses [the narrow profile](../profiles/native-community.json) and
[`check_community_standards.py`](../scripts/check_community_standards.py), which
calls the existing bootstrap auditor. It requires a local README,
effective contribution/Code of Conduct/security files, at least one valid
effective issue template, an effective PR template, and a **local nonempty,
non-placeholder licence file**. Native Markdown checks require readable, nonempty body content
that is not a placeholder; plain prose and nested sections are accepted without
requiring particular headings. The full bootstrap audit retains its substantive
section requirements. Neither file presence nor this gate rates prose quality.

The narrow profile has no mandatory issue-role names. An empty role mapping is
accepted only for this exact six-control profile with no recommended controls;
it still fails when there is no valid effective issue form. The full bootstrap
policy retains all 17 controls and its bug, feature and documentation roles.
Native checks accept empty optional labels/assignees in legacy Markdown
frontmatter. Additional invalid forms remain visible in result details when one
valid effective form exists; full bootstrap checks still reject invalid forms.
It remains the authority for agent context, runtime setup and other bootstrap
requirements; the narrow gate does not replace it.

The licence check reads root `LICENSE`, `LICENCE` or `COPYING`, optionally with
`.md`, `.txt` or `.rst`, through the auditor's bounded, non-following Tree reads.
It never inherits the account's licence, chooses terms, copies a licence or
certifies legal suitability. A missing, empty or obvious placeholder file stays a failed
control until the repository owner supplies appropriate existing terms.
Multiple nonempty local licence files are recorded together as presence
evidence, without choosing or reconciling their terms.

### Consumer workflow

Create `.github/workflows/community-standards.yml` with the following shape.
Replace `REVIEWED_40_CHARACTER_COMMIT_SHA` with the reviewed immutable commit
that contains the action. Keep the stable job name and avoid path filters so
required-check rules can always receive a result.

```yaml
name: Community Standards
on:
  pull_request:
  push:
  merge_group:
  workflow_dispatch:
permissions:
  contents: read
jobs:
  community-standards:
    runs-on: ubuntu-24.04
    timeout-minutes: 10
    steps:
      - uses: edithatogo/repository-standards/.github/actions/community-standards@REVIEWED_40_CHARACTER_COMMIT_SHA
```

The action owns sibling checkouts: the candidate in `project` and account
defaults in `community-defaults`. It reads actual GitHub repository metadata,
requires the matching owner's `.github` repository to be public, resolves its
default branch to an immutable commit, then verifies both checkout SHAs,
origins and clean state. Unavailable or inconsistent observations fail closed.
Local overrides retain precedence, including the whole issue-group override.

Only central scripts from the SHA-pinned action's `github.action_path` execute.
The isolated Python 3.15.2 environment uses the existing hash-pinned PyYAML
source/build dependencies. Neither consumer nor defaults code is imported or
executed, checkout credentials are not persisted, and the workflow needs only
`contents: read`; it does not use `pull_request_target`. Bounded metadata and
reports are retained as a run artifact for 14 days under that repository's
access controls. Private reports are not public estate aggregates.

### What a passing check means

This is a **candidate file gate**. [GitHub's community profile metrics](https://docs.github.com/en/rest/metrics/community#get-community-profile-metrics) are a
separate observation of the default branch and GitHub's own recognition rules;
adding a PR workflow does not itself update that score. The gate also checks
bounded issue-form structure. A passing gate is not a claim of a 100% GitHub
health score or a complete bootstrap audit.

The central policy workflow includes a `community-standards` canary job calling
the local composite action. Observe that final head's canary and policy tests
before consumers pin its published SHA; a local unit suite alone is not a
hosted action receipt.

A configured workflow is not automatically a merge requirement. After a real
`community-standards` run succeeds, use authenticated repository-administration
access to require that exact check through branch protection or a ruleset. Do not report
protection, private reporting, hosted success or estate-wide adoption from
source files alone. This action changes no repository settings and assigns no
licence or mandatory human approval.

## GitHub references

- [Default community health files](https://docs.github.com/en/communities/setting-up-your-project-for-healthy-contributions/creating-a-default-community-health-file)
- [Issue forms](https://docs.github.com/en/communities/using-templates-to-encourage-useful-issues-and-pull-requests/syntax-for-issue-forms)
- [Discussion category forms](https://docs.github.com/en/discussions/managing-discussions-for-your-community/creating-discussion-category-forms)
- [Private vulnerability reporting](https://docs.github.com/en/code-security/how-tos/report-and-fix-vulnerabilities/report-privately)
- [Template repositories](https://docs.github.com/en/repositories/creating-and-managing-repositories/creating-a-template-repository)
