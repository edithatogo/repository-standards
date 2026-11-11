#!/usr/bin/env bash
set -euo pipefail
cd /work
# The readonly workspace is owned by the checkout runner, not by the sandbox UID.
git config --global --add safe.directory /work
for executable in gitleaks opengrep python promptfoo git; do command -v "$executable" >/dev/null || exit 2; done
test "${HF_HUB_OFFLINE:-}" = 1 && test "${npm_config_offline:-}" = true || exit 2
# A checked-out repository must never supply or override the scanner's trusted asset manifest.
PYTHONPATH=/policy/security/offline-ai python -m security.verify_network
PYTHONPATH=/policy/security/offline-ai python -m security.verify_assets
# History scan is independent from untrusted repository configuration.
gitleaks git /work --config /policy/security/offline-ai/.gitleaks.toml --redact --exit-code 1
if [[ "${EVENT_NAME:-}" == push || "${EVENT_NAME:-}" == pull_request ]]; then
  if [[ "${BASE_SHA:-}" =~ ^[0-9a-f]{40}$ ]] && git cat-file -e "${BASE_SHA}^{commit}" 2>/dev/null; then
    git diff "${BASE_SHA}" HEAD --binary --no-ext-diff | gitleaks stdin --config /policy/security/offline-ai/.gitleaks.toml --redact --exit-code 1
  fi
fi
PYTHONPATH=/policy/security/offline-ai python /policy/security/offline-ai/scripts/verify_sast_fixtures.py
opengrep scan --config /policy/security/offline-ai/.opengrep/rules.yaml --error --exclude .git .
PYTHONPATH=/policy/security/offline-ai python -m pytest -q -p no:cacheprovider \
  /policy/security/offline-ai/tests/test_detect_ai.py \
  /policy/security/offline-ai/tests/test_agent_boundary.py \
  /policy/security/offline-ai/tests/test_verify_assets.py \
  /policy/security/offline-ai/tests/test_target_provider.py \
  /policy/security/offline-ai/tests/test_identifiers.py \
  /policy/security/offline-ai/tests/test_verify_network.py
ai=false
if [[ "${ENFORCE_AI:-false}" == true ]] || bash /policy/security/offline-ai/scripts/detect_ai.sh; then
  ai=true
fi
if [[ "$ai" == true ]]; then
  test -f /opt/models/gliner-pii/config.json || { echo "Offline GLiNER model missing"; exit 2; }
  PYTHONPATH=/policy/security/offline-ai python -m pytest -q -p no:cacheprovider /policy/security/offline-ai/tests/test_local_dlp.py /policy/security/offline-ai/tests/test_local_dlp_integration.py
  cd /policy/security/offline-ai
  # Mock corpus verifies runner wiring, not application prompt safety.
  PYTHONPATH=. promptfoo eval -c promptfooconfig.yaml --no-cache --no-progress
  if [[ -f /work/security/agent_security_adapter.py ]]; then
    export SECURITY_AGENT_WORKSPACE=/work
    export SECURITY_AGENT_ADAPTER=/work/security/agent_security_adapter.py
    PYTHONPATH=. promptfoo eval -c promptfooconfig.integration.yaml --no-cache --no-progress
  elif [[ "${ENFORCE_AI:-false}" == true ]]; then
    echo 'Real local agent adapter required for enforced AI security profile' >&2
    exit 2
  fi
fi
