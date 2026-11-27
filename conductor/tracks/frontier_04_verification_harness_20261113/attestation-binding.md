# Independent attestation binding — 27 November 2026

Refs #19 and #192. #199's corrected head 44c6430ed17f70351241451403842d12b077fac9
passed eight checks and the exact-head review. Squash merge
af84c5a0e32fae5632b162fa21d482e837c6ca23 preserved its qualified tree;
receiving checks passed.

The new opt-in adapter invokes the trusted installed GitHub CLI's
[attestation verification](https://cli.github.com/manual/gh_attestation_verify),
not custom cryptography. It stages the same bounded bytes in a private temporary
directory. Independently supplied digest and producer identity are required;
enforce github.com, exact source and signer revision, same-repo non-reusable
main-branch workflow, GitHub OIDC issuer, SLSA v1 predicate, SHA-256 and
GitHub-hosted runner. No caller-supplied trust root or attestation bundle.
Nonzero exit, missing executable, changed bytes or timeout fail closed.
The executable/configuration and credential context must be independently
trusted; do not use a token with write scope.

For v1 receipts, inspect_attested_receipt reuses the merged semantic verifier
against the independently expected target repository, revision, check names and
freshness, then authenticates those exact bytes. Producer attestation does not
prove that underlying checks really ran; provenance_verified remains false
for the broader claim and write_authorized remains false. The byte-level
adapter also supports evidence artifacts such as public F01 aggregates, but
does not validate snapshot completeness, per-repository identity or tree
contents. F01's actual signed public artifact and authenticated private
snapshot checks remain separate gates. No live publication is changed.

Local TDD: seven methods passed under Python 3.13.5; native verifier boundary
mocked, v1 receipt validation real (schema and verifier blobs matched main).
Reproduce missing-module/missing-function failures and reject substituted
bytes, forged green claims, wrong target, missing/stale checks, unsafe policy
arguments, timeout and missing CLI. No actual signature verification claimed:
gh is unavailable locally, and local DNS prevents a complete clone.
Native positive/negative signed-artifact canaries, full hosted suite and
independent review remain required. No new model experiment or privileged
activation; preserve #196's security-review hold.
