#!/usr/bin/env bash
set -euo pipefail
cd /work
# The readonly workspace is owned by the checkout runner, not by the sandbox UID.
git config --global --add safe.directory /work
for executable in gitleaks opengrep python promptfoo git node; do command -v "$executable" >/dev/null || exit 2; done
quiet() { PYTHONPATH=/policy/security/offline-ai python -m security.quiet_exec "$@"; }
test "${HF_HUB_OFFLINE:-}" = 1 && test "${npm_config_offline:-}" = true || exit 2
# A checked-out repository must never supply or override the scanner's trusted asset manifest.
quiet network-preflight python -m security.verify_network
quiet asset-preflight python -m security.verify_assets
# Verify the installed binary and trusted rules against ephemeral positive/negative controls.
quiet gitleaks-fixtures python /policy/security/offline-ai/scripts/verify_gitleaks.py
# Reuse exact reviewed fingerprints and the isolated Git view with offline rules.
quiet gitleaks-history python -I /policy/security/offline-ai/scripts/scan_gitleaks.py
quiet sast-fixtures python /policy/security/offline-ai/scripts/verify_sast_fixtures.py
quiet opengrep opengrep scan --strict --disable-nosem --taint-intrafile --config /policy/security/offline-ai/.opengrep/rules.yaml --error --exclude .git .
quiet pytest python -m pytest -q -p no:cacheprovider \
  /policy/security/offline-ai/tests/test_detect_ai.py \
  /policy/security/offline-ai/tests/test_agent_boundary.py \
  /policy/security/offline-ai/tests/test_verify_assets.py \
  /policy/security/offline-ai/tests/test_target_provider.py \
  /policy/security/offline-ai/tests/test_identifiers.py \
  /policy/security/offline-ai/tests/test_identifier_properties.py \
  /policy/security/offline-ai/tests/test_verify_network.py \
  /policy/security/offline-ai/tests/test_quiet_exec.py \
  /policy/security/offline-ai/tests/test_dlp_socket.py \
  /policy/security/offline-ai/tests/test_node_python_bridge.py
quiet node-tests node --test /policy/security/offline-ai/clients/node/dlp-client.test.mjs
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
