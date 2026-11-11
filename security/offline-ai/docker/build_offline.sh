#!/usr/bin/env bash
# Requires a preloaded, vetted, digest-pinned base image and local vendor assets.
set -euo pipefail
repo_root="$(git rev-parse --show-toplevel)"
cd "$repo_root"
: "${BASE_IMAGE:?Set BASE_IMAGE to a locally available image@sha256:digest}"
[[ "$BASE_IMAGE" =~ @sha256:[0-9a-f]{64}$ ]] || { echo "BASE_IMAGE must be immutable" >&2; exit 2; }
docker image inspect "$BASE_IMAGE" >/dev/null
for path in vendor/python-wheels vendor/requirements.lock vendor/bin/gitleaks vendor/bin/opengrep vendor/promptfoo/node_modules/.bin/promptfoo vendor/models/gliner-pii/config.json vendor/manifest.json; do
  [[ -e "$path" ]] || { echo "Missing required offline asset: $path" >&2; exit 2; }
done
docker build --network=none --pull=false --no-cache \
  --build-arg "BASE_IMAGE=$BASE_IMAGE" \
  -f security/offline-ai/docker/Dockerfile \
  -t localhost/offline-ai-security:candidate .
docker image inspect localhost/offline-ai-security:candidate --format '{{index .RepoDigests 0}}' || {
  echo "Candidate built; publish/import to local registry and record immutable digest before qualification." >&2
  exit 2
}
