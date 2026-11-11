# Offline scanner image contract

The `docker/Dockerfile` is a **build recipe**, not a qualified image. No dependencies, GLiNER model weights, or binary bundles are downloaded by this repo. Procurement and verification of these assets happen independently in an approved build environment.

Expected local vendor tree at the build context root:

- `vendor/python-wheels/`: audited compatible wheels, including Presidio Analyzer/Anonymizer, GLiNER, pytest, and pinned transitive dependencies.
- `vendor/requirements.lock`: pip hashes for **every** installed wheel.
- `vendor/bin/gitleaks`, `vendor/bin/opengrep`: independently qualified binaries.
- `vendor/promptfoo/`: independently qualified offline Node distribution with full dependency tree.
- `vendor/models/gliner-pii/`: model config, tokenizer and weights vetted for licensing and safety.
- `vendor/manifest.json`: externally reviewed SHA256 records for qualified files, including GLiNER config and weight file(s).

`security.verify_assets` rejects absent or tampered model assets, symlinks, duplicates, malformed manifests, and untrusted paths. A manifest **self-generated from the same untrusted input is not a provenance guarantee**. Bind the approved manifest to a signed release record before use.

Build with `BASE_IMAGE=locally-loaded-image@sha256:<digest> bash security/offline-ai/docker/build_offline.sh`. The build script fails if any input is missing. A successful build is not deployment: inspect SBOM, image digest, model behavior, vulnerability results, filesystem permissions and actual `--network none` behavior before assigning `SECURITY_IMAGE_DIGEST`.

Do not commit real clinical data, private repository content, or sensitive model weights to this standards repository. No GitHub-hosted Actions job can be described as wholly air-gapped, because checkout and orchestration require GitHub connectivity.
