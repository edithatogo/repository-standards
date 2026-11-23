# Limma exact numeric-span review — 23 November 2026

## Scope and ownership

This increment starts from central commit
`4517ffdc2ffc9161af4f1fc9a2560b8690d760cd` on the isolated
`codex/limma-numeric-privacy-review-20261123` branch. Inspection of all 27 open
PRs found no pending source-byte conflict in the changed paths; the nominally
overlapping PR #152 blobs were already identical to main. The wider privacy
rollout remains open.

Limma's immutable target is `c6a757779c0f5d9869bf71a55df0c64cc69ac7b5`.
Its original complete scan used central
`2efdbd988064f6857795b9fa9ed4e1d08d18791d` with unchanged recognition and
severity. Gitleaks found zero secrets. Presidio selected 757 paths, scanned 756,
and skipped the Conductor submodule. It reported 123 blocking phone matches,
61,671 advisories and 53,001 finding groups, of which 52,001 were omitted by
the public report's cap. Thirty blocking matches were visible; 93 were omitted.
This was an observed failed full scan, separate from Limma's passing native
strict-suite and incremental checks.

## Complete classification

An uncapped diagnostic used the pinned scanner's unchanged Git selection,
blob reading, recognizers, chunking, deduplication, profile and severity. Its
per-blob totals reconcile with the original report. It recovered all 123 exact
identities in 115 blocking finding groups, without emitting matched values or
source-row snippets. Independent review checked every blob, line, Unicode span,
matched-value hash, CSV field boundary and immutable generator reference.

| Path under `tests-validation/data/` | Exact matches | Numeric role |
| --- | ---: | --- |
| `block/bojkova_pairs/input_log2.csv` | 20 | Log-intensity fractional digits |
| `block/techrep_mixed/input_log2.csv` | 4 | Synthetic log-intensity fractional digits |
| `block/techrep_synth/input_log2.csv` | 4 | Synthetic log-intensity fractional digits |
| `block/techrep_synth_na/input_log2.csv` | 3 | Synthetic log-intensity fractional digits |
| `matrix/conditions_categorical_numeric_covariates/input_log2.csv` | 30 | Log-intensity fractional digits |
| `matrix/conditions_numeric_covariate/input_log2.csv` | 30 | Log-intensity fractional digits |
| `matrix/conditions_only/input_log2.csv` | 30 | Log-intensity fractional digits |
| `matrix/conditions_categorical_numeric_covariates/design.csv` | 1 | Seeded noninteger numeric covariate |
| `matrix/conditions_numeric_covariate/design.csv` | 1 | Seeded noninteger numeric covariate |

The nine paths contain seven distinct Git blobs, all unchanged from audited
upstream `ba41fb6bbf6e3f2524bd44f5be017c827d5c4aaa`. No match crosses a CSV
field or belongs to a header or row label. Each central registry entry contains
its immutable source URL and applicable `block_goldens.R` or
`scalar_goldens.R` generator URL. The review establishes that the exact matched
spans are intrinsically numeric nonidentifiers. It does not claim full historical
regeneration, anonymity of the wider dataset or scientific qualification.

The complete value-free evidence remains in Limma's local verification receipts:

| Evidence | SHA-256 |
| --- | --- |
| Original failed full-scan JSONL | `6f047155898047d2196334f5beb485deeaab6ea6ceb8a8899b620d20395a6230` |
| Complete inventory | `ac5a1f69a68927eeeef79c52142d62d5eb4af0570b7eac62890c737e4c6e2241` |
| Source classification | `c691cb7e6f12fb4f150f5739b1e2a15cc1680348c7720df91ee04e2beef8ea3f` |
| Independently accepted 123-entry proposal | `3e3075404f857d80348e853eff6b2454141c051274fb7d6de878de1eed5d8c15` |

The reviewed central registry itself preserves every exact identity and source
reference, so qualification does not depend on publishing source data or a
second copy of the per-span inventory.

## Bounded registry change

All 21 previous JSON records are semantically unchanged. The 123 additions are
exactly the independently accepted proposal. One compact object per finding
line gives **144 unique identities in 126,835 bytes**, SHA-256
`cdc0a78625995b666cb99445462732055f7aefa4468433184aa9dc3f0329d47f`.
This fits within a fixed **128 KiB** cap, with 4,237 bytes remaining.

