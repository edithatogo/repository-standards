# Execution plan — Agent harness, context and change safety

## Incremental deliverables
1. Evolve AGENTS.md into testable instruction hierarchy and context-pack format: architecture, risk, owned paths, permissions, out-of-scope actions, local validation, rollback and evidence links.
2. Build benign/malicious corpus for prompt injection, tool-output laundering, secret exfiltration attempts, fake CI statuses, forged policy exceptions and unsafe auto-merge instructions.
3. Require agent-generated changes to pass exact-commit tests and static/security checks; disclose unsupported or unexecuted checks. Independent automated reviewer compares behavior, privacy and policy to explicit specs.
4. Add bounded token/context and tool-call budgets, provenance receipts, semantic-diff review and task-level capability gates.
5. Evaluate on repeated seeded canary tasks and publish false-pass, missed-finding and change-rework metrics without exposing sensitive contents.

## Implementation loop and review
For every numbered increment: define fixtures and negative controls, demonstrate failing tests, implement the minimum coherent change, run focused and full policy checks, perform independent automated security/behavioral review, fix findings, then verify hosted canary and exact-commit evidence. Update track status only after evidence; archive only after documented acceptance. Use scoped PRs, never force-push or bypass required checks.

## Owned paths (initial candidates; reconcile before edits)
- `AGENTS.md`
- `conductor/workflow.md`
- `docs/solo-maintainer-standard.md`

## Release gate
Attacks do not cause prohibited actions; test suite catches forged receipts and instructions; no secret values in logs; artifact can be reproduced at a declared commit; no second human required by default.

## Blockers and recovery
API forbidden, unsupported entitlement, unstarted runners, stale branch, unmerged consumer PR and nondeterministic test are explicit unresolved states. Maintain retry bounds and no-false-green accounting. Do not claim estate deployment when only central code passes.


## Local-model integration qualification — 26 November 2026

