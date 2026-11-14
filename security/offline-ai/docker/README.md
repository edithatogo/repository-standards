# Offline scanner image contract

The `docker/Dockerfile` is a **build recipe**, not a qualified image. No dependencies, GLiNER model weights, or binary bundles are downloaded by this repo. Procurement and verification of these assets happen independently in an approved build environment.

Supply a digest-pinned base with Python 3.15.1, Node and Git. The build checks
the actual interpreter before installing the locked wheels.

Expected local vendor tree at the build context root:

- `vendor/python-wheels/`: audited compatible wheels, including Presidio Analyzer/Anonymizer, GLiNER, pytest, and pinned transitive dependencies.
- `vendor/requirements.lock`: pip hashes for **every** installed wheel.
- `vendor/bin/gitleaks`, `vendor/bin/opengrep`: independently qualified binaries.
- `vendor/promptfoo/`: independently qualified offline Node distribution with full dependency tree.
- `vendor/models/gliner-pii/`: model config, tokenizer and weights vetted for licensing and safety.
- `vendor/manifest.json`: an externally approved **schema-v2** SHA256 inventory
  covering every supplied file and permitted Promptfoo link described below.

## Complete supplied-asset inventory

Schema 2 has exactly three fields: `schema_version` (integer `2`), `files`
(`{"path": "/absolute/image/path", "sha256": "<approved 64-character digest>"}`
records), and `symlinks` (`{"path": "/absolute/image/path", "target":
"../relative/target"}` records). The digest placeholder is explanatory and is
not accepted by the verifier. The manifest does not contain its own hash.

The same inventory is checked against the vendor directory before Docker is
called, and against installed image paths before pip installs any wheels.

| Vendor input | Image path and required coverage |
| --- | --- |
| `bin/gitleaks`, `bin/opengrep` | Both regular executable files under `/usr/local/bin` |
| `requirements.lock` | `/opt/offline-ai/requirements.lock` |
| `python-wheels/` | Every file in the nonempty, flat `/opt/offline-ai/wheels` wheelhouse |
| `promptfoo/` | Every file and declared link under `/opt/promptfoo`, including package metadata, lock and CLI target |
| `models/gliner-pii/` | Every model file under `/opt/models/gliner-pii`, including config and weights |

Schema 1 is intentionally rejected: it could verify a model while leaving
scanner binaries and dependency inputs unchecked. Duplicate JSON keys, unknown
fields, path aliases, hardlinks, missing/unlisted files and changed bytes fail
closed. Parent-directory symlinks are rejected. Only inventoried Promptfoo links
with exact relative targets resolving to verified files within the Promptfoo
tree are permitted. Files and directories must be accessible to the non-root
scanner, and scanner entrypoints must be executable.

A manifest **self-generated from the same untrusted input is not a provenance
guarantee**. Bind the independently approved inventory to a signed release
record. This contract verifies supplied files; the base image, installed package
behavior, licensing, vulnerabilities and SBOM require their own qualification.

To check a supplied bundle without running Docker or installing packages:

```sh
PYTHONPATH=security/offline-ai python -m security.verify_vendor /path/to/vendor
```

Build with `BASE_IMAGE=locally-loaded-image@sha256:<digest> bash security/offline-ai/docker/build_offline.sh`. The build script fails if any input is missing. A successful build is not deployment: inspect SBOM, image digest, model behavior, vulnerability results, filesystem permissions and actual `--network none` behavior before assigning `SECURITY_IMAGE_DIGEST`.

## Execute image qualification

After approving the supplied assets, building the image and recording its
immutable local registry digest, use a clean checkout of the reviewed policy
commit. The host helper uses Python's standard library and an existing local
Docker daemon. It neither downloads assets nor registers a runner.

```sh
python security/offline-ai/docker/qualify_image.py \
  --policy-sha <reviewed-40-character-policy-commit> \
  --image localhost/offline-ai-security@sha256:<approved-image-digest> \
  --manifest-sha256 <approved-sha256-of-the-manifest-file> \
  --receipt /path/outside-the-checkout/new-qualification.json
```

Replace all placeholders with independently verified values. The receipt must
not already exist. The helper rejects a dirty checkout, a mismatched policy
commit, a mutable image tag and a remote Docker daemon. It exports the exact
commit once using `git --no-replace-objects archive`, rejects archive links and
mounts the resulting snapshot read-only. Ignored files and later checkout edits
cannot alter the policy being tested.

Every control runs with an explicit entrypoint in a fresh non-root container,
`--pull=never`, `--network=none`, a read-only root, no capabilities, bounded
resources, canonical manifest/model paths and local temporary caches. The
controls are:

1. Required runtime version and executable availability.
2. Network namespace preflight.
3. Binding the image's manifest bytes to the approved manifest digest.
4. Complete asset-inventory verification.
5. Actual Gitleaks positive and negative controls.
6. Actual Opengrep language and sanitizer-spoofing controls.
7. Actual model-backed DLP tests: all three specified tests must complete setup,
   call and teardown successfully, without skips or deselection.
8. Actual Promptfoo mock-provider regression.

Model qualification always runs; it is not conditional on detecting AI files in
a consumer repository. Automatic third-party pytest plugins and extra pytest
options cannot convert skipped model tests into passing evidence.

The helper writes an atomic private receipt with image, policy and manifest
identifiers and each control's outcome. A successful receipt has `status:
passed`. An execution failure has `status: failed`, with `passed`, `failed` and
`not-run` controls and a container-cleanup result. Preflight rejection produces
no qualification receipt. Failed or interrupted containers are explicitly
removed; a cleanup failure is reported separately. Raw scanner output, model
responses and exception text are suppressed.

The receipt records the requested manifest digest; it is bound to image bytes
only when the `manifest-binding` control passed. A receipt is evidence of the
listed image/toolchain checks, not an attestation of universal detector recall.
`application_adapters_qualified` and `runner_registration_qualified` remain
false even after success. The Promptfoo mock is not actual application defense.

## Remaining runner activation

Before enabling a consumer, an approved Linux x64 host must have the qualified
image available as `localhost/offline-ai-security@sha256:...`, the matching
`SECURITY_IMAGE_DIGEST` configured, and an eligible ephemeral runner labelled
`ai-security-offline`. Verify host isolation and runner eligibility separately.
Then qualify the central release, update the consumer's immutable pin and run
the consumer checks on its final commit. Neither this recipe nor a passing
orchestration test constitutes runner provisioning or permission to merge an
unqualified consumer.

The stdlib host tests use an explicitly fake Docker executable to test control
flow, immutable references, failure receipts, cleanup and output suppression.
They do not build or qualify an image. The model-wrapper unit tests simulate
pytest's reporting contract and likewise do not replace the real model suite.

Do not commit real clinical data, private repository content, or sensitive model weights to this standards repository. No GitHub-hosted Actions job can be described as wholly air-gapped, because checkout and orchestration require GitHub connectivity.
