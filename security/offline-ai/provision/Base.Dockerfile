ARG NODE_IMAGE
ARG PYTHON_IMAGE
ARG GIT_BUILD_IMAGE
FROM ${NODE_IMAGE} AS node
FROM ${GIT_BUILD_IMAGE} AS git-build
ARG GIT_VERSION
ARG GIT_ARCHIVE_SHA256
ARG GIT_CARGO_LOCK_SHA256
RUN --network=none --mount=type=bind,source=git,target=/opt/git-source,readonly \
    printf '%s  /opt/git-source/git.tar.xz\n' "$GIT_ARCHIVE_SHA256" | sha256sum --check \
    && mkdir /tmp/git-source \
    && tar --extract --xz --file=/opt/git-source/git.tar.xz \
      --directory=/tmp/git-source --strip-components=1 --no-same-owner \
    && rustc --version | grep -E '^rustc 1\.100\.0 ' \
    && cargo --version | grep -E '^cargo 1\.100\.0 ' \
    && (cd /tmp/git-source && cargo generate-lockfile --offline) \
    && printf '%s  /tmp/git-source/Cargo.lock\n' "$GIT_CARGO_LOCK_SHA256" | sha256sum --check \
    && make -C /tmp/git-source -j2 prefix=/usr/local DESTDIR=/git-runtime \
      NO_CURL=YesPlease NO_OPENSSL=YesPlease NO_EXPAT=YesPlease \
      NO_GETTEXT=YesPlease NO_PERL=YesPlease NO_TCLTK=YesPlease \
      CARGO_ARGS='--release --locked --offline' \
      CFLAGS='-O2 -fstack-protector-strong -D_FORTIFY_SOURCE=3 -fPIE -Wformat -Werror=format-security' \
      LDFLAGS='-Wl,-z,relro,-z,now -pie' INSTALL_STRIP=-s install \
    && test "$(/git-runtime/usr/local/bin/git --version)" = "git version $GIT_VERSION" \
    && install -D -m 0644 /tmp/git-source/COPYING /git-runtime/usr/local/share/doc/git/COPYING

FROM ${PYTHON_IMAGE} AS runtime-files
COPY --from=node /usr/local/bin/node /usr/local/bin/node
COPY --from=node /usr/local/LICENSE /usr/local/share/doc/node/LICENSE
COPY --from=git-build /git-runtime/usr/local/ /usr/local/
# The prepared package bytes stay in a read-only build mount; dpkg preserves
# the official package database and licenses in the resulting runtime image.
RUN --network=none --mount=type=bind,source=os,target=/opt/offline-os,readonly \
    python -I /opt/offline-os/prepare_os_packages.py --install /opt/offline-os \
      --receipt /usr/local/share/offline-ai/os-packages.json \
    && python -I -c 'import sys; assert sys.version_info[:3] == (3, 15, 2)' \
    && node -e 'if (Number(process.versions.node.split(".")[0]) !== 24) process.exit(2)' \
    && git --version \
    && test ! -e "$(git --exec-path)/git-remote-http" \
    && test ! -e "$(git --exec-path)/git-remote-https" \
    && linked="$(ldd /usr/local/bin/git)" \
    && ! printf '%s\n' "$linked" | grep -Ei 'libcurl|not found' \
    && packages="$(dpkg-query -W -f='${Package}\n')" \
    && ! printf '%s\n' "$packages" | grep -E '^(git|libcurl[^[:space:]]*)$' \
    && test ! -e /usr/local/bin/npm \
    && test ! -e /usr/local/bin/npx \
    && test ! -e /usr/local/lib/node_modules

# Copy the patched runtime files into a new layer, including the Debian
# package database. The earlier zlib bytes stay in the build stage.
FROM scratch
COPY --from=runtime-files / /
ENV LANG=C.UTF-8 \
    PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
ENTRYPOINT []
CMD ["python", "--version"]
