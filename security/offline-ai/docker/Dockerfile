# Offline-only build. Supply a preloaded, digest-pinned image with Python 3.15.1, Node and Git.
# Never substitute a remote tag, or run this with build network access.
ARG BASE_IMAGE
FROM ${BASE_IMAGE}
ENV PIP_NO_INDEX=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
    HF_HUB_DISABLE_TELEMETRY=1 npm_config_offline=true \
    PROMPTFOO_DISABLE_TELEMETRY=1 PROMPTFOO_DISABLE_UPDATE=1 \
    PYTHONSAFEPATH=1 \
    SECURITY_ASSET_MANIFEST=/opt/offline-ai/manifest.json \
    GLINER_MODEL_DIR=/opt/models/gliner-pii
RUN --network=none python -c 'import sys; assert sys.version_info[:3] == (3, 15, 1), sys.version'
COPY vendor/python-wheels/ /opt/offline-ai/wheels/
COPY vendor/requirements.lock /opt/offline-ai/requirements.lock
COPY vendor/bin/gitleaks /usr/local/bin/gitleaks
COPY vendor/bin/opengrep /usr/local/bin/opengrep
# vendor/promptfoo contains a complete, audited offline npm installation.
COPY vendor/promptfoo /opt/promptfoo
COPY vendor/models/gliner-pii /opt/models/gliner-pii
COPY vendor/manifest.json /opt/offline-ai/manifest.json
COPY security/offline-ai/security /opt/offline-ai/security
ENV PYTHONPATH=/opt/offline-ai
# Direct builds also verify the complete supplied inventory before pip runs.
RUN --network=none python -m security.verify_assets
RUN --network=none python -m pip install --disable-pip-version-check --no-index \
    --find-links=/opt/offline-ai/wheels --require-hashes \
    -r /opt/offline-ai/requirements.lock
RUN --network=none ln -s /opt/promptfoo/node_modules/.bin/promptfoo /usr/local/bin/promptfoo
# Caller overrides command. Scanner is launched by the trusted, pinned workflow.
# Clear the base image entrypoint so it cannot replace a qualification command.
ENTRYPOINT []
CMD ["python", "-m", "security.verify_assets"]
