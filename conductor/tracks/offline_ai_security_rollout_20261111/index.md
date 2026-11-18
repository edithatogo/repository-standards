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

## Implementation tranche — offline contracts and source-to-sink assurance

Implemented in the central draft PR:

- `security/offline-ai/security/agent_boundary.py`: explicit DLP ingress and egress contracts, preventing tool invocation when sanitization fails and normalizing potentially sensitive exception text from transformations.
- `security/offline-ai/tests/test_agent_boundary.py`: five offline boundary regression tests, passed in a local isolated test environment using a minimal test-only DLP stub; production detector behavior was not tested by these five cases.
- `security/offline-ai/security/verify_assets.py`: SHA-256 verifier for a reviewed local asset manifest, trusted-root enforcement, duplicate and symlink rejection, required GLiNER config/weight verification.
- `security/offline-ai/tests/test_verify_assets.py`: seven positive/negative synthetic manifest cases passed locally (tampered weights, missing weights, duplicates, symlink, untrusted root, malformed manifest).
- `security/offline-ai/docker/Dockerfile`, `docker/build_offline.sh`, `docker/README.md`: offline build recipe requiring a preloaded digest-pinned base, local wheels, package hashes, binaries, Promptfoo and GLiNER files. Not built, qualified or deployed; provisioning assets are not present.
- `security/offline-ai/fixtures/taint/`: Python, TypeScript and Rust positive/negative fixtures; `scripts/verify_sast_fixtures.py` requires the real Opengrep executable to detect all three positive examples without flagging benign controls. Not yet executed against the binary.
- `security/offline-ai/run.sh`: asset verification and SAST rule qualification now execute before repository scan; locally runnable unit tests are invoked in scanner before conditional model tests.
- Central reusable workflow references scanner policy commit `06def09d9595bce33fc43fa390940a3c61fce125`. Consumer caller references are unchanged pending central qualification and merge.

The 12 locally executed unit cases are **not** a complete validation of the scanner stack. Requirements 01–09 remain open until independent asset/model verification, full real-tool tests, network-denial tests, cross-language runtime integrations and estate-wide reconciliation succeed.

**Design limitation:** explicit `guarded_invoke` and `guarded_transform` calls do not automatically interpose on unmodified application code. Product-level interception and Rust/TypeScript compatibility remain open, and Python `sanitize_context` must not be treated as proof of anonymization.

## Security engineering tranche — continuation

Additional centrally committed assets and status:

| Track | Implemented locally | Qualification remaining |
| --- | --- | --- |
| 01 Offline supply chain | Offline-only Dockerfile, vetted wheelhouse and binary contract, digest-locked base-image requirement, local manifest checksum verifier with 7 synthetic tests | Actual image build, complete dependency lock and signed release/SBOM |
| 02 Offline isolation | Loopback-only network namespace preflight with 5 synthetic tests | Real Docker network and ephemeral runner verification, host firewall policy |
| 03 Gitleaks | Ephemeral clean/secret synthetic Git-history qualification script; no test secrets committed | Execute against pinned Gitleaks binary and verify correct CLI flags |
| 04 Opengrep | 8 positive/negative language fixtures, including spoofed sanitizer tests; intrafile taint flag; no generic TypeScript sanitizer exemption | Execute against real Opengrep, qualify Rust coverage and all rule syntax |
| 05 DLP | Validated NHI and Medicare recognizers with 5 synthetic tests; model and checksum gates | Production Presidio/GLiNER integration, PHI recall and false-positive evidence |
| 06 Agent boundaries | Explicit input/result sanitization, normalized tool exceptions; regression first exposed an unsanitized tool response and exception and both were fixed | Integrate into actual agent ingress, retrieval, MCP, logs and egress |
| 07 Local red-team | Repo-scoped real-agent Python Promptfoo provider and integration configuration; 5 provider tests | Actual local agent adapters, adversarial corpus quality, pinned CLI |
| 08 Estate rollout | Retained 175 draft consumer PRs; central PR #126 updated, no merges | Two protected repository exceptions, repin after central qualification |
| 09 Evidence | Updated README and granular Conductor receipts | Publish value-free SARIF and audited aggregate receipt |

Local unit-testing evidence: 29 checks passed across asset integrity, network namespace, synthetic identifiers, agent-boundary behavior and constrained provider loading; three additional focused shell AI-detector tests passed locally. These tests use synthetic fixtures; they do **not** prove model PII recall, production agent boundary coverage or real scanner binary execution.

A negative TDD run caught two cases in `guarded_invoke`: returning raw tool output and propagating a tool exception with unmasked contents. The implementation now sanitizes the sink result and suppresses unsafe exception text. A separate AI-detector correction distinguishes an inspection error (exit 2) from a genuine absence of AI code (exit 1), preventing accidental skipping of conditional security checks.

**Remaining hard blockers:** preprovisioned vetted image/weights, real Opengrep/Gitleaks/Promptfoo and GLiNER qualification, end-to-end application interception, vulnerability review and branch-policy exceptions. The local image build recipe is not itself a built image or verified SBOM.

## Final local security hardening in this tranche

- Discovered and repaired an offline **data-leak channel via GitHub Actions logs**: Opengrep findings and Promptfoo outputs were previously emitted to standard output. The new `security/quiet_exec.py` executes scanner controls with stdout/stderr redirected to `DEVNULL`, emits fixed labels only on failure, and suppresses potentially sensitive exception/response text. Four synthetic local tests passed, including a failing child process that prints a synthetic canary.
- Required loopback-only namespace check, model asset hash verification and real Gitleaks positive/negative temporary Git-history qualification before repo scanning. No secret fixtures are committed for Gitleaks history testing.
- Strengthened Opengrep policy against **no-op sanitizer-name spoofing**. Only explicitly qualified Python sanitizer paths are accepted; TypeScript currently has **no approved sanitizer** pending a real implementation. Added two spoof fixtures and selected Opengrep `--taint-intrafile`.
- Fixed the fail-open AI-code classification path: detector now returns 2 on Git inspection error, and the orchestration aborts rather than silently skipping AI stages. Three additional local shell regression tests passed.
- Added tests and wiring for all new modules. In total **36 distinct local focused tests passed** in the development sandbox across the Python boundary, asset verifier, local agent provider, clinical identifiers, network isolation, quiet executor and shell AI detector. This excludes unverified real Opengrep/Gitleaks/GLiNER/Promptfoo integration and no whole-repository test-suite pass is claimed.
- Real-model GLiNER, Opengrep and Gitleaks fixture checks are **not verified** until the pinned scanner image and pre-provisioned model assets are made available to the self-hosted runner.

**Risk register:** CI logs must never contain raw findings, snippets, model responses, prompts, PII, PHI or plaintext secrets. The runtime intentionally returns only coarse control-failure labels. A privacy-safe count/receipt format can be added after integration, without exposing matched values.

