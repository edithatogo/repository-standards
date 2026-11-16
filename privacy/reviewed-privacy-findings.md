# Reviewed privacy nonidentifiers

`reviewed-privacy-findings.json` is a trusted, size-bounded registry carried by
the pinned scanner. Each reviewed span binds the exact Git blob, canonical path,
entity, line, Unicode character offsets, matched-value SHA-256 and repository
profile. The accompanying reason and immutable evidence links explain why that
specific span is not an identifier. The scanner reads the registry afresh and
rejects malformed or duplicate complete identities. Target files, environment
variables and inline text cannot supply reviews.

Reviews apply only to blocking matches in committed blobs under the repository
profile. They do not apply to staged content or the sensitive profile. Changed
blobs and other spans still receive normal detection and severity. The public
report counts reviewed nonidentifiers separately without emitting matched text;
unsupported files and advisory findings remain visible.

The identity is content-addressed and is not bound to a repository name. The
same bytes at the same path in another repository can receive the same review.
Only intrinsically nonidentifying spans should be entered; a value whose privacy
depends on surrounding records or repository context must remain blocking.

## Voiage synthetic fixtures — 16 November 2026

Eighteen spans are reviewed: 15 are decimal outputs in a deterministic synthetic
health example, two are aggregate numbers in a normative result fixture, and one
is a fictional process-table literal in a resource-sampling test. Each entry
links its immutable source and supporting generator or fixture documentation.
These entries do not review any other data or establish scientific acceptance of
the paper. A local full scan also reported binary and submodule coverage gaps;
reviewing these spans does not close those gaps.

Changes require exact-source provenance review, neighboring unreviewed-match
tests with the real recognizer, the shared scanner and policy suites, and current
hosted qualification before a consumer adopts a new action pin.
