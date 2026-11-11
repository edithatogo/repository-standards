#!/usr/bin/env bash
set -euo pipefail
cd /work
for executable in gitleaks opengrep python promptfoo git; do command -v "$executable" >/dev/null || exit 2; done
test "${HF_HUB_OFFLINE:-}" = 1 && test "${npm_config_offline:-}" = true || exit 2
# History scan is independent from untrusted repository configuration.
gitleaks git /work --config /policy/security/offline-ai/.gitleaks.toml --redact --exit-code 1
if [[ "${EVENT_NAME:-}" == push || "${EVENT_NAME:-}" == pull_request ]]; then
  if [[ "${BASE_SHA:-}" =~ ^[0-9a-f]{40}$ ]] && git cat-file -e "${BASE_SHA}^{commit}" 2>/dev/null; then
    git diff "${BASE_SHA}" HEAD --binary --no-ext-diff | gitleaks stdin --config /policy/security/offline-ai/.gitleaks.toml --redact --exit-code 1
  fi
fi
opengrep scan --config /policy/security/offline-ai/.opengrep/rules.yaml --error --exclude .git .
ai=false
if [[ "${ENFORCE_AI:-false}" == true ]] || grep -Eiq '(langchain|llama.index|openai|anthropic|mcp|promptfoo|agent|rag)' <(git ls-files); then
  ai=true
fi
if [[ "$ai" == true ]]; then
  test -f /opt/models/gliner-pii/config.json || { echo "Offline GLiNER model missing"; exit 2; }
  PYTHONPATH=/policy/security/offline-ai python -m pytest -q /policy/security/offline-ai/tests/test_local_dlp.py
  cd /policy/security/offline-ai
  PYTHONPATH=. promptfoo eval -c promptfooconfig.yaml --no-cache --no-progress
fi
