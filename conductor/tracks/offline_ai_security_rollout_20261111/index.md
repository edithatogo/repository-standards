# Offline AI security estate rollout — 2026-11-11

Status: **implementation staged / execution not qualified**. Central draft PR #126.

## Estate discovery and rollout receipts

GitHub search `user:edithatogo archived:false fork:false` returned 177 repositories on 2026-11-11, including `repository-standards`. An additional accessible repository (`academic-research-skills`) was included via owner-affiliation discovery. Search `is:pr is:open head:security/offline-ai-security-rollout-20261111` reported **175 open consumer PRs**. These are proposals, **not** active controls.

Two exceptions require separate remediation:
- `Budget_2026_MMH`: branch and workflow committed; creating a PR returned GitHub 403 `Resource not accessible by integration`.
- `nztaxmicrosim`: branch created; GitHub ruleset rejected file creation with 409 `Changes must be made through a pull request`. No executable caller committed.

No existing workflows were removed or replaced. Several existing repositories already deploy the independent Gitleaks/Presidio guard; this new strict-offline profile is additive.

## Requirements and MoSCoW

**Must**
- Immutable SHA reference for central workflow and immutable SHA-256 local security image.
- Runner checkout performed with no persisted credentials, scanner execution in `--network none` container, no runtime downloads or model fetches.
- Runner image includes independently verified Gitleaks, Opengrep, Presidio, anonymizer, GLiNER and Promptfoo with hashes/SBOM; local model weights only.
- Gitleaks complete git history plus changed-range scan; Opengrep taint rules; fail-closed runtime DLP; deterministic mock red-team cases.
- Repository and central implementation CI must be validated, including negative controls; evidence never contains raw secret/PII values.
- CI runner should enforce protected non-root execution, resource constraints, isolation, no workflow-token access in scanning container, and local-only caches.
- Exemptions are tracked with precise provenance, not blanket ignores.
- Protected repository exceptions remediated without bypassing branch rules.

**Should**
- Add real application ingress, retrieval, MCP, logging and egress DLP integrations; mock-only tests cannot substantiate live protection.
- Validate Rust and TS sanitizer implementations independently; a Python wrapper alone is not sufficient.
- Review source-to-sink reachability on real code bases; quantify false positive/false negative rates.
- Reconcile estate manifest, managed-files registry, privacy-secrets standard and Conductor requirement tests.
- Enforce code coverage against seeded adversarial datasets and observed boundary integrations.

**Could**
- Generate SARIF with value-free annotations; produce sealed local compliance receipts and a periodic attestation.
- Hardware-backed isolated runners and offline artifact mirror.

**Won't yet**
- Hosted LLM judges, live token verification, auto-downloads inside scanning, or claims of complete PII recall.

## Executable tracks

- [ ] 01. Qualify scanner container image and binary/model digests, generate SBOM and local SPDX record.
- [ ] 02. Provision self-hosted runner labels and network denial; verify no egress via test harness.
- [ ] 03. Integration-test exact Gitleaks and Opengrep CLI arguments against pinned binary versions (positive and negative fixtures).
- [ ] 04. Integration-test Presidio+GLiNER model loading, offsets, clinical and financial fixtures, failure-closed behavior and offline dependency enforcement.
- [ ] 05. Validate Promptfoo provider API against pinned CLI and add real, local agent providers.
- [ ] 06. Add per-language sanitizer contracts for Python, TypeScript and Rust and enforce genuine egress interception.
- [ ] 07. Resolve repository exceptions and audit PRs, checks, branch policies and merges.
- [ ] 08. Update caller workflow SHA only after qualified central merge; roll out merges one by one after checks pass.
- [ ] 09. Reconcile all managed-file and estate conformance contracts; publish no-sensitive-data aggregate outcomes.

## Known limitations

A GitHub-managed controller/checkout requires GitHub connectivity even when the scanner container cannot reach the network. Configuration labels such as `SECURITY_NO_EGRESS` are not sufficient proof; namespace/container/network tests must demonstrate denied egress. Regex/SAST/NER detectors are bounded, and 100% detection across arbitrary PII and unknown code is not establishable.

## Continuation evidence — 2026-11-11

- Added a tracked-content AI detector (`security/offline-ai/scripts/detect_ai.sh`), including generic filename imports. Its five local synthetic fixture tests passed using Python pytest; this is not proof of whole-estate classifier recall.
- Added dedicated regression fixtures for the AI detector, enabled on the offline runner for all repositories.
- Hardened container options with `--pull=never`, a non-root UID, a readonly workspace, a dedicated writable tmpfs and tool-specific offline cache environment variables. Scanner execution stays `--network none`.
- Added a **non-mocked Presidio/GLiNER integration smoke suite**, required when AI code is detected. No successful full-model run has yet been observed. This remains a blocking qualification gate.
- Scanner runtime policy checkout now points at the updated immutable commit `dc52f7b5364253d7ff94684a8c8a62d97e349d88`. Consumer reusable workflow calls are still pinned to `36362fa872e4ce747266a6e795fcefa3dd343f67`; these call the changing central draft only after their PRs are updated to the qualified final SHA.
- The two identified exceptions remain unresolved: `Budget_2026_MMH` (403 creating PR) and `nztaxmicrosim` (409 protected-branch write).
- GitHub Actions security lint, policy and existing privacy workflows were observed queued/pending during these commits, not passing. Do not merge based on these observations.