The only scanner runtime change is the cap from 64 to 128 KiB. No recognizer,
threshold, severity, report cap, match identity, file selection or consumer
override changes. Reviews still apply solely to exact committed blob spans in
the repository profile. Staged scans, sensitive scans, changed blobs or paths,
and other matches retain normal blocking behavior.

The new behavioral test pads valid JSON to exactly 128 KiB: it failed against
the original 64 KiB implementation, then passed after the bounded change. The
same test rejects one further byte. Existing tests exercise malformed and
duplicate entries, every identity mismatch, consumer overrides, staged and
sensitive scans, and neighboring unreviewed matches with real phone and credit
card recognizers. The full real Limma replay exercises the new numeric entries;
no duplicate numeric-recognizer rule or fixture was introduced.

## Executable qualification

The clone-local native hook was installed before tracked edits. Its trusted
staged guard uses the unchanged central workflow pin
`b30b07bcdaa6aebad2c6a57a4d0adc3616dabfe4`; it then runs the policy suite and
the separate real scanner suites against the candidate source. A disposable
native-hook proof passed a safe commit and blocked synthetic privacy and secret
canaries with unchanged HEAD. Actual candidate commit invocation and hosted
results must be recorded separately from this setup proof.

Use the documented hash-verified Python 3.15.2 policy environment and the
isolated privacy tooling environment:

```sh
PYTHONPATH=scripts GITLEAKS_BINARY="$GITLEAKS_BINARY" \
  .venv/bin/python -m unittest discover -s tests -v
PYTHONPATH=scripts GITLEAKS_BINARY="$GITLEAKS_BINARY" "$SCANNER_PY" \
  -m unittest discover -s tests -p 'test_privacy*.py' -v
PYTHONPATH=scripts GITLEAKS_BINARY="$GITLEAKS_BINARY" "$SCANNER_PY" \
  -m unittest discover -s tests -p 'test_secrets_scan.py' -v
"$SCANNER_PY" -I scripts/privacy_guard.py --root "$LIMMA_ROOT" \
  --binary "$GITLEAKS_BINARY" --mode full \
  --head c6a757779c0f5d9869bf71a55df0c64cc69ac7b5
```

Set `SCANNER_PY`, `GITLEAKS_BINARY` and `LIMMA_ROOT` to the actual isolated
Python, verified Gitleaks binary and Limma checkout. Logs and command receipts
are retained under `artifacts/verification/limma-numeric-review/`; clean-base
setup and canary proof are under `artifacts/verification/central-clean-baseline/`.

Clean-base qualification: **349 policy tests discovered, 311 passed, 38 explicit
capability skips** (26 Presidio and 12 Gitleaks). Separate real suites passed
**46 privacy and 39 Gitleaks tests with zero skips**. Capability skips in the
policy environment are never counted as real scanner execution.

Candidate qualification passed **350 policy tests discovered, 324 passed and
26 explicit Presidio capability skips**; this invocation supplied
`GITLEAKS_BINARY`, so its 12 Gitleaks capability tests executed. The separate
real suites passed **47 privacy and 39 Gitleaks tests with zero skips**. Their
command receipt SHA-256 is
`f894cdf1e4add9ef260ab835156e13f28968e50aab198dce4ee08c1ae0185d7e`.
The size-bound red test and six passing review/identity tests are retained
separately. Independent review accepted the source, registry, tests and scope
with no blocking finding.

The candidate complete scan of the immutable Limma target exited **0** after
223.980 seconds: **zero Gitleaks secrets, zero blocking privacy matches and
123 reviewed numeric spans**. It retained **61,671 advisories**, selected 757
paths, scanned 756 and skipped the Conductor submodule. Its report correctly
remains `status: incomplete` with `coverage_complete: false`; passing the
blocking gate does not imply complete coverage. The safe JSONL SHA-256 is
`1a153dd6b67d7ed4c5d9f96d6f6658f802ddd014143ba0d6293f15a7eb26e2cc`.
The receiving receipt binds the exact scanner, registry and test-file hashes.

Actual native commit, current hosted
`behavioral-tests` and candidate-source `canary-scan` are acceptance gates.
The central privacy workflow's older pinned action cannot alone qualify the
new scanner source. Limma must adopt an immutable qualified central revision
and pass its own full receiving scan and strict local/hosted CI. Advisory
counts and submodule coverage limits remain explicit after exact-span review.
