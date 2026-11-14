# Offline scanner input preparation

This directory separates online acquisition of pinned public assets from offline image construction and real qualification. Preparation never registers a runner or declares an image qualified.

## Dependency review gate

`sources.json` starts with `lock_status: candidate_required`. `prepare_vendor.py` fails before downloads in that state. The separate candidate workflow uses Python 3.15.1, Node 24.22.1 and uv 0.13.8 to resolve public metadata from fixed Python version inputs and the exact Promptfoo 0.125.1 package. The existing privacy lock remains authoritative for shared Python versions. Torch and PyYAML are deliberately excluded from candidate resolution: the CPU Torch wheel has a separately verified upstream digest, and PyYAML is built using the existing source-pinned privacy builder.

The candidate consists of `requirements.extra.lock`, `promptfoo/package.json`, `promptfoo/package-lock.json` and a receipt. It is explicitly unreviewed and cannot qualify an image. Review all exact versions, registry origins, hashes and the retained privacy constraints. Commit the two new lockfiles to this directory, update their SHA256 entries in `sources.json.policy_inputs`, and set `lock_status` to `reviewed` in that separate reviewed commit. Automated source review is supported; no second-maintainer approval is introduced.

The workflow uploads the candidate as an ordinary artifact. It also emits only the three fixed public lock paths in ordered `OFFLINE_LOCK_CHUNK` JSON records, followed by `OFFLINE_LOCK_RECEIPT`. Reconstruct each path by index, require exactly the reported number of chunks, and verify both SHA256 and Git blob SHA before creating a Git object. These public metadata records permit recovery if the development workspace is unavailable. Do not promote a partial or hash-mismatched candidate.

## Prepare the vendor tree

After committing reviewed locks, run on Linux x64 with Python 3.15.1, Node >=22.22.0, npm and uv 0.13.8 installed:

```sh
python security/offline-ai/provision/prepare_vendor.py \
  --destination /new/path/vendor \
  --receipt /existing/evidence/preparation.json
```

Both output paths must be new. Keep the vendor tree outside the clean policy checkout. The script verifies the committed source catalog and policy input hashes, downloads checksum-bound Gitleaks/Opengrep/CPU Torch assets, builds the three existing source-pinned privacy wheels, downloads the exact hash-locked remaining wheel closure, and verifies that closure in an isolated environment. It installs Promptfoo with `npm ci --ignore-scripts` against the reviewed lock. Model preparation is delegated to the adjacent `prepare_model.py`, which has its own pinned model sources and receipt.

Only after those stages pass does preparation generate and verify the complete schema-v2 vendor manifest. A private receipt binds source records, policy inputs, model provenance and the resulting manifest. A failed run records the failed stage and unexecuted stages and does not mark the image or runner qualified. Raw third-party process output is suppressed during preparation; the candidate resolver uses only public dependency metadata.

The Gitleaks and Opengrep digests were independently checked against their upstream GitHub release APIs. The CPU Torch digest and metadata digest were checked against the official PyTorch CPU index; this avoids CUDA packages. Promptfoo's package integrity was checked against the npm registry and its release tag resolves to source commit `8569e72ed6cf7737082a6042be8d925e40f9739d`. Exact provenance URLs are retained in `sources.json`. Source-built and exported artifacts are bound by their recorded outputs; byte-identical rebuilds have not been demonstrated.

Continue with the existing offline Docker build and `docker/qualify_image.py`. Successful acquisition or installation does not establish scanner behavior, detector recall, model qualification, measured host isolation or runner eligibility.