## Cross-language DLP and regression evidence

Completed in this tranche:

- Added a local, private Unix socket `security/dlp_socket.py` broker, wrapping the Python sanitizer for other native runtimes, with 1 MiB payload limits, 0700 parent directory, 0600 socket, duplicate JSON-key rejection and fixed value-free error responses. Seven broker tests passed.
- Added Node.js + TypeScript-compatible, dependency-free `clients/node/dlp-client.mjs` / `.d.mts` with strict socket path, timeout, payload/response caps, transport failure and no HTTP. Five Node tests passed.
- Added Rust `clients/rust/` typed `serde_json` Unix client and tests, **not compiled in this environment**; exact dependency and Cargo.lock qualification remain open.
- Added an actual Python broker↔Node client process interoperability fixture, with two passing synthetic tests, including a value-free rejection response.
- Added deterministic seeded checksum metamorphic tests for AU Medicare and both NZ NHI formats (2,400 generated input cases plus mutations), all three pytest tests passed.
- The central scanner's `run.sh` includes Python broker tests, Python↔Node interop, standalone Node tests and identifier property tests as required controls.
- The isolated privacy wrapper `security.quiet_exec` removes raw findings, tool outputs and stack traces from GitHub CI logs; its four regression tests passed.
- The local focused regression run passed **48 Python tests and 5 Node tests**. It used a test-only DLP stub for socket/boundary checks. It does not establish real GLiNER/Presidio integration recall or prove Rust correctness.

Outstanding mandatory qualification:

1. Fully validated image, actual Gitleaks/Opengrep/Promptfoo CLI and Presidio/GLiNER model tests.
2. Real agent, retrieval and MCP adapters in each application; no automatic instrumentation is claimed.
3. Rust `cargo test --offline --locked` and TypeScript consumer integration with a live model-backed socket server.
4. Deployment on a hardened ephemeral, private, self-hosted runner with measured network isolation and log review.
5. Two GitHub repository policy exceptions, repinning 175 consumer callers to the final qualified central commit, and merging only after checks pass.

## Qualification tooling repairs — 2026-11-15

Follow-up for `unimelb-thesis-template-typst` PR #9:

- Replaced the partial manifest with schema 2, requiring complete inventories of
  supplied scanner binaries, locked wheels, Promptfoo files and model files.
  Verification runs against the vendor bundle before Docker, and against image
  paths before package installation. Unlisted files, tampering, path aliases and
  unsafe links fail closed. The manifest still requires independent approval.
- Added `docker/qualify_image.py` to execute eight real runtime, network,
  manifest, asset, Gitleaks, Opengrep, model and Promptfoo controls against a
  local digest-pinned image. All stages use one exported immutable policy
  snapshot and explicit container entrypoints. Private outcome receipts retain
  failed and unexecuted stages and container-cleanup results without raw output.
- Added `scripts/qualify_model.py`, which requires the three exact real-model
  tests and every setup/call/teardown phase to pass. Skipped, deselected, missing,
  extra or incomplete tests cannot qualify the model. Pytest configuration,
  plugin autoload and inherited options cannot alter the intended test set.
- Repaired consumer-directory Python import shadowing: the trusted quiet
  wrapper and its child controls use safe-path mode. Three process regressions
  reproduced false success before the fix and passed after it on Python 3.15.1
  and 3.15.2.
- The Python 3.15.2 policy command
  `PYTHONPATH=scripts .venv/bin/python -m unittest discover -s tests -v` completed
  with **186 tests: 151 passed and 35 existing capability-dependent skips**.
  This includes 7 asset-preflight, 11 image-orchestration, 12 model-orchestration
  and 3 trusted-Python regression tests. An additional 57 focused asset cases
  passed on both Python 3.15.1 and 3.15.2. Eight synthetic real-pytest protocol
  scenarios confirmed acceptance of complete passes and rejection of skipped,
  errored, incomplete or unexpected model-test execution.
