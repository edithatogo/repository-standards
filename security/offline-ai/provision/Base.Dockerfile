ARG NODE_IMAGE
ARG PYTHON_IMAGE
FROM ${NODE_IMAGE} AS node
FROM ${PYTHON_IMAGE}
COPY --from=node /usr/local/bin/node /usr/local/bin/node
COPY --from=node /usr/local/LICENSE /usr/local/share/doc/node/LICENSE
# The prepared package bytes stay in a read-only build mount; dpkg preserves
# the official package database and licenses in the resulting runtime image.
RUN --network=none --mount=type=bind,source=os,target=/opt/offline-os,readonly \
    python -I /opt/offline-os/prepare_os_packages.py --install /opt/offline-os \
      --receipt /usr/local/share/offline-ai/os-packages.json \
    && python -I -c 'import sys; assert sys.version_info[:3] == (3, 15, 2)' \
    && node -e 'if (Number(process.versions.node.split(".")[0]) !== 24) process.exit(2)' \
    && git --version \
    && test ! -e /usr/local/bin/npm \
    && test ! -e /usr/local/bin/npx \
    && test ! -e /usr/local/lib/node_modules
ENTRYPOINT []
CMD ["python", "--version"]
