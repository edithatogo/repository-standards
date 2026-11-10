# Repository privacy and secret scanning

This standard supplies an additive source-control check using Gitleaks and
Presidio. It does not change a product's runtime dependencies, data model or
existing security controls. Deployment and execution are recorded separately in
the [rollout track](../conductor/tracks/privacy_secrets_rollout_20261110/index.md).

## Shared implementation

Consumers call `.github/actions/privacy-secrets` from this repository at an
immutable commit SHA. The action reads its own trusted scanner scripts and
configuration through `github.action_path`; it never executes a consumer's
application, package-install hooks or scanner configuration. Existing consumer
Gitleaks configurations and privacy checks remain independent controls.

The baseline uses Gitleaks **8.30.1**, Presidio Analyzer **2.2.366** and Presidio
Anonymizer **2.2.366**. Gitleaks release binaries are checksum-verified and Python
dependencies are installed from `privacy/requirements.lock` with required hashes.
Anonymizer is available in the tooling environment; automatic redaction of source
files and application-runtime redaction are not part of this implementation.

The tooling uses an isolated **Python 3.12** environment. This is a scoped
compatibility exception to repositories selecting Python 3.15 for their own
software: Presidio 2.2.366 declares Python `>=3.11,<3.15`. It does not change a
consumer's `.python-version`, environment, dependency lock or production runtime.
Requalify the isolated version and hash lock together when upstream compatibility
changes; never silently install into an existing product environment.

## Detection contract

| Control | Repository profile | Sensitive profile |
| --- | --- | --- |
| Gitleaks upstream default secret rules | Blocking findings | Same |
| Presidio AU tax file and Medicare numbers, credit cards and IBANs | Formatted or context-supported findings block; bare numeric matches are advisory | All supported matches block |
| Presidio email addresses and AU/NZ phone numbers | Block under `data`, `datasets`, `fixtures`, `exports` or `records`; advisory elsewhere | Block throughout selected text |
| Names, street addresses, dates of birth, NHI, IRD and local medical-record identifiers | Not provided by this baseline | Not provided by this baseline |

The profile is deliberately explicit: public bibliographies, attribution and
package metadata often contain names and contact details. Advisory does not mean
safe to publish. Review findings in their source context; choose `sensitive` for
repositories whose content warrants the stronger contact/identifier gate.

Presidio's existing pattern, validation and checksum recognizers are called
directly. No NLP model, generative model, remote recognizer, paid privacy service
or Copilot integration is enabled. Downloads install the tooling; repository
text is not sent to an additional detector service.

Gitleaks always extends its upstream default rules. Consumer `.gitleaks.toml`,
`.gitleaksignore`, environment overrides and inline `gitleaks:allow` comments do
not weaken this independent baseline. It does not automatically baseline existing
secrets or introduce blanket exclusions for tests, documentation or generated text.

Individually verified false positives may use the pinned tooling's
[exact reviewed-finding registry](../privacy/reviewed-findings.md). Each entry
binds commit, path, rule, line and matched-value digest; other findings still block.
The safe summary separately counts reviewed nonsecrets and remaining findings.

## Scan scope

| Invocation | Secret scan | Personal-identifier scan |
| --- | --- | --- |
| Pull request | Submitted commit range, including a secret added and later deleted | Complete final blobs of changed tracked files |
| Push to configured default branch | Introduced commit range; initial branch falls back to full history | Complete final blobs of changed tracked files; initial branch scans tracked text |
| Weekly schedule or manual full audit | All locally reachable Git history in a complete clone | Current tracked text snapshot |
| Local `--staged` | Staged Git diff, including an initial commit | Complete blobs of changed staged/index files |

The personal-identifier check does not inspect every historical blob. A PII value
added and removed within a series of commits may therefore be absent from its
changed-file scan. Full personal-identifier history analysis requires a separate
review. Gitleaks history scanning covers locally fetched refs, not deleted remote
refs, all GitHub PR refs, external archives or repository copies.

The scanner reads immutable Git blobs instead of following checked-out symlinks.
Text notebooks are included as stored JSON; cells are not executed and embedded
image payloads are not decoded. Binary documents, images, non-UTF-8 content, LFS
payloads, symlinks, submodule contents and files above the configured limit are
reported as coverage gaps. They are not certified clean. Consumer-specific
document extractors and existing broader privacy checks remain necessary.

