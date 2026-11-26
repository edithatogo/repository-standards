# Reviewed nonsecret findings

`reviewed-findings.json` records individually reviewed false positives in the
shared scanner. It is loaded from the pinned tooling checkout on every scan.
Target repositories, environment variables, ignore files and inline comments
cannot add or replace an admission. Upstream Gitleaks rules remain enabled.

## Exact identity and review

An entry must bind all of these fields together:

| Field | Required meaning |
| --- | --- |
| `commit` | Full immutable commit ID reported by Gitleaks |
| `path` | Exact canonical repository-relative filename |
| `rule_id` | Exact Gitleaks rule identifier |
| `line` | Exact positive integer starting line |
| `value_sha256` | SHA-256 of the actual matched value's UTF-8 bytes |
| `reason` | Substantive explanation establishing that the value is not a credential |
| `evidence_urls` | Public immutable source/object evidence supporting that review |

The initial two entries concern independently verified Git blob identifiers in
the public `edithatogo/tobac` publication inventory. Review recomputed each Git
blob identifier from its object bytes and checked the referenced workflow's
qualified action pin. The registry links the exact introducing commit and
objects. Public visibility alone never makes a credential safe to admit.

An admission does not cover another commit, file, rule, line or value, even if
the text appears similar. Distinct values on the same line require separate
entries, each with its own value digest and review. Paths are compared as
reported, without normalization into an approved path. Staged findings and
findings lacking a commit are never admitted. Duplicate complete identities or
JSON keys, unknown fields, invalid types, missing files and malformed registries
fail closed.

The registry is limited to 128 KiB. This permits the individually recorded
identities in the current audit while retaining a fixed fail-closed size limit.

## Tobacco capsule and historical full audit — 14 November 2026

Six additional exact coordinates cover a public native-capsule workflow digest,
a scanner-log digest and four occurrences of a reCAPTCHA site identifier across
two immutable commits. The workflow blob reproduces the capsule's SHA-256.
Two retained original scanner logs reproduce the checkpoint's log digest.
The HTML occurrences are `data-sitekey` attributes in browser-rendered widget
markup, matching the documented client integration. Review records contain the
matched-value digests and immutable public Git object links. Raw values and
scanner reports stay outside this repository. The browser integration is
documented by [Google](https://developers.google.com/recaptcha/docs/display).

The consumer issues new capsule pins as `sha256:` content identifiers. Real
Gitleaks regressions retain SHA-1 and SHA-256 exact-admission coverage and verify
that a nearby bare hexadecimal credential continues to block.

## Voiage historical findings — 16 November 2026

The Voiage full-history audit exposed 100 exact findings. Eighty-six are archive
checksums for 14 Rust crate releases: each value was checked against both an
immutable crates.io index revision and the downloaded crate bytes. The remaining
entries identify frozen API-contract digests, Git tree or submodule identifiers,
bibliography keys, a test-code symbol and a prose phrase. Their immutable source
and corroborating object links are recorded with each entry.

Some historical lines contain several different checksums. Each one has a
separate identity and evidence entry; an unreviewed value on the same line still
blocks. Registry publication and a consumer pin update require their own current
source, security and hosted checks.

## CallTrack qualification fixtures

The CallTrack full-history audit matched 25 UUID4 fixture identifiers in
historical Android qualification receipts. Each entry points to the exact
JSON line and the fixture generator at the same Git revision. The generator
creates the identifier for a synthetic instrumentation session. The registry
stores the matched-value digest and exact finding coordinates.

## Change process

1. Establish the exact scanner finding locally, without posting raw values or
   snippets. Independently verify its nonsecret nature using immutable evidence.
2. Add only that finding's complete identity and a substantive review reason.
   Never import a target repository's allowlist or admit a path, rule or generic
   hash pattern. Native repository scanners retain their own review process.
3. Add behavioral tests for the exact case, mismatches and additional unreviewed
   findings. Run the shared policy/privacy suites and real Gitleaks checks.
4. Review and publish the central change through its normal required gates.
   Existing consumer pins continue using their previous behavior until a
   separately reviewed pin update adopts the new tooling commit.

## Private processing and public results

On POSIX, the wrapper requests an internal unredacted JSON report so it can hash
the actual matched value. Scanner stdout and stderr are discarded. A private
temporary directory has mode `0700`; child umask `077` retains report mode
`0600` even when Gitleaks replaces the file. The wrapper checks its file type,
permissions and link count before reading, and removes the report on success,
scanner error, timeout or parsing failure. Raw reports are never uploaded or
included in public summaries. Non-POSIX scans retain redacted reports and do not
apply admissions.

Public output separates `detected_finding_count`, `reviewed_nonsecret_count` and
the remaining blocking `finding_count`. Admission-only scans return status
`reviewed_nonsecret` and exit `0`; any additional finding still returns `1`.
Malformed registries and scan errors return `2`. No-match scans remain `clean`.
These outcomes apply only to the requested scan scope and do not establish that
unscanned history or unsupported content is safe.
