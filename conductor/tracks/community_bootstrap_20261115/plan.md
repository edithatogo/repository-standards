# Execution plan: community and repository bootstrap

## Scoped implementation

- [x] Reconcile repository heads, public account defaults, starter settings and
  concurrent PR-template ownership.
- [x] Define the contract and implement the bounded auditor with negative
  fixtures for inheritance, invalid inputs, unsafe paths and explicit unknowns.
- [x] Prepare complete shared community files and scoped starter guidance.
- [x] Preserve candidate source in nine review branches.
- [x] Qualify recovered final validator source locally on Python 3.15.2.
- [~] Require fresh hosted qualification and integrate passing heads.
- [ ] Resolve independent-review findings and verify every final PR head.
- [ ] Integrate passing scoped PRs, record actual deployed commits and reconcile
  existing issues #10, #18 and #40.
- [ ] Record bounded acceptance; keep wider estate rollout separate.

## Validation and recovery record

Before the executor interruption, the earlier validator tree passed 40 focused
behavioral tests with no skips on Python 3.15.2 and PyYAML 6.0.3. Seven earlier
schema tests passed after correcting the compiled-validator test binding. The
full 263-test attempt had one test-harness error and 34 pre-existing optional
scanner capability skips; it is not recorded as an all-pass result.

The initial starter candidates passed structural audits with actual observed
template/discussion settings, plus 149 targeted ignore-rule assertions. The
documentation starter passed its Markdown linter, the Node starter passed its
single existing test, and LaTeX/Typst make targets were inspected with dry runs.
Full native/document builds were not performed locally.

The local environment then became unavailable. The exact 15-file shared-default
payload survived in tool state and was published at commit
`52987aa2a6d9904a15e62226a02e02b72bca4cbd` in
[defaults PR #9](https://github.com/edithatogo/.github/pull/9).
Other final files were reconstructed from retained baselines and patch records.
Those reconstructed bytes require fresh review and hosted tests. The prior
counts above are historical evidence only.

The hosted parser installation uses the hash-verified PyYAML 6.0.3 source
distribution with `PYYAML_FORCE_LIBYAML=0`, disabled build isolation and separately
hash-pinned build tools. There is no assumption that a Python 3.15 wheel exists.

## Integration gate

Use the actual Python 3.15.2 policy jobs, schema acceptance, CodeQL and applicable
privacy/security checks. Resolve the final malformed workflow/devcontainer
counterexamples and legitimate relative-parent CLI paths. After a changed head,
wait for that head's own checks; do not reuse earlier green runs.

Review the published file list and preserved unowned blobs, then merge
sequentially with an expected-head lease. Capture each merge SHA and observed
provider/setting evidence. Keep unavailable evidence explicit.

## Remaining boundaries

A successful source suite does not activate a GitHub App, protection rule,
private reporting, development container, environment configuration or F01 live
credential. Updating seven starters does not retrofit their files into existing
consumer repositories. F03 apply mode and unrelated draft PRs stay gated.

## Recovered-source qualification

Execution became available again. The final source/test files hash to Git blobs
`077852291908c900d719b86e50be6e70d63998f6` and
`30b708b4b778986708243596b42c025784e1c2ee`.
The actual runtime was Python 3.15.2, PyYAML 6.0.3 without LibYAML, and
fastjsonschema 2.21.2.

- Full one-command suite: **274 selected, 240 passed, 34 existing capability
  skips**. All 50 behavioral and 8 public-contract tests executed.
- Separate evidence schema/pipeline acceptance: **4 passed**.
- Python compile checks passed.
- Central and shared-default snapshot audits: **13 pass, 4 explicitly not
  applicable**, exit 0 each, using observed settings and the central policy.
- Independent review found no remaining blocker in the concrete validator
  repairs or root-owned contract/documentation/CI scope.

Python starter PR #9 passed its actual Python 3.15.1 CI (one test), privacy scan
and Codecov patch check, and was merged at
`126d23c1f4c0e020fba87fb0ddfa5f3cbdb81d5d`. The other candidates retain their own head-specific gates.