## Workflow and reporting rules

- Use `pull_request`, a default-branch push, a staggered weekly schedule and manual
  dispatch. Never run this scanner through privileged `pull_request_target`.
- Pin external actions to commit SHAs, use `contents: read`, disable persisted
  checkout credentials and submodule checkout, and set a timeout and concurrency.
- Fetch complete Git history for the full audit. Missing history, unavailable
  dependencies, malformed ranges and tool errors must not become a clean result.
- Do not print matches, source snippets, author/email fields, commit messages,
  exception payloads or raw scanner stdout. Summaries contain rule/entity, escaped
  path, line and counts only. Paths can themselves carry private information;
  repositories must avoid identifiable filenames in public source and logs.
- Keep raw Gitleaks reports in private temporary storage and remove them on exit.
  Do not upload reports as artifacts or post automated finding comments.
- A passing exit code means no blocking finding within the stated scope. Inspect
  advisory findings and the coverage fields; an incomplete scan is not a complete
  privacy assessment. No-result output does not establish anonymisation.

CI runs after content reaches GitHub. It can detect a problem before merge when
the check is required, but cannot prevent the preceding upload. Install and test
the [local hook commands](../privacy/local-hooks.md) in each working clone for
checks before committing or pushing. A committed configuration does not install
hooks in existing developer clones.

## Findings and exceptions

For a genuine secret, revoke or rotate it through its owning service and remove it
from current source. Rewriting history is a separate, explicitly reviewed action;
deleting the current line does not remove historical exposure. For private data,
stop publication and assess affected copies before deciding on remediation.

Do not paste findings into public issues. Diagnose locally with value-free output.
Use synthetic fixtures and public example identifiers only after checking their
provenance. Proposed false-positive handling must be narrow, documented and tested
against a nearby real-positive case. The initial shared baseline supplies no
consumer-controlled suppression file; a required exception needs a reviewed
scanner/profile change and a new pinned revision.

## Rollout and maintenance

The 2026-11-10 inventory contains **303** owned repositories: **277** active and
**26** archived; **101** are private. These are discovery counts, not protection
claims. The public track stores aggregate evidence only. Keep the complete
inventory, private repository names, private paths and private PR URLs out of this
public repository.

Record each repository as discovered, prepared, PR opened, configured on its
default branch, executed, or blocked. A branch/PR alone is not a deployed control.
Require existing native and instruction-defined gates before merging; never
weaken them to finish the rollout. A successful receiving check qualifies
execution in that repository. For the qualified 2026-11-10 implementation pinned
to `985503bc8eae58e7d6ef36a6e5427d0077e0193c`, the 84 source tests, hosted source
canary and successful receiving canaries also support installation of an exact
baseline-only addition while its receiving job is queued or refused before runner
startup. Verify the exact workflow, expected PR head and default-branch pin,
and label execution unverified. This does not waive a required check, a local
validation or review requirement, an existing security gate, or a privacy failure
after scanner execution. The distinction installs reviewed configuration without
claiming that an unavailable runner scanned the repository.

Empty repositories need an initial commit. Archived repositories remain read-only
pending separate handling.
Disabled Actions, fork restrictions, quota refusal and suspended schedules are
execution blockers and must be reported separately from installed workflow files.

Reconcile the inventory when adding repositories. Updates to this shared action
require behavioral tests, checksum/hash-lock review, a canary and explicit
consumer-pin updates. Immutable pins do not automatically follow upstream fixes.
Normal GitHub Actions usage still applies; no premium detector or paid integration
is required. Roll back by reverting only the rollout commit, preserving existing
controls and unrelated work.

## Primary references

- [Gitleaks usage, configuration and maintenance notice](https://github.com/gitleaks/gitleaks)
- [Gitleaks 8.30.1 release](https://github.com/gitleaks/gitleaks/releases/tag/v8.30.1)
- [Presidio supported entities and detection methods](https://presidio.dataprivacystack.org/supported_entities/)
- [Presidio Analyzer 2.2.366 package and Python compatibility](https://pypi.org/project/presidio-analyzer/2.2.366/)

Gitleaks upstream currently describes feature development as complete, with
security patches continuing. Retain the requested tool; evaluate a successor
separately against detection and migration evidence before changing the baseline.
