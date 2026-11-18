#!/usr/bin/env bash
# Online preparation followed by a strictly offline build and actual controls.
# This command never registers a runner or grants production qualification.
set -euo pipefail
umask 022
if [[ "$#" != 2 && "$#" != 3 ]]; then
  echo "Usage: qualify_hosted.sh CLEAN_POLICY_CHECKOUT NEW_DESTINATION [--gitleaks-candidate-evidence-only]" >&2
  exit 2
fi
candidate_args=()
candidate_enabled=false
if [[ "$#" = 3 ]]; then
  [[ "$3" = --gitleaks-candidate-evidence-only ]] || exit 2
  candidate_args+=("$3")
  candidate_enabled=true
fi
policy_root="$(cd -- "$1" && pwd)"
destination="$(python -I -c 'import pathlib,sys; print(pathlib.Path(sys.argv[1]).absolute())' "$2")"
policy_sha="$(git --no-replace-objects -C "$policy_root" rev-parse HEAD)"
[[ "$policy_sha" =~ ^[0-9a-f]{40}$ ]] || exit 2
[[ "$destination" = /* && "$destination" != "$policy_root" && "$destination" != "$policy_root/"* ]] || exit 2
[[ "$destination" != *","* && "$destination" != *$'\n'* && "$destination" != *$'\r'* ]] || exit 2
[[ ! -e "$destination" && ! -L "$destination" ]] || { echo "Choose a new preparation destination" >&2; exit 2; }
[[ -z "$(git --no-replace-objects -C "$policy_root" status --porcelain --untracked-files=all)" ]] || exit 2
python -I -c 'import sys; assert sys.version_info[:3] == (3, 15, 2)'
[[ "$(uname -s)" = Linux && "$(uname -m)" = x86_64 ]] || exit 2
mkdir -p "$destination/evidence" "$destination/context" "$destination/base-context" "$destination/registry"
evidence="$destination/evidence"
registry_name="offline-image-qualification-$RANDOM-$$"
registry_created=false
stage=preflight
finish() {
  status=$?
  trap - EXIT
  if [[ "$registry_created" = true ]]; then
    if ! docker rm --force "$registry_name" >/dev/null 2>&1; then
      status=2
      stage=registry-cleanup
    fi
  fi
  python -I - "$evidence/hosted-execution.json" "$stage" "$status" "$policy_sha" "$candidate_enabled" <<'PY'
import json, os, pathlib, sys
path, stage, status, policy, candidate = sys.argv[1:]
record = {
    "schema_version": 1,
    "kind": "offline-image-hosted-execution",
    "status": "passed" if status == "0" else "failed",
    "last_stage": stage,
    "policy_commit": policy,
    "gitleaks_candidate_evidence_only": candidate == "true",
    "preparation_network_access": True,
    "scanner_network_access": False,
    "runner_registration_qualified": False,
    "application_adapters_qualified": False,
    "image_exported": False,
    "image_redistribution_qualified": False,
    "release_qualified": False,
}
with pathlib.Path(path).open("x", encoding="utf-8") as stream:
    os.fchmod(stream.fileno(), 0o600)
    json.dump(record, stream, indent=2, sort_keys=True)
    stream.write("\n")
PY
  exit "$status"
}
trap finish EXIT

# Freeze a local Docker endpoint; remote daemons cannot use these host paths.
endpoint="${DOCKER_HOST:-$(docker context inspect --format '{{.Endpoints.docker.Host}}')}"
[[ "$endpoint" = unix:///* && "$endpoint" != *[[:space:]]* ]] || exit 2
export DOCKER_HOST="$endpoint"
unset DOCKER_CONTEXT
[[ "$(docker info --format '{{.OSType}}')" = linux ]] || exit 2
docker version --format '{{json .}}' > "$evidence/docker-version.json"

# Acquire only the reviewed Debian runtime closure before the offline build.
stage=os-package-preparation
python -I "$policy_root/security/offline-ai/provision/prepare_os_packages.py" \
  --destination "$destination/base-context/os" --receipt "$evidence/os-packages.json"

stage=git-source-preparation
git_lock="$policy_root/security/offline-ai/provision/git-source.json"
mapfile -t git_source < <(python -I - "$git_lock" <<'PY'
import json, re, sys
with open(sys.argv[1], encoding="utf-8") as stream:
    lock = json.load(stream)
version, url, size, digest = (lock[k] for k in ("version", "url", "size_bytes", "sha256"))
if (lock["schema_version"] != 1 or not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", version)
        or url != f"https://www.kernel.org/pub/software/scm/git/git-{version}.tar.xz"
        or type(size) is not int or not 0 < size <= 32 * 1024 * 1024
        or not re.fullmatch(r"[0-9a-f]{64}", digest)):
    raise SystemExit(2)
print(version, url, size, digest, sep="\n")
PY
)
[[ "${#git_source[@]}" = 4 ]] || exit 2
mkdir "$destination/base-context/git"
git_archive="$destination/base-context/git/git.tar.xz"
curl --fail --silent --show-error --location --proto '=https' --proto-redir '=https' \
  --max-time 120 --max-filesize "${git_source[2]}" "${git_source[1]}" -o "$git_archive"
[[ "$(wc -c < "$git_archive" | tr -d '[:space:]')" = "${git_source[2]}" ]]
printf '%s  %s\n' "${git_source[3]}" "$git_archive" | sha256sum --check
cp "$git_lock" "$evidence/git-source.json"

stage=upstream-preparation
# Missing committed locks fail here; candidate-lock generation is a separate job.
PYTHONDONTWRITEBYTECODE=1 python "$policy_root/security/offline-ai/provision/prepare_vendor.py" \
  --destination "$destination/context/vendor" --receipt "$evidence/preparation.json" "${candidate_args[@]}"
PYTHONPATH="$policy_root/security/offline-ai" PYTHONSAFEPATH=1 \
  python -m security.verify_vendor "$destination/context/vendor"
cp "$destination/context/vendor/manifest.json" "$evidence/asset-manifest.json"
cp "$destination/context/vendor/requirements.lock" "$evidence/requirements.lock"
cp "$policy_root/security/offline-ai/provision/base-images.json" "$evidence/base-images.json"

stage=base-preparation
mapfile -t images < <(python -I - "$policy_root/security/offline-ai/provision/base-images.json" <<'PY'
import json, re, sys
with open(sys.argv[1], encoding="utf-8") as stream:
    data = json.load(stream)
if data.get("schema_version") != 1 or data.get("architecture") != "linux/amd64":
    raise SystemExit(2)
for name, repository in (("python", "python"), ("node", "node"),
                         ("registry", "registry"), ("git_builder", "buildpack-deps")):
    ref = data[name]["reference"]
    if not re.fullmatch(r"docker\.io/library/" + repository + r"@sha256:[0-9a-f]{64}", ref):
        raise SystemExit(2)
    print(ref)
PY
)
[[ "${#images[@]}" = 4 ]] || exit 2
python_image="${images[0]}"
node_image="${images[1]}"
registry_image="${images[2]}"
for image in "${images[@]}"; do
  docker pull --platform linux/amd64 "$image"
  [[ "$(docker image inspect "$image" --format '{{.Os}}/{{.Architecture}}')" = linux/amd64 ]] || exit 2
done

# The registry is private to this job and listens only on host loopback.
chmod 0777 "$destination/registry"
docker run --detach --rm --name "$registry_name" \
  --read-only --cap-drop ALL --security-opt no-new-privileges \
  --pids-limit 128 --memory 256m --cpus 1 \
  --publish 127.0.0.1:80:5000 \
  --mount "type=bind,src=$destination/registry,dst=/var/lib/registry" \
  --env REGISTRY_STORAGE_FILESYSTEM_ROOTDIRECTORY=/var/lib/registry \
  --env REGISTRY_HTTP_ADDR=0.0.0.0:5000 "$registry_image" >/dev/null
registry_created=true
ready=false
for attempt in $(seq 1 30); do
  if curl --fail --silent --output /dev/null http://127.0.0.1/v2/; then ready=true; break; fi
  sleep 1
done
[[ "$ready" = true ]] || exit 2

stage=offline-base-build
docker build --network none --pull=false \
  --build-arg "PYTHON_IMAGE=$python_image" --build-arg "NODE_IMAGE=$node_image" \
  --build-arg "GIT_BUILD_IMAGE=${images[3]}" --build-arg "GIT_VERSION=${git_source[0]}" \
  --build-arg "GIT_ARCHIVE_SHA256=${git_source[3]}" \
  --file "$policy_root/security/offline-ai/provision/Base.Dockerfile" \
  --tag localhost/offline-ai-base:candidate "$destination/base-context"
docker push localhost/offline-ai-base:candidate
base_image="$(docker image inspect localhost/offline-ai-base:candidate --format '{{index .RepoDigests 0}}')"
[[ "$base_image" =~ ^localhost/offline-ai-base@sha256:[0-9a-f]{64}$ ]] || exit 2
[[ "$(docker image inspect "$base_image" --format '{{len .RootFS.Layers}}')" = 1 ]] || exit 2
printf '%s\n' "$base_image" > "$evidence/base-image.txt"
docker run --rm --pull=never --network none --read-only --cap-drop ALL \
  --security-opt no-new-privileges --pids-limit 32 --user 65534:65534 "$base_image" \
  sh -eu -c 'git --version; sha256sum /usr/local/bin/git; dpkg-query -W zlib1g' \
  > "$evidence/git-runtime.txt"

stage=offline-image-build
git --no-replace-objects -C "$policy_root" archive "$policy_sha" security/offline-ai \
  | tar -xf - -C "$destination/context"
docker build --network none --pull=false --no-cache \
  --build-arg "BASE_IMAGE=$base_image" \
  --file "$destination/context/security/offline-ai/docker/Dockerfile" \
  --tag localhost/offline-ai-security:candidate "$destination/context"
docker push localhost/offline-ai-security:candidate
image="$(docker image inspect localhost/offline-ai-security:candidate --format '{{index .RepoDigests 0}}')"
[[ "$image" =~ ^localhost/offline-ai-security@sha256:[0-9a-f]{64}$ ]] || exit 2
printf '%s\n' "$image" > "$evidence/scanner-image.txt"
manifest_sha="$(sha256sum "$evidence/asset-manifest.json" | cut -d ' ' -f 1)"

stage=actual-image-controls
python "$policy_root/security/offline-ai/docker/qualify_image.py" \
  --policy-sha "$policy_sha" --image "$image" --manifest-sha256 "$manifest_sha" \
  --receipt "$evidence/qualification.json"
python -I - "$evidence/qualification.json" "$policy_sha" "$image" <<'PY'
import json, sys
with open(sys.argv[1], encoding="utf-8") as stream:
    receipt = json.load(stream)
assert receipt["status"] == "passed"
assert receipt["policy_commit"] == sys.argv[2] and receipt["image"] == sys.argv[3]
assert all(item["status"] == "passed" for item in receipt["stages"])
assert receipt["runner_registration_qualified"] is False
PY

stage=registry-cleanup
# Keep the candidate image local. Binary redistribution needs a separate
# license and corresponding-source review; retain execution evidence only.
docker stop --time 10 "$registry_name" >/dev/null
registry_created=false
if [[ -n "${GITHUB_OUTPUT:-}" ]]; then
  printf 'image=%s\npolicy_sha=%s\nevidence=%s\n' "$image" "$policy_sha" "$evidence" >> "$GITHUB_OUTPUT"
fi
stage=complete
