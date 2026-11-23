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

## Innovate vendored matrix fixture — 17 November 2026

Three credit-card-pattern matches cross the minus sign between the real and
imaginary parts of complex coefficients in a sparse matrix test fixture. The
matched characters are fragments of two coefficients, not a standalone payment
identifier. The fixture's Git blob is
`10db683d632277443e5ed5a2730e3aeb5bee85c2`; its SHA-256 is
`da741086a459c084c4b79da1079d6d0b2322a30afd9a72e9e959dc8c4bc291f7`.
The bytes match the [upstream faer fixture](https://codeberg.org/sarah-quinones/faer/raw/commit/0539947ffb757a739d7e703a7d2fa0c792a909c1/faer/test_data/sparse_cholesky/medium-1.txt),
and the pinned Innovate copy's sparse Cholesky test parses it as complex matrix
data. The registry binds each review to the exact blob, path, entity, line,
offsets and matched-value digest. No other values or files are reviewed here.

Changes require exact-source provenance review, neighboring unreviewed-match
tests with the real recognizer, the shared scanner and policy suites, and current
hosted qualification before a consumer adopts a new action pin.

## Limma numeric fixtures — 23 November 2026

The registry adds 123 exact phone-pattern spans in nine paths (seven distinct
Git blobs) at Limma commit `c6a757779c0f5d9869bf71a55df0c64cc69ac7b5`.
All source blobs match the audited upstream revision
`ba41fb6bbf6e3f2524bd44f5be017c827d5c4aaa`. Independent review verified each
blob, line, Unicode offset, matched-value digest, CSV field and pinned generator:
121 matches are fractional digits strictly inside numeric log-intensity fields;
two are whole noninteger numeric covariate fields from a seeded R generator.
None cross fields or match a row label or header. Every entry links the exact
source and the applicable generator. This is a review of those numeric spans;
it neither certifies the dataset as anonymous nor establishes historical
regeneration or scientific acceptance.

The complete original scan reported 123 blocking matches and 61,671 advisories.
Its public report omitted 52,001 finding groups after its reporting cap; the
review therefore used a complete, reconciled inventory from the unchanged
scanner and immutable blobs. All 123 blocking identities were checked, including
the 93 matches absent from the capped report. Advisory findings and the skipped
Conductor submodule remain visible and are outside this exact-span review.

The registry is now bounded to 128 KiB and formatted as one compact JSON object
per finding line. The 144 entries retain all 21 prior records unchanged. Tests
accept valid JSON at the exact byte bound and reject one additional byte. The
larger capacity does not alter recognizers, severity, identity matching, profile
or staged-scan behavior. Future additions must remain within the fixed bound
or undergo a separate reviewed capacity change.

See the [qualification record](../conductor/tracks/privacy_secrets_rollout_20261110/limma-numeric-review-2026-11-23.md)
for provenance, commands, evidence hashes and the remaining hosted/receiving gates.
