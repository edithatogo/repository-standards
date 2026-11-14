#!/usr/bin/env bash
# Requires gh, git, jq. Safe default: dry run.
set -euo pipefail
OWNER="${OWNER:-edithatogo}"
BRANCH="${BRANCH:-security/offline-ai-security-rollout-20261111}"
CENTRAL_SHA="${CENTRAL_SHA:-36362fa872e4ce747266a6e795fcefa3dd343f67}"
DRY_RUN="${DRY_RUN:-1}"
INCLUDE_FORKS="${INCLUDE_FORKS:-0}"
RUN_ROOT="${RUN_ROOT:-.offline-ai-security-rollout}"
mkdir -p "$RUN_ROOT"
for cmd in gh git jq; do command -v "$cmd" >/dev/null || exit 2; done
gh auth status >/dev/null
mapfile -t repos < <(gh repo list "$OWNER" --limit 10000 --json nameWithOwner,isArchived,isFork,isEmpty,defaultBranchRef \
  --jq '.[] | select(.isArchived == false and .isEmpty == false) | [.nameWithOwner,.isFork,.defaultBranchRef.name] | @tsv')
for row in "${repos[@]}"; do
  IFS=$'\t' read -r name fork default <<< "$row"
  [[ "$name" == "$OWNER/repository-standards" ]] && continue
  if [[ "$fork" == true && "$INCLUDE_FORKS" != 1 ]]; then echo "SKIP fork $name"; continue; fi
  echo "PLAN $name @ $default"
  [[ "$DRY_RUN" == 1 ]] && continue
  target="$RUN_ROOT/${name#*/}"
  if [[ ! -e "$target/.git" ]]; then gh repo clone "$name" "$target"; fi
  (
    cd "$target"
    [[ -z "$(git status --porcelain)" ]] || { echo "SKIP dirty $name"; exit 2; }
    git fetch origin "$default"
    git checkout "$default"
    git pull --ff-only origin "$default"
    if git show-ref --verify --quiet "refs/heads/$BRANCH"; then
      git checkout "$BRANCH"
    else
      git checkout -b "$BRANCH" "origin/$default"
    fi
    mkdir -p .github/workflows
    cat >.github/workflows/offline-ai-security.yml <<YAML
name: Offline AI security
on:
  push:
  pull_request:
  workflow_dispatch:
permissions:
  contents: read
jobs:
  offline-ai-security:
    uses: $OWNER/repository-standards/.github/workflows/reusable-ai-sec-pipeline.yml@$CENTRAL_SHA
    permissions:
      contents: read
    with:
      enforce_ai: false
YAML
    git add .github/workflows/offline-ai-security.yml
    if ! git diff --cached --quiet; then
      git commit -m "security: adopt offline four-layer CI profile"
      git push -u origin "$BRANCH"
    fi
    count=$(gh pr list --repo "$name" --head "$BRANCH" --state open --json number --jq length)
    if [[ "$count" == 0 ]]; then
      gh pr create --repo "$name" --base "$default" --head "$BRANCH" --draft \
        --title "security: adopt offline four-layer CI profile" \
        --body "Pinned local scanning profile. DRAFT: qualification and self-hosted runner required. Central implementation: https://github.com/$OWNER/repository-standards/pull/126"
    fi
  ) || echo "EXCEPTION $name" >&2
done