- Restored the consumer's disabled Typst CI and executed it on PR #9 head
  `52b9ce77354183fcfe7c4a663a3901b6665e702c`.
  [Run 43608782761](https://github.com/edithatogo/unimelb-thesis-template-typst/actions/runs/43608782761)
  passed all four profiles (default, draft, print and screen), including
  formatting, compilation and PDF validation. Repository runner settings showed
  no configured self-hosted runners; this build does not qualify offline scanning.

The orchestration tests use fake Docker or synthetic pytest reports. No actual
scanner image was built or qualified, no approved asset bundle or model was
supplied, and no runner was registered. Steps 01–09 remain incomplete. The
central rollout and consumer PR #9 remain draft until their real qualification
gates pass; this tranche does not authorize a qualified-release claim or
consumer merge. Existing application-adapter and Rust qualification gaps remain.

## Runtime provisioning continuation — 2026-11-15

- Reconciled source repair PR #140: merged into the existing rollout branch at
  `0523a1d450476f5e49265f9ec1c888691e1b4884`, with successful source checks and
  the fix branch already pruned. Central PR #126 remains draft.
- No remote device was connected at this checkpoint. The development workspace
  had no container engine or writable cgroup controls and subsequently became
  unavailable. It was not registered as a security runner.
- Added independently pinned upstream acquisition and a separate metadata-only
  candidate-lock workflow. Missing reviewed locks fail preparation before any
  download. Generated candidates remain unreviewed until their complete hashes,
  versions and provenance are checked and committed.
- Repaired the native GLiNER model format and selected a built-in, local-only
  Deberta uni-encoder path. Preparation converts the verified tensor checkpoint
  to safetensors and supplies its complete local tokenizer/encoder configuration.
- Added actual container-state checks for non-root identity, zero capabilities,
  no privilege escalation, read-only policy/root mounts and finite cgroup-v2
  memory, process and CPU limits. Requested Docker flags alone are insufficient.
- Added hosted preparation followed by network-denied Docker build and the real
  image controls. Evidence retains exact source/image/manifest identities.
  Binary registry export was subsequently withheld pending the redistribution
  review recorded below. Hosted success cannot register a runner or qualify the
  central release by itself.

Eleven native-model contract tests passed on Python 3.15.2 before the workspace
connection was lost. The combined source and subsequent preparation/container
regressions require hosted verification; no image/model execution result is
claimed by this source checkpoint. Requirements 01–09 remain open, including
real self-hosted runner eligibility, host isolation, vulnerability review and
applicable application/language qualification. Consumer PR #9 remains draft.

## Reviewed preparation follow-up — 2026-11-15

The workspace recovered and Python 3.15.2 was restored. The combined policy
suite initially reproduced a stale image-test failure marker left after the
runtime check became `security.verify_container`; correcting the marker restored
the required failure-path coverage. The first hosted policy run reproduced that
same defect. Its privacy and Actions-security checks passed, and
[candidate run 43651617676](https://github.com/edithatogo/repository-standards/actions/runs/43651617676)
completed using Python 3.15.1. Its three public candidate files were reconstructed
from retained chunks and verified against their exact byte lengths, SHA256 and
Git blob identifiers.

The first image run reached the Docker host and failed at upstream preparation
with the expected unreviewed-lock catalog. Its retained execution receipt keeps
release, runner and application qualification false. No scanner execution is
inferred from that attempt.

The follow-up also requires byte equality between the selected policy workflow
and the calling commit after normalizing only the single immutable policy SHA.
Regression cases reproduced the old acceptance of changed container entrypoints
and network flags, then verified rejection. Model preparation now preserves
private fixed-stage failure receipts, pinned model cards and associated
source-code license texts, with exact attribution hashes and explicit scopes.

The reviewed dependency commit retains all 21 shared privacy pins/hash sets and
verifies all 18 additional Python releases and 603 unique npm releases against
upstream metadata. Four exact transitive npm overrides resolve the reported
advisories; the final npm audit reports zero known advisories. The committed
`security/offline-ai/provision/dependency-review.json` binds the reviewed lock
bytes and records the source checks, advisory dispositions and remaining real
execution gates. Native optional packages remain included without lifecycle
scripts, with a silent libsql/esbuild execution check during preparation.

The integrated Python 3.15.2 policy suite completed with **250 tests: 215 passed
and 35 existing capability-dependent skips**. It includes 19 container-control,
12 immutable-source, 13 vendor-preparation and 9 model-preparation cases. Shell
syntax and diff whitespace checks passed. These source tests do not substitute
for the required Python 3.15.1 model and image execution.

Central PR #145 contains this preparation work. Central PR #126 and consumer
PR #9 remain draft while real image execution, image vulnerability review,
isolated self-hosted runner eligibility and applicable integration gates remain
open. No runner has been registered and no consumer pin has been changed.


## First hosted preparation result — 2026-11-15

[Run 43653722717](https://github.com/edithatogo/repository-standards/actions/runs/43653722717)
passed the actual binary downloads, Python wheel installation and dependency
check, Promptfoo native SQLite/esbuild smoke, and model export on Python 3.15.1.
The retained model receipt records GLiNER 0.2.30, CPU Torch 2.15.0+cpu,
Transformers 5.22.2, safetensors 0.8.0, sentencepiece 0.2.3 and protobuf 7.36.2.
Its tokenizer export is 16,034,016 bytes, within the existing 16 MiB limit.
Model inference and scanner-image qualification remain separate unexecuted gates.

Preparation then failed during manifest finalization. The wheel builder puts
uv's one-byte build-only metadata beside its wheels, which the strict flat
wheelhouse verifier rejects. The follow-up stages the exact three expected
regular wheels from temporary build output. Unexpected and aliased outputs
remain rejected, and the complete manifest verifier is unchanged.

The same source increment adds a checksum-pinned Grype collector for the exact
qualified image, retaining the complete findings, internal suppressions,
database provenance and hashes with review and release qualification false.
Pin-only workflow changes now trigger image qualification. The repository permits
squash merges, so a receiving squash source requires a subsequent pin-only PR;
the ancestor and source-byte checks remain in force.

The Grype source increment completed the Python 3.15.2 policy suite with 265
tests and 35 existing capability skips. The three additional wheel-staging
regressions were published after the workspace disconnected; their final local
completion was not observed. The combined source requires hosted validation.
No runner or consumer has been activated.

## Actual controls and packaging correction — 2026-11-15

[Run 43655829149](https://github.com/edithatogo/repository-standards/actions/runs/43655829149)
passed complete preparation and the strict manifest check, built the image
without build network access, and passed seven actual controls: runtime
restrictions, network preflight, manifest binding, asset verification,
Gitleaks fixtures, Opengrep fixtures and the required real-model DLP tests.
The receipt binds policy `f44ec9e4c1e1fb28f70292b73ab3c6dd31469c22`, manifest
`f83008306612aeeb980cb6d6813c58639563ac9eb358539221c88c9ad8c5a25e` and image
`sha256:b460fc731abe0f09a7880e6bc726965e711bc67a4757d17132f9d4f86aa405a9`.
The artifact's full SHA256 was independently verified. Promptfoo mock evaluation
failed, while container cleanup passed; inventory and vulnerability collection
did not run after that failure.

The exact Promptfoo release and its Node/Commander parser confirmed that all
three eval invocations used an unsupported progress option. They now use
`--no-progress-bar`. The regression first failed on all three old calls, then
passed; full local Python 3.15.2 validation completed 269 tests with 234 passes
and 35 existing capability-dependent skips. The pinned Python wrapper also
executed all four configured mock cases successfully. Full image execution
remains required after the correction.

The subsequent bounded packaging review identified missing attributable license
notices for the pinned Gitleaks and Opengrep binaries. Their exact upstream
license texts and source records are retained in the policy and copied into the
image. This does not establish complete binary-redistribution qualification.
The optional image/registry archive is therefore no longer produced or uploaded;
the artifact retains execution receipts, the manifest, inventory and advisory
evidence. The approved host must build from the verified inputs, qualify its own
actual digest and manifest, and obtain SPDX and vulnerability review for those
bytes. Existing runner, release and applicable integration gates remain open.

The pinned SBOM action was also found to retrieve an installer from a mutable
upstream branch. A bounded collector now downloads the exact Syft 1.57.1 Linux
amd64 archive (31,432,061 bytes; SHA256
`bf52519eb57f675d47c07d43213cb6dff6449f3d6d1147ff6701ed91f44eef0c`),
verifies those bytes and runs no installer script. It records private SPDX,
configuration, version and provenance evidence, binds the described container
to the local digest, and retains the prior squashed-image inventory scope.
The existing Grype collector still inventories vulnerabilities across all
layers. Thirteen focused source tests passed; the full Python 3.15.2 source
suite completed 282 tests with 247 passes and 35 existing skips. These fixture
tests do not replace actual Syft execution, image review or runner qualification.


## Actual image qualification and image review — 2026-11-15

Runtime preparation PR #145 merged into this draft rollout branch at
`3c47f49719a7c862c4a4870955303db2f4b2b55d`; its receiving tree exactly matches
tested head `258b590d01506da42c7113fc17eac992fab803d5`. Its branch was deleted
and that deletion verified. All current source checks passed. Local and hosted
policy validation recorded **282 tests: 247 passes and 35 existing capability
skips**.

[Image run 43660592619](https://github.com/edithatogo/repository-standards/actions/runs/43660592619)
passed all eight actual image controls, including the required real model tests
and corrected full Promptfoo evaluation. Cleanup, checksum-pinned Syft inventory
and Grype evidence collection also passed. The complete 58,000,358-byte artifact
14140484647 was downloaded and independently verified against SHA256
`a6045446103e66dd410340342858b0c9366e8f4da83f5df20b1f53a67d1304c8`.
Independent read/hash checks confirmed policy, image, manifest and both report
identities. The database file itself is not included in the artifact; its hash
is a collector observation. Exact identities and findings are retained in
`security/offline-ai/provision/image-review-baseline.json`.

The full-image report contains **3,246 package/advisory matches** (748 distinct
advisory IDs) and 1,985 scanner-internal suppressions. It is not a passing
vulnerability disposition. The reviewed Promptfoo lock's zero-advisory npm
audit did not cover the global npm copied from the base image. The image review
identified concrete fixes for the full Debian base, unused global npm, Python
patch level and the released Gitleaks compiler/module closure.

The continuation preserves all-layer evidence, source ancestry/byte checks and
separate runner/release gates. Python 3.15.2 fixes two reported Python advisories;
its remaining socket and HTTP issues stay explicit. Any rebuilt Gitleaks module
candidate must be fully reviewed before use. The approved isolated host must
qualify and review its own actual image and manifest. Central #126 and consumer
#9 remain draft; no runner was registered and no consumer pin changed.

## Innovate hosted Ubuntu canary — 17 November 2026

At the user's direction, chat `01a1e448-3a28-7653-a681-cd3fdb41f498` owns
this bounded candidate in `/Volumes/PortableSSD/GitHub/repository-standards-innovate44`,
branch `codex/innovate44-offline-hosted`, based on
`b623faeb6e4588fba5882c0e711080a73408f939`. Allowed source paths are the
Innovate hosted canary workflow and this track record. Native/authentication
scope: none; checkout tokens are not persisted or passed into the scanner.
Existing offline rollout and image-advisory branches retain their owners and
are not modified. The next operation is a single hosted, evidence-only consumer
canary against Innovate head `fab4343b009e933ada4ed6460b20c336d1e5beed` and base
`cc2e4da4af9c848043b31f1191c9d96212048276`, using the existing candidate's
immutable policy selection, online verified preparation and offline image
controls, followed by the actual consumer scan with container networking denied.

The canary is not a replacement for Innovate's queued offline-security gate and
cannot establish image, vulnerability-review, release or consumer qualification
by itself. It retains the image-control, SBOM and all-layer Grype receipts without
exporting the image or vendor bundle. Prior hosted evidence reported 473
package/advisory matches and one scanner-ignored match; a fresh image and report
must be reviewed rather than reusing those findings as an acceptance decision.
The scientific release gate and central PRs #126 and #147 remain open.

Local Python 3.15.2 actionlint and boundary assertions passed; the latter also
rejected removal of network denial, a writable consumer mount and disabled pip
offline mode. The staged real Presidio/Gitleaks guard scanned both changed files
without findings or skips. The documented full policy suite ran 316 tests on
macOS arm64 and failed with five failures, 26 errors and 24 capability skips;
it is not a pass. One focused SBOM fixture reproduced a failure because the
unchanged collector requires Linux x64 at preflight. The same collector sources
and tests are byte-identical to the earlier hosted Linux policy job for `b623faeb`,
which passed; the new head still needs its own hosted Linux checks. No container,
model or consumer execution is claimed from this local run.

A managed-worktree request for the verified shared checkout and base did not
return and was cancelled; readback showed no attached artifact or additional
Git worktree. This lane reuses its existing isolated clone and does not claim an
app-managed worktree. The merged privacy branch remains preserved separately.

### Tracked-source SAST coverage follow-up

Chat `01a1e448-3a28-7653-a681-cd3fdb41f498` owns the bounded coverage
correction in this checkout, based on `21fa8674305687671988a2cdb12b1846bbec1a67`.
Allowed paths are `security/offline-ai/scripts/scan_opengrep.py`, its focused
tests and fixture qualification, `security/offline-ai/run.sh`, the exact-hosted
canary's consumer SHA, the required runtime-policy pin and this track. Native and
authentication scope: none. The next operation is an explicit tracked-source
inventory and fail-closed scanner result check, retaining the pinned rules and
their positive and negative controls. Source discovery, parser coverage and
finding review must each succeed; listing a path as scanned alone is not proof of
complete parsing. An uninitialized Git submodule is outside the parent index's
source inventory and is not represented as scanned. A materialized submodule must
not be silently ignored. Image-vulnerability review and release qualification
remain open.

The current local probe on Innovate `74a4d0690636ca9f6e445b4d778b5e2f6488234d`
enumerated and reported all 888 supported parent-index files, with one
uninitialized submodule outside that scope. Opengrep returned seven findings,
one partial-parse report and 46 per-file parser failures; this is a failing
scan, not complete coverage. An independent review reproduced omitted tracked
dotfiles and a false clean on an unresolved LFS pointer. The candidate includes
those dotfiles, rejects LFS pointers and unreported files, and verifies parser
status per target. It also independently compiles Python for syntax and uses the
existing hash-inventoried esbuild binary to check JavaScript/TypeScript syntax;
neither executes consumer code. Synthetic real-tool controls cover a clean
Python/JSX/TypeScript set, an ignored tracked finding, bare dotfiles and eight
invalid syntax cases. Eight focused wrapper tests passed on Python 3.15.2.
These controls do not prove complete Rust parsing or authorize an exemption for
the 46 failures. Hosted Linux validation remains necessary.

Actionlint and shell/Python syntax checks passed. A 47-test shared-policy run
passed 46 tests and failed one on macOS because the synthetic expected path used
`/var` while the tested resolver returned `/private/var`. An exact rerun with a
resolved temporary root passed; the initial run is not represented as an
unqualified 47-test pass. The hosted Linux policy and scanner runs remain open.

An isolated Python 3.15.2 experiment built tree-sitter 0.26.1 from source and
installed its Rust grammar 0.24.2. It parsed the affected faer file and rejected
synthetic malformed input and an LFS pointer; this is a local feasibility probe,
not a pinned scanner dependency or proof that Opengrep analyzed the same syntax.

### Rust rule-boundary follow-up

The same chat and checkout own a bounded follow-up based on
`4fb29296743fc4ca8610ae30ff0aef7891b9f76e`. Allowed paths additionally include
`security/offline-ai/.opengrep/rules.yaml`, the Rust SAST fixtures, the fixture
verifier, this track and the subsequent runtime-policy pin. Native scope: none.
The next operation is to cover reproduced direct-log bypasses involving Rust
raw identifiers and logging-macro spellings without changing existing controls.
A proposed rule for `use std::env` was not retained: independent review showed
it falsely flagged valid code where an unrelated local module shadowed the
import. Imported and function aliases and macro-definition expansions remain
reproduced gaps; this change is not complete Rust dataflow coverage.

The corrected direct rule detects raw identifiers, raw logging macro names,
generic calls, parenthesized function items and a quote character before the
source. Line-specific real-Opengrep controls and the existing clean/comment
controls passed; all new Rust fixtures compiled with Rust 1.99.1. A separate
local feasibility test ran Semgrep core 1.185.0 against all 745 tracked Rust
files with the same rule file and no reported errors or findings, and it passed
the bounded Rust positive/negative controls. It also accepted 11 of 51 invalid
Rust mutation inputs, so its parse status alone is insufficient. Its native
binary, dynamic libraries, syntax gate, licensing and image scan are not
qualified; it has not replaced Opengrep in the image.

Hosted run `44045133378` on policy head `4fb2929` and Innovate `74a4d069`
passed image controls, immutable policy export, network denial, secret history,
SAST fixtures and the wrapper tests, then failed the actual Opengrep consumer
scan. The hash-verified image artifact `14311941384` contains 484 advisory
matches, including 14 critical and 150 high, plus one scanner-ignored critical
match; its vulnerability and release qualification flags remain false.

### Unreviewed Gitleaks dependency candidate

The same chat and checkout own the bounded source-build candidate follow-up
against `21fa8674305687671988a2cdb12b1846bbec1a67`. The allowed source paths
also include `security/offline-ai/provision/gitleaks-build-sources.json`,
`security/offline-ai/provision/gitleaks_candidate.py`, its focused tests and
this track. This is candidate preparation only: it does not install or publish a
binary, alter the image, approve advisory dispositions or qualify a release.
The next operation is to resolve fixed candidate versions for the four modules
identified by version-level advisory queries, retain exact checksums and run the
existing isolated build and fixture workflow. The earlier candidate's build and
fixtures passed, but its four module version matches require a new candidate and
fresh whole-closure evidence.

The local Go 1.27.4 resolution selected 203 modules and exactly the requested
versions, including rardecode 2.4.6, x/crypto 0.59.0, x/sys 0.50.0 and x/text
0.44.0. The initial offline cross-build probe failed because it had not populated
the complete module cache; it is not build evidence. The candidate's 12 focused
source-build tests passed. The full closure, Linux binary controls and image
scan remain required before this can replace the current upstream binary.

Two independent hosted candidate builds completed with identical binary and
module metadata hashes; their clean/canary controls passed. A fresh OSV query
returned no version matches for the 65 compiled Go modules, Gitleaks itself or
Go 1.27.4, while the older-Go positive control returned 48 matches. A separate
query of all 202 downloaded modules found seven with version-level advisories;
none appeared in the compiled module list. Their disposition and the complete
licence/source obligations remain review work. No rebuilt binary was installed
in the tested image.

## Hosted canary scanner correction — 17 November 2026

The same chat and isolated checkout own the follow-up to hosted run
`44014472493`; the bounded allowed paths now also include
`scripts/secrets_scan.py`, `tests/test_secrets_scan.py`,
`privacy/reviewed-findings.json`, `privacy/reviewed-findings.md`, and the
single runtime-policy pin in `.github/workflows/reusable-ai-sec-pipeline.yml`.
The branch still starts from `b623faeb6e4588fba5882c0e711080a73408f939`;
existing provider, image-advisory and central rollout owners retain their work.

That hosted Ubuntu run passed eight image controls and failed the actual consumer
at Gitleaks history. Its retained fresh all-layer image report had 485
package/advisory matches, including 14 critical and 141 high, and one additional
scanner-ignored critical match. The image remains unreviewed and unqualified;
no waiver, image export, consumer promotion or release qualification follows.
Preparation accessed the network. The scanner container used `--network none`.

The scanner correction preserves offline safe-directory isolation and integrates
the already merged shared privacy registry and merge-history handling. Fifteen
additional exact Innovate matches are public file or log SHA-256 digests, each
independently recomputed from the corresponding immutable commit and recorded by
complete finding identity. Distinct values and duplicate contexts remain
blocking unless independently and unambiguously reviewed. Git environment,
replacement and graft settings, shallow and incomplete clones, binary diff
attributes, repository fsmonitor and signature hooks have regression coverage.
The wrapper checks the selected Git producer before Gitleaks, refuses staged
binary or custom-driver diffs and fails on private scanner diagnostics. Its
separate checks assume the checkout, refs and index remain stable while scanning.

With the checkout-local Python 3.15.2 and Gitleaks 8.30.1,
`PYTHONPATH=scripts .venv/bin/python -m unittest tests.test_secrets_scan -v`
passed 57 tests, including the real-tool negative fixtures. The initial fake
scanner fixtures used an inherited `python3` pointing to Python 3.11 despite the
3.15.2 test runner. The fixture now explicitly uses the runner's interpreter;
all 57 tests passed again with `.venv/bin` first in `PATH`. `actionlint` passed
on the hosted workflow. The staged Gitleaks and Presidio guard with the
checkout-local `privacy-guard/venv` Python 3.15.2 selected and scanned all six
changed files with no blocking findings or skips. An initial run with the lean
`.venv` failed its Presidio step because that environment lacks the privacy
dependencies; it is not a successful privacy check. The full-history Innovate
remote-ref clone scan returned
15 reviewed nonsecret findings and zero blocking findings with the strengthened
Git history options. It took about 10 minutes on the local multi-core host;
the scanner's per-process timeout is raised from 10 to 25 minutes for the
four-CPU hosted container, within the existing 30-minute offline control limit.
This run preceded the final private-diagnostic check, so the exact immutable
candidate still needs a fresh hosted Ubuntu run. The canary adds an outbound IPv4
denial probe inside the consumer container; the probe has not yet been observed
on the hosted runner. Vulnerability disposition and the separate scientific
release gate remain open regardless of a canary result.

### Shared privacy and Python patch reconciliation

The same chat and checkout own a follow-up against candidate head `c646606`.
The older offline base still uses Python 3.15.1 in its local privacy action and
behavioral workflow, and its self-scan pins an older Python 3.12 action. Passing
those runs is not current Python 3.15.2 evidence. The bounded source scope now
also covers the privacy action/workflows, privacy locks, installer, notice,
review registry and docs, privacy wheel builder and tests, and the offline
vendor preparer, source hash catalog and focused vendor tests. Reconcile the
already merged shared privacy source at `c82b2658f6874127d05f825dbe9ed4747f146efd`
with the offline-specific builder and its integrity bindings. Preserve the
offline-only behavior and meaningful tests, and run the exact new source in a
fresh hosted build before drawing conclusions. The already-running `c646606`
canary remains a separate immutable evidence run.

The reconciled privacy source and recognizer reviews are taken from that merged
commit. The offline preparer now invokes its Python-3.15.2-only builder without
the retired version-selection flag, and its catalog binds the exact builder,
locks and upstream MIT notice. `tests.test_privacy_wheel_build`,
`tests.test_offline_vendor_preparation` and `tests.test_privacy_scan` passed 55
tests with the selected Python 3.15.2 privacy environment. A real macOS arm64
source build produced both Presidio compatibility wheels and PyYAML; the builder
verified the MIT notice inside each Presidio wheel. This local build is not a
Linux scanner image or a hosted consumer result. The real staged Gitleaks and
Presidio guard selected and scanned all 21 follow-up files with no blocking
findings or skips.

Hosted run `44020563460` on `c646606` built the image and passed its controls.
The new in-container outbound IPv4 probe reported denial. The consumer then
failed with exit 126 because `run.sh` is not executable and the canary invoked it
directly; the consumer scan did not start. The follow-up invokes the tracked
script through Bash. The retained value-free artifact `14300594394` has verified
SHA-256 `6a38fa6958219e80f43b6571fde075ec1ef7442c8a464b48ab8840e496d4ee45`.
Its all-layer Grype receipt records 485 matches, including 14 critical and 141
high, plus one ignored match; the report hash matches the receipt. Image review
and release qualification remain false. These observations neither approve the
image nor substitute for the next exact-source consumer run. A subsequent local
full-history scan with the final scanner and diagnostic handling again returned
15 reviewed nonsecret findings and zero blocking findings; its value-free receipt
is retained outside Git.

### Consumer policy snapshot continuation

The same chat and checkout own a follow-up from `cdf01f8`, limited to the
hosted canary, this track, a consumer-policy export helper, the shared snapshot
helper and focused tests, plus the separate source-pin update. Hosted run
`44022146249` passed the outbound network probe and Gitleaks history but failed
`sast-fixtures`.
Its value-free artifact `14302450484` has verified SHA-256
`ada1da776de05c2617acb221e2bdd7b2f21e2847e83fae50dceef9399d9ebe8a`;
its Grype report matches the receipt and again records 485 matches, including
14 critical and 141 high, plus one ignored match. Image review remains pending.

The image qualification's archived policy has no Git metadata; the consumer
instead mounted a Git worktree whose `.git` file names a host-only path.
On synthetic fixtures, the digest-verified Opengrep 2.0.0 macOS binary scanned
all 11 controls from the archived policy and found all seven bad fixtures. The
same policy with an unavailable host Git pointer returned an error and scanned
zero files. This local reproduction supports using the same committed, symlink-
rejecting Git archive snapshot for the consumer, but does not prove the Linux
container result. The new exporter checks the policy SHA and clean checkout,
refuses an existing destination and reuses the image qualifier's archive and
link checks. The archive is compared byte-for-byte with the committed Git tree,
permissions are made readable to the unprivileged container, and the qualifier
is loaded from committed source instead of ignored bytecode. The exporter and
existing image-qualification suite passed 20 focused tests, including hostile
Git attributes, inherited environment, fsmonitor, bytecode and umask checks.
With a synthetic Git checkout, the actual exporter and digest-verified Opengrep
2.0.0 scanned all 11 controls
from the exported snapshot, found all seven bad fixtures and found no good
fixtures. `actionlint` passed on the canary. The actual hosted consumer must
still be rerun.

The current Gitleaks rebuild candidate artifact `14302060049` has verified
SHA-256 `134925e0caaae74271472c727be7ded00e52b915c23aa924fa3c780749da8589`.
Its receipt reports a Go 1.27.4 build, verified module closure and a passing
synthetic fixture, while review, image and release qualification remain false.
An OSV querybatch of 65 compiled module versions and the candidate standard
library returned version-level advisory IDs for four packages: `rardecode/v2`,
`x/crypto`, `x/sys` and `x/text`. A known-vulnerable Go 1.24.11 standard-library
positive control returned matches. The value-free local receipt has SHA-256
`6e7e1f2dbfa928928c1c6bd015357a2da1efa67ecb4c70b0fc1cda37e453ddaa`.
These matches do not establish reachability, and the query did not cover Debian
or other image layers. The candidate is not an approved substitute for review.

### Alert 44 exact-consumer follow-up

The existing integrator in chat `01a1e448-3a28-7653-a681-cd3fdb41f498` owns
this checkout `/Volumes/PortableSSD/GitHub/repository-standards-innovate44`,
starting at `44fd2045ab6dc8cb359ff318dc3e0ebd68c4e20e`. The bounded scope is
the hosted canary's immutable Innovate commit, this record, and the separate
pin-only runtime-policy commit. The next operation is to rerun the hosted canary
for Innovate head `e2a3ce65f330252c9ad74b182a19a0e8cdb19418` without weakening
its scanner or image gates.

On the preceding shared head, hosted run `44051618007` passed image controls,
network denial, full-history secret scanning, SAST fixtures and scanner-wrapper
tests; the actual consumer scan failed at Opengrep. Artifact `14315055546` has
SHA-256 `461b6f5dc33e7db7cbe72f405d805fca39c8caa582d1803c5b722c068f3d30c5`.
Its SBOM and vulnerability receipt evidence hashes were verified. The all-layer
report retains 484 matches, including 14 critical and 150 high, plus one
scanner-ignored critical match. Vulnerability review and release qualification
remain false. Separate image-controls run `44051618055` passed its controls; it
does not qualify the vulnerable image or the consumer SAST result.

### Gitleaks image-candidate continuation — 18 November 2026

The same integrator owns this clean isolated checkout at base
`a32c1331f606dc620df9a3be4e45e96bc85bf2ea`. The bounded candidate scope is
the existing Gitleaks source builder, vendor preparation and focused tests,
the hosted qualification script and canary workflow, its provisioning README,
a hash-bound candidate lock, and this track. The runtime-policy pin may be updated only after the
source commit. Native scope is limited to the existing draft PR and its hosted
evidence runs; no consumer pin or required check is changed.

The retained all-layer report's three fixed critical Go matches and 19 high
standard-library matches identify `/usr/local/bin/gitleaks`. The independent
squashed SBOM also inventories the same package names and versions; that
name/version correlation alone does not establish exploitability. The earlier
source-build artifact `14316722318` is bound to commit `a32c1331` and its
GitHub archive SHA-256 is
`8b248e17ddc259d233e6d1b1c8496554af2edc1581996707632e26d20544dde0`.
Its 65 compiled module versions and Go 1.27.4 had no matches in the earlier
bounded OSV query; the 202-module downloaded closure and licence obligations
still require review. The next operation is an explicitly evidence-only build
using the frozen closure and binary hashes, followed by the existing real
image, offline-control and vulnerability collectors. The normal reusable lane
continues to use its current pinned source until the candidate is qualified.

The evidence-only option now verifies the rebuilt binary's exact size and
SHA-256 and the five frozen source/module metadata hashes before staging it in
the local candidate image. The default vendor path still selects the pinned
upstream binary. A negative control exposed a partial candidate binary left
after a later builder failure; the candidate path now removes it and the
regression passes. On repo-local Python 3.15.2, 56 focused builder, vendor,
export and image-qualification tests passed. Shell syntax, actionlint, Ruff
syntax/name checks and the existing offline Zizmor mode passed. The staged
Gitleaks/Presidio guard scanned all eight selected files without blocking
findings or skipped files. These local checks do not establish Linux image,
consumer SAST, advisory, licence or release acceptance.

Hosted consumer run `44237141011` tested policy head
`dcd6852ffebab75d23944a85292b7476590fb0a3`, exported source policy
`f0f5fb74fcb849352841fcf60eaa8466fc138ded` and Innovate
`e2a3ce65f330252c9ad74b182a19a0e8cdb19418`. Candidate image construction,
the eight image controls, policy export and network-denial execution passed.
The actual consumer failed at Opengrep, so the run failed and the lane is not
qualified. The separately passing image-controls run `44237141169` used the
default vendor path and is not evidence for the rebuilt Gitleaks candidate.

Artifact `14398112646` has verified archive SHA-256
`aad2a22404a2df5ad53475d32020892e4088fa6b2d8278556ea4bbfa97ab4199`.
Its asset-manifest, SBOM and vulnerability-receipt hashes were independently
checked. The image digest is
`sha256:7f8b4b4c09d6adae9e75b60a79f0ca8afc0b90d63e2d0dd833fb84478def6b12`;
the manifest binds the candidate Gitleaks binary to SHA-256
`be39829e02d116295fc8babe39cf60b25964d45c1c801869105022dfd4577ebe`.
The all-layer Grype report retains 451 matches, including 11 critical and
129 high, plus one scanner-ignored match. None of the report's matches names
the Gitleaks binary location; the previous report had 33 there, including
three critical and 21 high. The two report database hashes differ, so their
aggregate count difference is not by itself an attribution or vulnerability
disposition. The remaining critical matches name Debian curl, glibc and SQLite
packages. Preparation, scanner and review receipts explicitly keep image,
vulnerability, consumer and release qualification false. Source, licence and
advisory review of the candidate and complete consumer parsing remain open.

### Debian 13 hosted image candidate, 18 November 2026

Chat `01a1e448-3a28-7653-a681-cd3fdb41f498` owns the offline image candidate
in `/Volumes/PortableSSD/GitHub/repository-standards-innovate44` on
`codex/innovate44-offline-hosted`, based on
`8e303d11a81ce821ffb37893030ee0d91d07b93f`. Scope is the Python base and
Debian package locks, the provisioner's distro check and focused test,
the provisioning README, this record, the hosted canary's Innovate ref,
and the subsequent runtime-policy source pin. Native scope is the existing
draft PR #152 and its hosted evidence runs. The next operation is to build
the pinned Debian 13 candidate and run the same image, network, SAST and
all-layer vulnerability controls on Innovate PR #684 head
`ecaccce231a1aa53b46418df52bd2cf3cc4e8d85`.

The official Linux amd64 Python 3.15.2 slim Trixie image digest is
`sha256:fd2aef5e0d8438208de9fe154ab5b331a2428fc0c9838d41611e611fd7a80d85`.
The verified base dpkg status contains 88 installed packages and has SHA-256
`75b63974c853f59abf2575cbcb5d0ff8075b2c8fa9151318c0ec7a98dafbe7e2`.
The image contains Debian-fixed glibc and SQLite versions for three critical
matches in the Bookworm image. Debian still lists the candidate curl version
as affected by CVE-2026-19931. The candidate cannot be approved before the
full hosted scan, dependency review and actual consumer controls complete.

The three Debian package indexes were verified against signed InRelease
metadata using the official base's Debian archive keyring. The catalog
selects 33 complete runtime archives totaling 23,792,168 bytes. The exact
archive sizes, hashes and Debian control fields were independently read
back before installation. Catalog SHA-256 is
`911778e03cd76fe91c5d7290b246a5a7f9482e78bb5b4fee373443bf1a0af43a`.
All 14 OS package tests and 19 offline container control tests passed on
Python 3.15.2. The hosted canary must still install the closure with
networking disabled and verify the final package database.

### Alternate Rust scanner trial, 18 November 2026

Chat `01a1e448-3a28-7653-a681-cd3fdb41f498` owns this trial on
`codex/innovate44-offline-hosted` in the existing shared-policy checkout.
The starting head is `7565d57f27711f51fe23918227171e67e1f3bf60`.
Scope is the standalone trial helper, the existing Rust fixture expectations,
the hosted canary, this record and the subsequent runtime-policy pin.
The separate evidence step targets Innovate PR #684 head
`12c58c52ca2caed38ad54b93e562c5c0f9a1d4a2`. The existing consumer
Opengrep check and full image vulnerability collection retain their gates.

The macOS standalone Semgrep core 1.185.0 passed every required Rust rule
fixture, including the line-specific controls. It reported all 747 tracked
Rust sources with zero errors and findings. Independent Rustfmt checks with
the declared vendor editions accepted the previously rejected sources.
The Linux wheel is pinned by size and SHA-256. Its native dependency bundle
still requires advisory and licence review before production use. The next
operation is an isolated Linux x64 trial using the same fixtures, tracked
paths and read-only mounts, with network access disabled during scanning.

The trial helper verified the actual Linux wheel and all 27 native files,
and its local scan reproduced all nine Rust fixtures and 747 source reports
on Python 3.15.2. All eight existing scan-wrapper tests, actionlint and diff
checks passed. The Linux trial retains a value-free result with its source
head. The normal Opengrep and image results remain separate promotion gates.

### Runtime dependency and Rust syntax qualification, 18 November 2026

Chat `01a1e448-3a28-7653-a681-cd3fdb41f498` owns this draft update in
`/Volumes/PortableSSD/GitHub/repository-standards-innovate44`, branch
`codex/innovate44-offline-hosted` at
`5a19460ed556500e2791af3179ace797a6ef4dc9`. The affected paths are the
runtime base, its Debian and Git locks, the hosted provisioner and canary,
the Rust scanner trial helper, their focused tests and this record. Native
scope is PR #152 and its runs. Innovate head `12c58c52` remains the test
consumer. The next operation is to run the existing hosted controls with
the reduced dependency closure and the independent Rust syntax check.

The prior all-layer report lists eight critical and 23 high matches in
`libcurl3t64-gnutls`. Debian 13 has a signed update for the one other high
match marked fixed, CVE-2026-85091 in zlib. Build Git 2.56.1 without HTTP
transport and restrict the additional Debian packages to the two native
runtime libraries and the fixed zlib archive. Assemble the runtime from
the updated filesystem so the original zlib bytes do not enter its layers.
Retain the full all-layer report and compare it with the prior result.

GitHub verifies the signed upstream Git tag for commit
`03b41523c576f26ad34085378717a0c1b287470f`. The release archive signature
also verifies against the same signing subkey
`E1F036B1FEE7221FC778ECEFB0B5E88696AFE6CB`. The current OSV query for
that commit returned zero advisory IDs. The Linux image and its runtime
dependencies still require exact hosted verification.

The fixed zlib archive matched the size and SHA-256 in the signed Debian
security index. The source-built macOS Git reported 2.56.1, passed local
init, commit, history and index checks and showed no curl linkage.
The Rust trial used Rustfmt from Rust 1.100.0 and local Semgrep core
1.185.0. It passed the nine rule fixtures and all 747 tracked files.
The syntax check rejected six malformed controls. The 14 OS package, 19
container and eight scanner wrapper tests passed on Python 3.15.2.
Shell syntax, actionlint, Zizmor and diff checks passed.

Hosted image run `44303265564` failed at Git's default Cargo build because
the C build image did not contain Cargo. The digest-pinned official Rust
1.100.0 Debian 13 build image retains Git's default Rust code.

Hosted image run `44304345875` then reached Cargo and failed because
the signed archive omits `Cargo.lock`. The lock examined earlier came
from the local compile. A fresh extraction generated the same single-crate
lock offline with Cargo 1.100.0. Verify its SHA-256 before the hosted build
runs with `--release --locked --offline`.

### Gitleaks report permissions and scanner provenance, 19 November 2026

Chat `01a1e448-3a28-7653-a681-cd3fdb41f498` owns this packet in
`/Volumes/PortableSSD/GitHub/repository-standards-innovate44` on
`codex/innovate44-offline-hosted` at `018ecdcc4157ad268839737bae43185a2c71876a`.
The scope is the Gitleaks build catalog, report-permissions patch, candidate
builder and staging checks, their focused tests and documentation, this record,
and the runtime policy pin. Native scope is draft PR #152 and its checks.
Innovate PR #684 head `12c58c52ca2caed38ad54b93e562c5c0f9a1d4a2` supplies the
consumer for the offline run.

The Go 1.27.4 cross-build reproduced the original hosted Linux amd64 binary
`be39829e02d116295fc8babe39cf60b25964d45c1c801869105022dfd4577ebe` and all 606
downloaded archive, module and version metadata hashes for 202 modules.
The binary links 65 modules. The 19 November OSV review returned zero advisories
for those modules and the Go standard library. Seven downloaded-only modules
have matches. The embedded go-re2 v1.9.0 payloads match its release tree, whose
recipe identifies RE2 2024-07-02, Abseil 20240722.0 and WASI SDK 25. The query
for the Gitleaks release source returned CVE-2026-124039. The offline wrapper
already pre-creates its report at mode `0600` in a private directory.

Apply the two-call-site report-permissions change from the open upstream
[Gitleaks PR #2312](https://github.com/gitleaks/gitleaks/pull/2312) to the
verified 8.30.1 source archive. Verify the patch bytes and the original and
patched source bytes. Exercise new and pre-existing reports alongside the
existing clean and secret detection fixtures before staging the new binary.

The patched Darwin arm64 binary passed the clean and secret detection fixtures
and both report permissions cases. The isolated cross-build produced a
22,868,092-byte Linux amd64 binary with SHA-256
`7feb4384b376745ebe1e466bd0115acc18cfb74d30ad265c2539529602210e41`.
The lock requires this hash and the original dependency metadata before the
hosted run can stage the binary. The patch is sourced from an open, unsigned
proposal and independently reviewed against the pinned release bytes.

The Semgrep 1.185.0 Linux wheel has SHA-256
`0eb6aaadad5b957af96d1300487e10af1dc8016e8ef53072effb48cd4906c02b`.
The PyPI attestation identifies the publisher. For 24 of the 26 bundled
libraries, the GNU build IDs and allocated code and data sections match RPMs
from the AlmaLinux 9 and 9.8 BaseOS catalogs. The comparison verified the signing
key and the catalog, metadata and RPM hash chain. Those libraries differ in
their dynamic linkage metadata. The matched packages include
`libcurl-minimal-7.76.1-40.el9_8.8` and `openssl-libs-3.5.8-2.el9_8`.
`libtree-sitter.so.0.26` and `libunwind.so.8` remain untraced. This leaves the
wheel's native library provenance incomplete for image promotion.

The 19 focused Gitleaks tests passed on Python 3.15.2. A 173-test offline suite
run on macOS reported the same five failures and 26 errors at the starting
commit and with the patch. The affected tests exercise SBOM and vulnerability
evidence code that requires Linux amd64. Actionlint passed with the existing
`ai-security-offline` runner label configured.

### Integrate the verified scanners in the hosted consumer lane, 19 November 2026

Chat `01a1e448-3a28-7653-a681-cd3fdb41f498` owns this packet at
`3bb521b0c24a8d79d1fa84478253e919e98c091b` in
`/Volumes/PortableSSD/GitHub/repository-standards-innovate44`. Scope is the
hosted consumer workflow, its locked scanner assets and SAST runner, focused
tests, the runtime policy pin, and this record. Native scope is draft PR #152.
PR #684 head `12c58c52ca2caed38ad54b93e562c5c0f9a1d4a2` supplies the test consumer.

The EPEL 9 libunwind RPM signature, payload and executable sections verified
against the shipped library. Hosted run `44394142641` reproduced Tree-sitter
0.26.3 with the same build ID, executable and read-only data. Hosted run
`44396381026` loaded the eight signed AlmaLinux updates and passed nine
Rust rules fixtures, six malformed syntax controls and all 747 Rust sources.
Hosted run `44393030180` reproduced the report-safe Gitleaks build and passed
both mode-0600 fixtures. Use those assets in the full hosted consumer run.
Keep the parent Git index as the common inventory, run Opengrep on its existing
non-Rust languages and Semgrep plus Rustfmt on every Rust file, and fail on
any findings, parser error or coverage gap. Keep image vulnerability review
separate from the workflow's runtime results.

On Python 3.15.2, nine SAST wrapper tests and 19 Gitleaks candidate tests passed.
Reassembly from the independently verified wheel and signed RPM bytes matched
all 27 locked files. Verification rejected a modified library. Actionlint,
Bash syntax and Git diff checks passed. The hosted job mounts the exact
Semgrep bundle and Rustfmt read-only and retains a separate asset inventory.
The whole-image SPDX and all-layer Grype scans continue against the runtime
image's actual digest.
