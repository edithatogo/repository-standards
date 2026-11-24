ARG NODE_IMAGE
ARG PYTHON_IMAGE
FROM ${NODE_IMAGE} AS node
FROM ${PYTHON_IMAGE} AS compiler
RUN --network=none --mount=type=bind,source=git-os,target=/opt/git-os,readonly \
    python -I /opt/git-os/prepare_os_packages.py --profile git-compiler \
      --install /opt/git-os --receipt /tmp/git-compiler.json

FROM compiler AS git-builder
RUN --network=none install -d -m 0755 -o 65532 -g 65532 /opt/built
USER 65532:65532
RUN --network=none --mount=type=bind,source=git-source,target=/opt/git-source,readonly \
    HOME=/tmp bash /opt/git-source/prepare_git.sh --build /opt/git-source /opt/built/git.deb

FROM compiler AS openssl-builder
RUN --network=none --mount=type=bind,source=openssl-os,target=/opt/openssl-os,readonly \
    python -I /opt/openssl-os/prepare_os_packages.py --profile openssl-compiler \
      --install /opt/openssl-os --receipt /tmp/openssl-compiler.json \
    && install -d -m 0755 -o 65532 -g 65532 /opt/built
USER 65532:65532
RUN --network=none --mount=type=bind,source=openssl-source,target=/opt/openssl-source,readonly \
    bash /opt/openssl-source/prepare_openssl.sh --build /opt/built/openssl

FROM ${PYTHON_IMAGE}
COPY --from=node /usr/local/bin/node /usr/local/bin/node
COPY --from=node /usr/local/LICENSE /usr/local/share/doc/node/LICENSE
# The prepared package bytes stay in a read-only build mount; dpkg preserves
# the official package database and licenses in the resulting runtime image.
RUN --network=none --mount=type=bind,source=os,target=/opt/offline-os,readonly \
    --mount=from=git-builder,source=/opt/built,target=/opt/built,readonly \
    --mount=from=openssl-builder,source=/opt/built/openssl,target=/opt/openssl,readonly \
    --mount=type=bind,source=openssl-source,target=/opt/openssl-source,readonly \
    python -I /opt/offline-os/prepare_os_packages.py --install /opt/offline-os \
      --receipt /usr/local/share/offline-ai/os-packages.json \
    && dpkg --install /opt/built/git.deb \
    && bash /opt/openssl-source/prepare_openssl.sh --install /opt/openssl \
    && install -D -m 0644 /opt/openssl/openssl-packages.sha256 /usr/local/share/offline-ai/openssl-packages.sha256 \
    && install -D -m 0644 /opt/openssl/openssl-tests.txt /usr/local/share/offline-ai/openssl-tests.txt \
    && install -D -m 0644 /opt/openssl/openssl-build-log.sha256 /usr/local/share/offline-ai/openssl-build-log.sha256 \
    && test -z "$(dpkg --audit)" \
    && test -r /usr/share/offline-ai/git-source.json \
    && dpkg --compare-versions "$(dpkg-query -W -f='${Version}' git)" ge '1:2.47.3-0+deb13u1' \
    && ! dpkg-query --show libcurl3t64-gnutls \
    && python -I -c 'import sys; assert sys.version_info[:3] == (3, 15, 2)' \
    && node -e 'if (Number(process.versions.node.split(".")[0]) !== 24) process.exit(2)' \
    && git --version \
    && test ! -e /usr/local/bin/npm \
    && test ! -e /usr/local/bin/npx \
    && test ! -e /usr/local/lib/node_modules
ENTRYPOINT []
CMD ["python", "--version"]
