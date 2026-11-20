#!/usr/bin/env bash
# Download the pinned upstream release, then build its local-history package offline.
set -euo pipefail
umask 022

version=2.56.1
revision=03b41523c576f26ad34085378717a0c1b287470f
archive_size=12804471
archive_sha256=234c011d07f7a7c8420ad3a1b692e71ec5b5a62a4626b07bc8d20a332eb3b1a8
source_url="https://codeload.github.com/git/git/tar.gz/$revision"
package_version="$version-0+offline1"

verify_source() {
  local archive=$1
  if [[ ! -f "$archive" || -L "$archive" ]] || [[ "$(wc -c < "$archive")" -ne "$archive_size" ]]; then
    echo "Git source archive size or type does not match the lock" >&2
    return 2
  fi
  printf '%s  %s\n' "$archive_sha256" "$archive" | sha256sum --check --status
}

source_receipt() {
  cat <<EOF
{
  "version": "$version",
  "package_version": "$package_version",
  "source_revision": "$revision",
  "source_url": "$source_url",
  "archive_size_bytes": $archive_size,
  "archive_sha256": "$archive_sha256"
}
EOF
}

case "${1:-}" in
  --prepare)
    [[ "$#" -eq 2 ]] || exit 2
    destination=$2
    mkdir -- "$destination"
    curl --fail --silent --show-error --location --proto '=https' --proto-redir '=https' \
      --max-time 120 --max-filesize "$archive_size" \
      --output "$destination/git.tar.gz" "$source_url"
    verify_source "$destination/git.tar.gz"
    cp -- "${BASH_SOURCE[0]}" "$destination/prepare_git.sh"
    source_receipt > "$destination/git-source.json"
    ;;
  --build)
    [[ "$#" -eq 3 ]] || exit 2
    archive="$2/git.tar.gz"
    output=$3
    verify_source "$archive"
    [[ "$(uname -s)" == Linux && "$(uname -m)" == x86_64 && "$(id -u)" == 65532 ]] || exit 2
    [[ ! -e "$output" && ! -L "$output" ]] || exit 2
    work="$(mktemp -d)"
    trap 'rm -rf -- "$work"' EXIT
    tar --extract --gzip --file "$archive" --directory "$work" \
      --no-same-owner --no-same-permissions
    source="$work/git-$revision"
    package="$work/package"
    make -C "$source" -j4 prefix=/usr NO_RUST=YesPlease NO_CURL=YesPlease \
      NO_OPENSSL=YesPlease NO_EXPAT=YesPlease NO_GETTEXT=YesPlease \
      NO_PERL=YesPlease NO_PYTHON=YesPlease NO_TCLTK=YesPlease git
    [[ "$("$source/git" --version)" == "git version $version" ]] || exit 2
    install -D -m 0755 "$source/git" "$package/usr/bin/git"
    strip --strip-debug "$package/usr/bin/git"
    install -D -m 0644 "$source/COPYING" "$package/usr/share/doc/git/copyright"
    source_receipt > "$package/usr/share/doc/git/offline-source.json"
    make -C "$source/templates" prefix=/usr DESTDIR="$package" install
    install -d -m 0755 "$package/DEBIAN"
    cat > "$package/DEBIAN/control" <<EOF
Package: git
Version: $package_version
Architecture: amd64
Maintainer: Repository Standards
Depends: libc6, zlib1g
Homepage: https://git-scm.com/
Description: Upstream Git for local scanner history
EOF
    dpkg-deb --build --root-owner-group -Zgzip "$package" "$output"
    ;;
  *)
    echo "Usage: prepare_git.sh --prepare NEW_DIRECTORY | --build SOURCE_DIRECTORY PACKAGE" >&2
    exit 2
    ;;
esac
