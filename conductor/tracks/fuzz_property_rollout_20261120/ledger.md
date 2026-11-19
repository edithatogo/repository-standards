# Public rollout execution ledger

Observation window: **19 November 2026 UTC**. This is a bounded record of the
approved consumer work, not a whole-estate conformance inventory. PR metadata and
GitHub Actions outcomes were read from their public repository endpoints. Local
results are implementation receipts; their toolchain and scope are stated below.
A linked successful targeted job does not make all checks on that PR successful.
StandardFlow PR #84 was merged externally at 20:21:05 UTC; its receiving-main
qualification has not been checked here. Other listed candidates remain open.
This coordinator has not merged any PR.

## Published candidates

Head links contain the complete observed SHA. `Passed` refers only to the named
job/workflow on that head, not to future commits, scheduled campaigns that have
not run, default-branch adoption or release acceptance.

| Repository / candidate | Exact observed head | Targeted hosted observation | Admission status / remaining gates |
| --- | --- | --- | --- |
| [foi-process #144](https://github.com/edithatogo/foi-process/pull/144) | [9781a1be0534](https://github.com/edithatogo/foi-process/commit/9781a1be0534e21f59aa90b47163fe4b3099f992) | [Current-head security-fuzz passed](https://github.com/edithatogo/foi-process/actions/runs/44607527370): replay properties and default-sanitizer libFuzzer smoke executed. Contracts also passed. | Completed-plan regression repaired without rewriting historical completion. Rust 1.88/feature-matrix compiler floors and the Chrono advisory pre-date this repair and remain open. |
| [kairos #398](https://github.com/edithatogo/kairos/pull/398) | [89c31a0b4838](https://github.com/edithatogo/kairos/commit/89c31a0b4838ebcd3d92dd71fce3673699ea92e8) | [Scheduler properties passed](https://github.com/edithatogo/kairos/actions/runs/44604639361/job/135844948808), with retained compiler/commit/test evidence. | Stable properties only. The separate cargo-fuzz/ASan obligation remains explicitly UNVERIFIED. All 19 observed workflows, including core and Conductor gates, passed on this head. |
| [careops-sim #217](https://github.com/edithatogo/careops-sim/pull/217) | [4dbb994d925f](https://github.com/edithatogo/careops-sim/commit/4dbb994d925fe5b03f4490617c26f13c4c3a3d8f) | [Stable parser mutation job passed](https://github.com/edithatogo/careops-sim/actions/runs/44605504979/job/135847987077), with retained evidence. | Stable shared-oracle execution; cargo-fuzz/ASan remains UNVERIFIED. Mandatory inventory/privacy checks passed after source registration; broader ci remains pending. |
| [dapane #35](https://github.com/edithatogo/dapane/pull/35) — draft | [ab15d239f24c](https://github.com/edithatogo/dapane/commit/ab15d239f24c1007933c5b8c2fb84b64f55d3bf7) | [Process models X2 passed](https://github.com/edithatogo/dapane/actions/runs/44605447430). | Rust 1.99.1 native tests and a completed local ASan campaign passed, with LeakSanitizer disabled only in the local environment. Integrator-owned schedule wiring and default-sanitizer hosted execution remain open; no shared workflow was reassigned. |
| [mailweft #26](https://github.com/edithatogo/mailweft/pull/26) — draft | [283b6b72593f](https://github.com/edithatogo/mailweft/commit/283b6b72593f3a7343fdce9b9471c15711399566) | [Bounded parser fuzzing passed](https://github.com/edithatogo/mailweft/actions/runs/44605938521). | Synthetic email/OCEL invariants and local ASan execution are recorded below. [Planning and contract checks failed](https://github.com/edithatogo/mailweft/actions/runs/44605938162); instrumentation and full-gate admission remain separate. |
| [CiteLattice #30](https://github.com/edithatogo/CiteLattice/pull/30) — draft | [a6e13f3ac76c](https://github.com/edithatogo/CiteLattice/commit/a6e13f3ac76c25c592a776d5adc775fb6735e58f) | [Bounded parser fuzzing passed](https://github.com/edithatogo/CiteLattice/actions/runs/44605963777). | Source/event ingestion invariants and local ASan execution are recorded below. Complete repository/consumer gates remain separate from the bounded campaign. |
| [archive-govt-nz #884](https://github.com/edithatogo/archive-govt-nz/pull/884) — draft | [331345ee1362](https://github.com/edithatogo/archive-govt-nz/commit/331345ee1362861fd7b13a69f47faa7401ef2b23) | [Generated archive boundary job passed](https://github.com/edithatogo/archive-govt-nz/actions/runs/44604687213/job/135845113210). | [Full CI failed](https://github.com/edithatogo/archive-govt-nz/actions/runs/44604687055) on six existing election formatting findings. PRs #866/#882 and coordinator #867 retain those paths. |
| [osf-cli-go #155](https://github.com/edithatogo/osf-cli-go/pull/155) | [4cf914bde73b](https://github.com/edithatogo/osf-cli-go/commit/4cf914bde73b3e58c822c64f7ee637525c5f5080) | [All seven provider mutation jobs passed](https://github.com/edithatogo/osf-cli-go/actions/runs/44605327703), including seed replay and evidence retention. | [ci](https://github.com/edithatogo/osf-cli-go/actions/runs/44605327725) hits the unchanged July 2026 provider-evidence freshness gate; [security](https://github.com/edithatogo/osf-cli-go/actions/runs/44605327510) remains with existing toolchain owner #152. |
| [rcagent #199](https://github.com/edithatogo/rcagent/pull/199) — draft | [364123679246](https://github.com/edithatogo/rcagent/commit/3641236792466abc89bb821917befd2a4033d75a) | [Synthetic property job passed](https://github.com/edithatogo/rcagent/actions/runs/44605619655/job/135848392289) and [hosted Quality passed](https://github.com/edithatogo/rcagent/actions/runs/44605619742). | Hosted platform validation/coverage passed; the local socket restrictions below are historical environment limits, not a current hosted failure. Offline security remains queued. |
| [mchs #418](https://github.com/edithatogo/mchs/pull/418) — draft | [d4b00389103f](https://github.com/edithatogo/mchs/commit/d4b00389103f0812adf5b6fe4ef12c67b580502a) | [Synthetic calculation property job passed](https://github.com/edithatogo/mchs/actions/runs/44605627036/job/135848420446). | Full dependency install encountered a killed NumPy compiler; full-suite, Rust, coverage and scientific gates remain open. |
| [tobac #177](https://github.com/edithatogo/tobac/pull/177) — draft | [a4dd271e3d6b](https://github.com/edithatogo/tobac/commit/a4dd271e3d6b1f6eba6da2550837c39d174f1d1f) | [Corrected-head accounting campaign passed](https://github.com/edithatogo/tobac/actions/runs/44607374832/job/135854570735). Initial-head success remains historical only. | Original signed noxfile restored byte-for-byte; separate nox_properties.py carries the campaign. Native interpreter/full qualification and broader hosted gates remain open; no signature or pin bypass. |
| [UOGTO #137](https://github.com/edithatogo/UOGTO/pull/137) — draft | [238bcc5d02e2](https://github.com/edithatogo/UOGTO/commit/238bcc5d02e2a856f7349bad4fc23c0a6ef0777d) | [Synthetic graph properties passed](https://github.com/edithatogo/UOGTO/actions/runs/44605941997). | Graph identity/payoff invariants do not discharge MAT04 scale or consumer acceptance. |
| [paignia #38](https://github.com/edithatogo/paignia/pull/38) — draft | [fca9799bb703](https://github.com/edithatogo/paignia/commit/fca9799bb703bfa52de05b7fa9a7ed9ee2e8933f) | [Corrected-head campaign queued](https://github.com/edithatogo/paignia/actions/runs/44609760946). The [earlier generated-game campaign passed](https://github.com/edithatogo/paignia/actions/runs/44606248674/job/135850593411) on `393d525f7aed`, retained as historical evidence only. | Introduced MSRV test-name lint repaired with descriptive variables; exact 1.75.0 formatting/default and all-feature Clippy/new tests passed again. Existing Rust 1.99.1 Clippy finding in owned `mixed_nash.rs` remains; fresh Native CI/offline security and consumer acceptance are separate. |
| [rac-conformance #195](https://github.com/edithatogo/rac-conformance/pull/195) — draft | [f3b8cd1fa1fb](https://github.com/edithatogo/rac-conformance/commit/f3b8cd1fa1fbcfef89cbe78d7e06f6bdb53266bb) | [PIC input-boundary campaign passed](https://github.com/edithatogo/rac-conformance/actions/runs/44606116060/job/135850139078), with case-labelled artifact. | Existing converter lint findings block full `make check`; policy/golden-fixture and release gates remain unchanged. |
| [standards_check #84](https://github.com/edithatogo/standards_check/pull/84) — merged externally | [647200238e3d](https://github.com/edithatogo/standards_check/commit/647200238e3d82993526afa306574c7d4c53f9b5) | [Canonical contract properties passed](https://github.com/edithatogo/standards_check/actions/runs/44606121446/job/135850163593), with seed/compiler/test artifact. | Foundation and canonical-pack workflows also passed on this PR head; offline security remains pending. Merged at [65adb34d2ffa](https://github.com/edithatogo/standards_check/commit/65adb34d2ffa5b2256100fa1796360e9092b2213); receiving-main qualification is unclaimed. PRISMA source, rights, migration and release gates remain open. |
| [authentext #348](https://github.com/edithatogo/authentext/pull/348) | [a098c3195537](https://github.com/edithatogo/authentext/commit/a098c319553718519955e3e8873ffc4a84c4cff5) | [CI passed](https://github.com/edithatogo/authentext/actions/runs/44605372196), including Node tests and coverage. | [Windows skill-distribution retry failed](https://github.com/edithatogo/authentext/actions/runs/44605372419/job/135855675949) during Vale download with repeated Chocolatey HTTP 503; package metadata resolved. Other checks passed; no introduced test defect was identified. |
| [innovate #694](https://github.com/edithatogo/innovate/pull/694) — draft | [c909bc448113](https://github.com/edithatogo/innovate/commit/c909bc4481131f4f9578512acb50dc9b22aff5bb) | [Continuous Fuzzing queued](https://github.com/edithatogo/innovate/actions/runs/44608223968). | Pinned nightly/cargo-fuzz, refreshed isolated lock, locked/offline preflight, bounded PR/weekly runs and logs are implemented. Native campaign execution is pending; compiler/policy checks are not fuzz execution. |
| [sourceright #144](https://github.com/edithatogo/sourceright/pull/144) — draft | [5987aa245de2](https://github.com/edithatogo/sourceright/commit/5987aa245de286fe7622d4d0fe1627fac13817fc) | [Updated-head Robustness pending](https://github.com/edithatogo/sourceright/actions/runs/44609604816). The [earlier Robustness run was cancelled](https://github.com/edithatogo/sourceright/actions/runs/44608240958) on superseded `c439292cb32a`. | Existing CSL/sidecar targets now have pinned, bounded 30-second PR/300-second weekly execution and artifacts; the follow-up gives scheduled/manual jobs 25 minutes for both campaigns and cold builds. Two local release compilations were SIGKILLed; no local mutation loop or sanitizer pass is claimed. |
| [healthpoint-rs #113](https://github.com/edithatogo/healthpoint-rs/pull/113) — draft | [53a42d4562dc](https://github.com/edithatogo/healthpoint-rs/commit/53a42d4562dcba7955ff14ab98b8c2f4edc62c0e) | [Bounded parser fuzzing queued](https://github.com/edithatogo/healthpoint-rs/actions/runs/44609107371). | Final native tests/preflight passed. An earlier instrumented draft was killed after 21,548 inputs and is not a pass or final-harness qualification. Exact-head sanitizer execution and broader gates remain open; the existing Smithery workflow reports a failure. |
| [fe-reader #51](https://github.com/edithatogo/fe-reader/pull/51) — draft | [ad3bb182a182](https://github.com/edithatogo/fe-reader/commit/ad3bb182a1829ef780bef6e87cd446d74462a765) | [Bounded parser fuzzing queued](https://github.com/edithatogo/fe-reader/actions/runs/44609120048). | Actual PDF native tests and lifecycle/architecture/schema checks passed. No completed local sanitizer campaign; full required gates remain open. The new campaign remains advisory under existing policy, so inspect its execution step/log before counting a pass. |

## Local execution receipts and limits

- **FOI process:** the latest registry validator, four focused tests and the
  security-fuzz contract check passed locally after preserving the completed
  plan. The latest head ran replay properties and default-sanitizer libFuzzer
  smoke in hosted CI. The remaining Rust 1.88/feature dependency floors and Chrono
  advisory were checked against the pre-repair source; they are separate gates.
- **Kairos:** Rust 1.99.1 executed seven existing scheduler property/negative-control
  tests. Track metadata validation passed. The old UNVERIFIED cargo-fuzz marker
  remains, alongside the new real stable execution.
- **careops-sim:** Rust 1.99.1 executed four tests, including 17,417 prefix/byte
  mutation inputs, 12 admitted structured variants and 20 rejected envelopes.
  Targeted Clippy, formatting, 414-task validation and stable compilation of the
  real shared-oracle fuzz target passed. Compilation is not sanitizer execution.
- **Dapane:** Rust 1.99.1 formatting, all-target Clippy and all 33 locked offline
  adapter tests passed, including two new native mutation tests. The local ASan
  campaign completed 34,920 inputs in 31 seconds with `detect_leaks=0`; its initial
  default-sanitizer run failed at exit because LeakSanitizer could not use ptrace.
  That initial run is not a pass. Existing process-model CI passed the native
  tests; the sole integrator retains PR/weekly campaign wiring and artifacts.
- **Mailweft:** Rust 1.99.1 locked all-target workspace tests, both new native
  tests, formatting, scoped no-dependency Clippy and Conductor doctor passed.
  The local ASan campaign completed 23,353 inputs in 31 seconds with leak
  detection disabled only for the executor's ptrace restriction. The initial
  default-sanitizer failure is not counted as passed; hosted defaults are intact.
- **CiteLattice:** Rust 1.99.1 executed both new native tests; formatting and
  ingest all-target Clippy passed. The local ASan campaign completed 14,902 inputs
  in 31 seconds with leak detection disabled for the same ptrace restriction.
  The initial default-sanitizer failure is not counted as passed. Bounded source
  and event invariants do not qualify producer compatibility or scientific use.
- **Archive-govt-nz:** eight properties, up to 1,000 cases each, passed on exact
  Python 3.15.1 in 15.15 seconds; targeted lint/types passed. Existing election
  formatting failures remain with their current owners.
- **OSF CLI:** all seven mutation targets ran in hosted PR jobs. Local `go test
  ./...`, race tests, vet, stub checks and review checks passed. The production
  module/compiler pin is unchanged by this rollout.
- **RCAgent:** five properties, up to 1,000 cases each, passed on Python 3.15.2 in
  89.18 seconds, plus 18 focused tests. The initial broad gate reported 3,261
  passed, 53 failed and 11 skipped; a shallow-history case passed after repair,
  leaving 52 socket-restricted cases without a qualifying local pass. The
  subsequent exact-head hosted Quality run passed its platform/coverage matrix;
  offline security is still queued.
- **MCHS:** eight properties, up to 1,000 cases each, passed on Python 3.15.1 in
  12.46 seconds; full Ruff 0.17.3 passed. The killed NumPy 2.4.6 compiler means a
  full dependency install/test receipt was not obtained.
- **TOBAC:** the corrected entry point passed four rational/accounting properties,
  up to 1,000 cases each, on locked Python 3.15.2 in 5.20 seconds. Pinned Ruff 0.17.4
  and Zizmor 1.32 passed. The original Nox blob and all 43 existing native acceptance
  pin bytes were preserved; no signatures changed. A missing native interpreter
  still limits the full local Nox profile. The current-head property campaign
  passed; native verifiers and broader qualification remain queued.
- **UOGTO:** three properties, up to 500 cases each, passed on Python 3.10.22 in
  108.30 seconds. `make validate` passed; all four hosted properties/validation/required/privacy workflows passed.
  `make test` reported 340 passed, one
  existing skip and 54 warnings. These do not replace MAT04/consumer evidence.
- **Paignia:** 576 strict-dominance games, 972 transformed analytic mixed games,
  576 false-witness checks and 24 non-finite mutations passed through three native
  tests on Rust 1.75.0. Full workspace/all-targets execution passed 235 tests;
  extraction and seven actual isolated artifact profiles passed. Artifact
  qualification used local committed package candidate `016ffcbfc991f1af10f9d4435255f16d11274279`,
  before workflow-trigger and generated-test name follow-ups, and is not an exact
  published-release receipt. Hosted MSRV Clippy caught terse variable names in the
  new test; descriptive names repaired the introduced finding without a waiver.
  The corrected source repeated all three generated tests and passed exact
  1.75.0 formatting and default/all-feature workspace Clippy. Rust 1.99.1 Clippy reports an unchanged `needless_range_loop` in the
  existing solver; no solver source was reassigned or altered.
- **RaC conformance:** 379 deterministic generated input tests passed using
  Python 3.12.14, uv 0.11.8 and locked PIC dependencies. Full-gate progress included
  101 tooling tests and 484 PIC tests at 85.12% coverage, above the unchanged
  80% floor. Four existing converter lint findings stopped later targets.
- **StandardFlow:** canonical Rust 1.98.1 formatting, all-target/all-feature
  Clippy and 59 workspace tests passed, including four properties at 256 cases
  each. Foundation validation/audit and Markdown/index checks passed; the local
  Python tooling profile was 3.12.14 and does not substitute for hosted 3.14.
- **AuthenText:** four fast-check properties at 2,000 cases each with seed 20261120
  passed. Normal tests passed all 63 isolated files, all 400 aggregate tests and
  two integration checks; targeted lint/format, typecheck and Conductor checks
  passed. Generated skill distribution remains a distinct gate; its Windows
  retry failed on repeated Chocolatey HTTP 503 while downloading Vale.

- **Innovate:** native cargo check, repeated locked check, repository policy,
  rustfmt and actionlint passed. An actual native fuzz loop awaits hosted
  acceptance; the refreshed isolated lock does not qualify the application.
- **SourceRight:** rustfmt, actionlint and diff checks passed. Release compilation
  was killed twice (once in the project and once in serde-saphyr); no local loop
  executed, so sanitizer/native execution remains explicitly unverified.

- **Healthpoint-rs:** the final two native tests passed on Rust 1.99.1, as did
  metadata-only preflight, shell syntax, actionlint and diff checks. Preflight
  rejected an earlier credential-shaped synthetic fixture; it was removed, and
  the scanner rules were unchanged. An earlier instrumented draft was killed
  after 21,548 inputs; that is not a completed campaign and does not qualify the
  final harness. Normal Clippy still reaches unchanged core-trait diagnostics.
- **Fe-reader:** the two new native tests passed on Rust 1.99.1 during
  implementation. Schema, architecture, lifecycle, shell syntax, actionlint and
  diff checks passed. The initial full workspace attempt was killed compiling
  syn; a serialized retry was pending at this observation. There is no completed
  local sanitizer receipt, and an advisory workflow's overall success alone
  cannot establish that its campaign executed successfully.

## Existing approaches and legitimate holds

| Repository/group | Disposition in this rollout |
| --- | --- |
| Atlas | Existing canonical `test_goblin` property suite already met the recommendation: four tests passed with locked uv/Python 3.14.6 at `23800d445e1d1ab07dec303dcb2eed57c7a0aef7`. No code change or new hosted acceptance is claimed. |
| Dioryx | Preserve the no-binary-parser/core-owner hold. No parallel parser harness is introduced. |
| Searchright; Voiage; FYI-CLI; FYI-archive; Aegisarchive | Retain the existing approaches and ownership. This record adds no replacement infrastructure and makes no fresh qualification claim for them. |
| merman; selkie; rust4pm | Retain upstream/fork alignment. No duplicate fuzz infrastructure is introduced by this coordinator. |

## Closure and evidence retention

Consumer PRs retain commands, budgets, local limitations and their run links.
Where workflows upload failure/test evidence, use those revision-bound artifacts
within the consumer's retention window. Minimized failures require reproducer
review before regression admission. Do not turn a synthetic invariant, an old
successful head, a queued security job or a configured schedule into a release,
memory-safety or scientific-qualification claim.

Remaining coordination work is in [the plan](plan.md). No default-branch receipt,
consumer integration, branch-protection change or merge is authorized by a row
in this ledger.
