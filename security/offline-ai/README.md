# Offline AI security profile (draft)

This is an **opt-in, pre-provisioned self-hosted** runner profile. The GitHub Actions control plane and checkout require access to GitHub; all scanning occurs in a Docker `--network none` container. This is not an air-gapped CI system. The runner administrator must pin an immutable image, install `gitleaks`, `opengrep`, `promptfoo`, `pytest`, `presidio-analyzer`, `presidio-anonymizer`, `gliner`, and a vetted GLiNER model under `/opt/models/gliner-pii`. Configure `SECURITY_IMAGE_DIGEST=sha256:<64-hex>` in the self-hosted runner environment. Do not run a container from untrusted repository files or package install scripts.

The main workflow is pinned to a **temporary branch for integration validation**. Replace with an immutable commit SHA before merging caller workflows. Provision the image before enabling required checks. The mock adversarial agent demonstrates the harness, **not actual application defense**. Add per-application local providers and explicit integration wiring before treating layer 3 or 4 as product coverage.

The legacy shared `privacy-secrets` action downloads dependencies and cannot satisfy strict offline execution; retain it independently for existing repositories until the new profile is verified. Do not weaken existing Gitleaks, Presidio, quality, or Conductor controls. The published Python DLP wrapper is opt-in by application code; simply storing it in a repository does not intercept agent calls.

This profile has no runtime network access. Model weights must be pre-provisioned and verified; no model, package, or binary downloads occur inside the scanning container. GitHub Actions still transmits workflow metadata and logs. Never log findings containing plaintext personal information.

## Current local capabilities and integration contract

- `security/verify_network.py` checks loopback-only network interfaces before scanning. This adds a fail-closed namespace preflight; it does not replace host-level firewall/runner isolation verification.
- `security/verify_assets.py` verifies a vetted manifest and GLiNER model file hashes before scanning. The reviewed asset manifest must be supplied with the prebuilt image.
- `scripts/verify_gitleaks.py` creates ephemeral synthetic positive/negative Git histories and requires the installed Gitleaks binary to distinguish them.
- `scripts/verify_sast_fixtures.py` uses the installed Opengrep CLI, including `--taint-intrafile`, and checks Python/TypeScript/Rust positive controls, benign controls, and spoofed-sanitizer bypasses.
- `security/identifiers.py` adds checksum-based recognition for AU Medicare and both NZ NHI identifier formats. NHI implementation source: HISO 10046:2024 and Health NZ NHI Implementation Guide; Medicare implementation source: ADHA Use of Healthcare Identifiers in Health Software Systems, Appendix E. This is one identifier family, not comprehensive de-identification.
- `security/agent_boundary.py` offers explicit `guarded_invoke` and `guarded_transform` APIs with input/output sanitization and normalized exceptions. They are not automatic interception.
- `security/target_provider.py` runs an explicitly named in-repository Python adapter; the only accepted implementation is inside the approved checkout. Add `security/agent_security_adapter.py` with `respond(prompt: str, vars: dict) -> str` in each application where agent-level evaluation is required. That adapter is executed inside the isolated container; never load a provider outside it. When `enforce_ai: true`, missing adapter fails rather than falling back to the mock.
- `promptfooconfig.integration.yaml` provides real-agent synthetic injection/exfiltration probes; existing `promptfooconfig.yaml` remains a **mock-only** harness test.

The runtime does not automatically protect a consumer application merely because the shared workflow runs. Production adoption must demonstrate real egress and ingress interception, including MCP, retrieval, logging and cloud-bound tool calls.

### Qualification evidence still missing

The locally run Python unit tests do not prove actual Opengrep finding coverage, Gitleaks CLI compatibility, Promptfoo CLI/provider compatibility, actual Presidio/GLiNER model behavior, a complete pinned container image, or runner network isolation. Every corresponding gate is expected to fail closed until its prerequisites are met. Do not merge 175 draft consumer callers in advance of a qualified central release.

## Cross-language local DLP broker

The optional broker `security/dlp_socket.py` is a **Unix-domain socket**, not HTTP, and does not bind any network address. Start it only in a pre-created, user-owned private directory (0700); it creates a 0600 socket. The default path is `/run/offline-dlp/dlp.sock`, configurable with `DLP_SOCKET_PATH`. The broker rejects duplicate JSON keys, invalid constants, oversized messages and unsupported payloads with the fixed response `DLP_REJECTED`; it never logs payload values.

Clients:
- Node/TypeScript: `clients/node/dlp-client.mjs` with `dlp-client.d.mts`; use `sanitizeViaSocket(value, {socketPath})` before any agent input, tool output, logging or egress boundary. Tested using Node's built-in test runner.
- Python: `security.agent_boundary` for in-process callers. The socket broker is an alternative for cross-language processes.
- Rust: `clients/rust/` contains a draft `serde_json`-based Unix socket client. **Not compiled or qualified** in this environment. The crate requires approved vendor dependencies, Cargo.lock and `cargo test --offline --locked`.

A synthetic, real-process Python-broker/Node-client integration test is in `tests/test_node_python_bridge.py`. The broker is not automatically installed into consumer applications; each runtime must instantiate it securely, bind its own source/sink call sites, and prove correct error handling. It is not a substitute for risk-based clinical de-identification.

**Privacy assurance:** all scanner, CLI test and Promptfoo output is suppressed by `security.quiet_exec` before reaching GitHub logs. It emits only predefined pass/fail labels. A security finding remains actionable via offline local inspection; raw logs and tool responses must not be uploaded to GitHub.