Cross-reference [F03 integration lane / issue #192](https://github.com/edithatogo/repository-standards/issues/192).
Build no new agent framework or inference service until the deterministic baseline shows
a need. Reuse the existing standards_check pinned ONNX and GGUF experiments where
compatible; keep optional model dependencies separate from the qualified policy runtime.

Candidate sequence (not yet qualified):
1. Classical log classification, lexical retrieval and native Git first.
2. One lightweight retrieval/reranking model (MiniLM or Qwen3-Embedding/Reranker-0.6B)
   if context selection fails; compare to lexical retrieval.
3. Existing MiniLM NLI ONNX and structured LiquidAI d1-2B decision experiment
   for separate preservation/routing diagnostics; licence and runtime checks first.
4. One small code-repair candidate (Qwen2.5-Coder-1.5B-Instruct or a measured successor);
   add alternative small reasoning models only for distinct failure classes. Independent
   counterexample generation is preferred to model voting; visual models only for
   actual rendering failures.

All inference runs locally from Hugging Face Hub weight snapshots (no Gemini,
Copilot, hosted model endpoints or proprietary inference APIs). Pin exact revision,
weight/tokenizer/config hashes, runtime and licence; prefer ONNX/safetensors/GGUF
without remote executable code. Download separately, verify assets, disable network
and telemetry for inference, limit resources, use typed output validated by trusted
policy. Models cannot access write tokens, invoke shell commands from output or
declare acceptance. No untrusted fork or private data on public receipts/runners.

Replay historical exact base/head pairs without exposing their accepted resolutions;
split calibration/evaluation by PR or repository, include synthetic harmful patches,
missing checks, forged receipts, injection and stale-base cases. Measure incorrect
acceptance and functionality loss before coverage, runner minutes and latency.
Keep model-relative findings advisory; independent tests and native protection
are authoritative. Record rejected candidates and abstentions. No automatic model
updates, training, extra GPU services or new dependencies until a bounded experiment
shows additional value.

### First local model experiment

Reuse the pinned StandardFlow CPU-only MiniLM NLI implementation from
d88f787ffd4647117bca4ca400cbb68d95197d40 (source blob da3b8f7712fe79536b8c33484f02a91d7f800645).
Independently verified original StandardFlow benchmark artifact 14925311073, archive
SHA-256 fe3cfa064cde26ba2dd3f8f1be53bb4137c5d071930df588644ae7eb2e805794,
provides the exact three Hugging Face asset hashes used by the new benchmark.
Download only those files, verify all bytes before model loading, execute on
a separate GitHub-hosted CPU job with a network namespace and scrubbed environment,
no write credential, and no external model endpoint. Top-level inference wheels
are pinned; the full transitive environment is retained, not yet hash-locked.
The benchmark compares exact matching with bidirectional NLI at the inherited
0.95 diagnostic threshold on 12 synthetic requirement-preservation cases.
The threshold is not PR-calibrated. Record false acceptances and false rejections;
never qualify merging or repair generation from this synthetic experiment.

Focused harness TDD: initial missing-module failure, four tests subsequently
passed under Python 3.13.5 using synthetic scoring stubs. Actual model inference
and qualified hosted suite are separate open gates. Candidate results determine
whether a second model or broader historical replay is justified. No inference
API, external upload, model authorization, or actual PR repair is introduced.

### Experimental execution and checksum representation

PR #195 tested merge e530bca75a2099dd260fa1ff83a828ce56dbeefc, source head
6ddc31f6adb73b1fb6ed182ac9d0210cd5455bb4. [CPU run 45785630295](https://github.com/edithatogo/repository-standards/actions/runs/45785630295)
successfully executed isolated, checksum-verified MiniLM inference. Artifact
15099364071 archive SHA-256 independently reproduced as
6cc4de4a6eafd3da760bbb1f1ec68225375e93e35248d006ae9b02868ad0b8e5.
At the predeclared diagnostic threshold, exact match classified 9/12 correctly;
NLI classified 11/12 correctly. Both had zero false acceptances among eight
synthetic nonequivalent pairs. NLI missed one of four equivalent pairs; the exact
baseline missed three. Model load plus evaluation 0.612 s; no claim of calibration,
production safety or generalization. Receipt explicitly denies merge qualification.

The candidate's independent privacy scan failed: Gitleaks generic-api-key on the
public tokenizer file checksum (line 19), not a credential, corroborated by the
prior verified StandardFlow receipt. Preserve #195 and the failed job 139791569450.
Use a conventional digest-first sha256sum-format manifest for public content
identifiers in a replacement candidate from unchanged main, with exact asset-name,
duplicate and digest-format validation. Do not alter Gitleaks rules or reviewed
finding policy, force-push, or treat the original failed run as passing. Five
focused local tests passed after adding a failing manifest regression; rerun all
checks and actual inference against the replacement candidate before integration.
The original inference receipt remains historical evidence only.

### 27 November 2026 — replacement qualification receipt

PR #196 original head 4cd4a1bbc5629e8a534b43cdab03a37744c2d431 passed all nine
observed checks, including both CodeQL analyses, the CodeQL alert gate, Zizmor,
policy, community, privacy and CPU benchmark. Its automated code review completed
without findings; no unresolved review threads. Policy job
[139793303833](https://github.com/edithatogo/repository-standards/actions/runs/45786154903/job/139793303833)
reported 372 tests, 38 capability skips, no failures (334 passed).
The [replacement inference run 45786154886](https://github.com/edithatogo/repository-standards/actions/runs/45786154886)
tested merge b05127c596143955070e361687fabfb083f61068. Artifact 15100047679 was
downloaded and its archive SHA-256 independently reproduced:

```text
8638338b6df23626c279af47c6d03ad4fcb714f1d2b53657e26e82b0ae1aff13
```

The receipt retains the same pinned model revision, three verified asset
hashes, fixture digest and threshold as the earlier experiment. Exact 9/12,
NLI 11/12; both zero false acceptances among eight designed nonequivalent
cases; three versus one false rejections. CPU model load and evaluation took
0.717 s (Python 3.12.16, ONNX Runtime 1.23.2); this is a repeated same-fixture
result, not independent validation or a latency benchmark. Transitive inference
wheels remain unqualified as a hash-locked closure. Merge authorization is false.
Preserve the draft #195 and its failed scan; do not count that revision as
accepted. Main advanced by the unrelated registry-only change; refresh #196
using both parents without force, preserve all executable blobs and require
current-head review and checks. No additional model experiment until this
integration gate is resolved. Future conflict and repair fixtures are synthetic
only under the owner's 27 November scope; no historical live PR replay, App
writes, automatic merges, or estate rollout.
