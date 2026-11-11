# Offline AI security profile (draft)

This is an **opt-in, pre-provisioned self-hosted** runner profile. The GitHub Actions control plane and checkout require access to GitHub; all scanning occurs in a Docker `--network none` container. This is not an air-gapped CI system. The runner administrator must pin an immutable image, install `gitleaks`, `opengrep`, `promptfoo`, `pytest`, `presidio-analyzer`, `presidio-anonymizer`, `gliner`, and a vetted GLiNER model under `/opt/models/gliner-pii`. Configure `SECURITY_IMAGE_DIGEST=sha256:<64-hex>` in the self-hosted runner environment. Do not run a container from untrusted repository files or package install scripts.

The main workflow is pinned to a **temporary branch for integration validation**. Replace with an immutable commit SHA before merging caller workflows. Provision the image before enabling required checks. The mock adversarial agent demonstrates the harness, **not actual application defense**. Add per-application local providers and explicit integration wiring before treating layer 3 or 4 as product coverage.

The legacy shared `privacy-secrets` action downloads dependencies and cannot satisfy strict offline execution; retain it independently for existing repositories until the new profile is verified. Do not weaken existing Gitleaks, Presidio, quality, or Conductor controls. The published Python DLP wrapper is opt-in by application code; simply storing it in a repository does not intercept agent calls.

This profile has no runtime network access. Model weights must be pre-provisioned and verified; no model, package, or binary downloads occur inside the scanning container. GitHub Actions still transmits workflow metadata and logs. Never log findings containing plaintext personal information.
