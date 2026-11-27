# Both inputs must be the reviewed Linux amd64 digests in base-images.json.
# Downloading those images is a separate online preparation step.
ARG NODE_IMAGE
ARG PYTHON_IMAGE
FROM ${NODE_IMAGE} AS node
FROM ${PYTHON_IMAGE}
COPY --from=node /usr/local/bin/node /usr/local/bin/node
COPY --from=node /usr/local/lib/node_modules /usr/local/lib/node_modules
RUN --network=none ln -s ../lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm \
    && ln -s ../lib/node_modules/npm/bin/npx-cli.js /usr/local/bin/npx \
    && python -I -c 'import sys; assert sys.version_info[:3] == (3, 15, 1)' \
    && node -e 'if (Number(process.versions.node.split(".")[0]) !== 24) process.exit(2)' \
    && git --version
ENTRYPOINT []
CMD ["python", "--version"]
