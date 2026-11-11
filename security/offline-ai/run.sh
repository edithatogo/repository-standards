#!/usr/bin/env bash
set -euo pipefail
cd /work
# The readonly workspace is owned by the checkout runner, not by the sandbox UID.
git config --global --add safe.directory /work
for executable in gitleaks opengrep python promptfoo git; do command -v "$executable" >/dev/null || exit 2; done
quiet() { PYTHONPATH=/policy/security/offline-ai python -m security.quiet_exec "$@"; }
test "${HF_HUB_OFFLINE:-}" = 1 && test "${npm_config_offline:-}" = true || exit 2
# A checked-out repository must never supply or override the scanner's trusted asset manifest.
quiet network-preflight python -m security.verify_network
quiet asset-preflight python -m security.verify_assets
# Verify the installed binary and trusted rules against ephemeral positive/negative controls.
quiet gitleaks-fixtures python /policy/security/offline-ai/scripts/verify_gitleaks.py
# History scan is independent from untrusted repository configuration.
quiet gitleaks-history gitleaks git /work --config /policy/security/offline-ai/.gitleaks.toml --redact --exit-code 1
if [[ "${EVENT_NAME:-}" == push || "${EVENT_NAME:-}" == pull_request ]]; then
  if [[ "${BASE_SHA:-}" =~ ^[0-9a-f]{40}$ ]] && git cat-file -e "${BASE_SHA}^{commit}" 2>/dev/null; then
    git diff "${BASE_SHA}" HEAD --binary --no-ext-diff 2>/dev/null | quiet gitleaks-diff gitleaks stdin --config /policy/security/offline-ai/.gitleaks.toml --redact --exit-code 1
  fi
fi
quiet sast-fixtures python /policy/security/offline-ai/scripts/verify_sast_fixtures.py
quiet opengrep opengrep scan --taint-intrafile --config /policy/security/offline-ai/.opengrep/rules.yaml --error --exclude .git .
quiet pytest python -m pytest -q -p no:cacheprovider \
  /policy/security/offline-ai/tests/test_detect_ai.py \
  /policy/security/offline-ai/tests/test_agent_boundary.py \
  /policy/security/offline-ai/tests/test_verify_assets.py \
  /policy/security/offline-ai/tests/test_target_provider.py \
  /policy/security/offline-ai/tests/test_identifiers.py \
  /policy/security/offline-ai/tests/test_verify_network.py \
  /policy/security/offline-ai/tests/test_quiet_exec.py
ai=false
if [[ "${ENFORCE_AI:-false}" == true ]]; then
  ai=true
elif bash /policy/security/offline-ai/scripts/detect_ai.sh; then
  ai=true
else
  status=$?
  if [[ "$status" -ne 1 ]]; then
    echo "AI inspection failed closed" >&2
    exit 2
  fi
fi
if [[ "$ai" == true ]]; then
  test -f /opt/models/gliner-pii/config.json || { echo "Offline GLiNER model missing"; exit 2; }
  quiet pytest python -m pytest -q -p no:cacheprovider /policy/security/offline-ai/tests/test_local_dlp.py /policy/security/offline-ai/tests/test_local_dlp_integration.py
  cd /policy/security/offline-ai
  # Mock corpus verifies runner wiring, not application prompt safety.
  quiet promptfoo-mock promptfoo eval -c promptfooconfig.yaml --no-cache --no-progress
  if [[ -f /work/security/agent_security_adapter.py ]]; then
    export SECURITY_AGENT_WORKSPACE=/work
    export SECURITY_AGENT_ADAPTER=/work/security/agent_security_adapter.py
    quiet promptfoo-agent promptfoo eval -c promptfooconfig.integration.yaml --no-cache --no-progress
  elif [[ "${ENFORCE_AI:-false}" == true ]]; then
    echo 'Real local agent adapter required for enforced AI security profile' >&2
    exit 2
  fi
fi
