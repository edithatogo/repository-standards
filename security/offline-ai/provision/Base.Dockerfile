ARG NODE_IMAGE
ARG WOLFI_IMAGE
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

FROM ${WOLFI_IMAGE} AS runtime-files
COPY --from=node /usr/local/bin/node /usr/local/bin/node
COPY --from=node /usr/local/LICENSE /usr/local/share/doc/node/LICENSE
COPY --from=git-build /git-runtime/usr/local/ /usr/local/
# apk authenticates the original vendor index and validates each package
# against it. The vendor bytes, including metadata, stay mounted read-only.
# Constrain the whole reviewed inventory so the signed index cannot select
# a newer transitive package that is absent from the locked bundle.
RUN --network=none --mount=type=bind,source=os,target=/opt/offline-os,readonly \
    set -eu; \
    set --; \
    while IFS= read -r package; do \
      constraint="$(printf '%s\n' "$package" | sed -nE \
        's/^([a-zA-Z0-9][a-zA-Z0-9._+-]*)-([0-9][a-zA-Z0-9._+]*-r[0-9]+)$/\1=\2/p')"; \
      test -n "$constraint"; \
      set -- "$@" "$constraint"; \
    done < /opt/offline-os/inventory.txt; \
    test "$#" -gt 0; \
    apk --no-network --no-cache --repositories-file /dev/null --repository /opt/offline-os add "$@" \
    && apk --repositories-file /dev/null info -v | LC_ALL=C sort > /tmp/wolfi-inventory \
    && cmp /tmp/wolfi-inventory /opt/offline-os/inventory.txt \
    && rm /tmp/wolfi-inventory \
    && python3.15 -I -B /opt/offline-os/cpython/cpython_backports.py \
      /opt/offline-os/cpython/cpython-backports.json --patches /opt/offline-os/cpython \
    && python3.15 -I -m venv /opt/offline-venv \
    && /opt/offline-venv/bin/python -I -c 'import ssl, sys, zlib; assert sys.version_info[:3] == (3, 15, 2)' \
    && /opt/offline-venv/bin/python -I -m pip --version \
    && node -e 'if (Number(process.versions.node.split(".")[0]) !== 24) process.exit(2)' \
    && git --version \
    && test ! -e "$(git --exec-path)/git-remote-http" \
    && test ! -e "$(git --exec-path)/git-remote-https" \
    && linked="$(/lib64/ld-linux-x86-64.so.2 --list /usr/local/bin/git)" \
    && ! printf '%s\n' "$linked" | grep -Ei 'libcurl|not found' \
    && packages="$(apk --repositories-file /dev/null info)" \
    && ! printf '%s\n' "$packages" | grep -E '^(git|libcurl[^[:space:]]*)$' \
    && test ! -e /usr/local/bin/npm \
    && test ! -e /usr/local/bin/npx \
    && test ! -e /usr/local/lib/node_modules

RUN --network=none set -eu; \
    for tool in mount umount; do \
      path="$(command -v "$tool" || true)"; \
      if [ -n "$path" ]; then test -L "$path" && rm -- "$path" || exit 2; fi; \
    done; \
    ! command -v mount && ! command -v umount

# Preserve the installed apk package inventory and all package notices.
FROM scratch
COPY --from=runtime-files / /
ENV LANG=C.UTF-8 \
    PATH=/opt/offline-venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
ENTRYPOINT []
CMD ["python", "--version"]
