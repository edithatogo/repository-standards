#!/usr/bin/env bash
# Acquire pinned Debian source online and build its packages in an offline stage.
set -euo pipefail
umask 022

source_revision=3.5.9-1~deb13u1
package_version="$source_revision+offline1"
source_url=https://deb.debian.org/debian/pool/main/o/openssl
recipe=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
sources=openssl-debian-sources.lock
packages=(libssl3t64 openssl-provider-legacy openssl)

verify_source() {
  local directory=$1
  local size=$2
  local digest=$3
  local name=$4
  local path="$directory/$name"
  [[ -f "$path" && ! -L "$path" && "$(wc -c < "$path")" -eq "$size" ]]
  printf '%s  %s\n' "$digest" "$path" | sha256sum --check
}

case "${1:-}" in
  --prepare)
    [[ "$#" -eq 2 ]] || exit 2
    destination=$2
    mkdir -- "$destination"
    while read -r digest size name; do
      curl --fail --silent --show-error --location --proto '=https' --proto-redir '=https' \
        --max-time 180 --max-filesize "$size" \
        --output "$destination/$name" "$source_url/$name"
      verify_source "$destination" "$size" "$digest" "$name"
    done < "$recipe/$sources"
    cp "$recipe"/{prepare_openssl.sh,"$sources",openssl35-dane-guard.patch} "$destination/"
    cp -R "$recipe/openssl-debian-patches" "$destination/"
    ;;
  --build)
    [[ "$#" -eq 2 ]] || exit 2
    output=$2
    [[ "$(uname -sm)" == "Linux x86_64" && "$(id -u)" == 65532 ]] || exit 2
    interfaces=$(awk -F: 'NR > 2 {gsub(/[[:space:]]/, "", $1); print $1}' /proc/net/dev)
    [[ "$interfaces" == lo ]] || exit 2
    while read -r digest size name; do
      verify_source "$recipe" "$size" "$digest" "$name"
    done < "$recipe/$sources"
    mkdir -- "$output"
    work=$(mktemp -d)
    trap 'rm -rf -- "$work"' EXIT
    cd -- "$work"
    dpkg-source -x "$recipe/openssl_$source_revision.dsc" source
    cd source
    while read -r digest filename; do
      patch="$recipe/openssl-debian-patches/$filename"
      printf '%s  %s\n' "$digest" "$patch" | sha256sum --check
      cp -- "$patch" "debian/patches/$filename"
      printf '%s\n' "$filename" >> debian/patches/series
    done < "$recipe/openssl-debian-patches/series.lock"
    cp "$recipe/openssl35-dane-guard.patch" debian/patches/offline-dane-guard.patch
    printf '%s\n' offline-dane-guard.patch >> debian/patches/series
    dpkg-source --before-build .
    printf '%s\n' '57e348cde1c6401bbf8209c432ca0420427ad9c4fbc92b6f39d4f471272ce796  crypto/x509/x509_vfy.c' | sha256sum --check
    cat > debian/changelog.offline <<CHANGELOG
openssl ($package_version) trixie; urgency=medium

  * Backport the source-pinned OpenSSL fixes for the offline scanner build.

 -- Repository Standards <noreply@users.noreply.github.com>  Sun, 22 Nov 2026 10:00:00 +0000

CHANGELOG
    cat debian/changelog >> debian/changelog.offline
    mv debian/changelog.offline debian/changelog
    if ! env -i PATH="$PATH" HOME="$work" LC_ALL=C.UTF-8 DEB_BUILD_OPTIONS=parallel=4 \
      dpkg-buildpackage --build=binary --unsigned-source --unsigned-changes > "$work/build.log" 2>&1; then
      tail -100 "$work/build.log"
      exit 2
    fi
    grep -Fx 'Result: PASS' "$work/build.log"
    grep -E '^Files=[1-9][0-9]*, Tests=[1-9][0-9]*,' "$work/build.log" > "$output/openssl-tests.txt"
    sha256sum "$work/build.log" | cut -d ' ' -f 1 > "$output/openssl-build-log.sha256"
    cd -- "$work"
    for name in "${packages[@]}"; do
      deb="${name}_${package_version}_amd64.deb"
      [[ "$(dpkg-deb --field "$deb" Package)" == "$name" ]]
      [[ "$(dpkg-deb --field "$deb" Version)" == "$package_version" ]]
      [[ "$(dpkg-deb --field "$deb" Architecture)" == amd64 ]]
      cp -- "$deb" "$output/$deb"
      sha256sum "$deb"
    done > "$output/openssl-packages.sha256"
    ;;
  --install)
    [[ "$#" -eq 2 ]] || exit 2
    cd -- "$2"
    sha256sum --check openssl-packages.sha256
    debs=()
    for name in "${packages[@]}"; do
      debs+=("${name}_${package_version}_amd64.deb")
    done
    dpkg --install "${debs[@]}"
    [[ -z "$(dpkg --audit)" ]]
    for name in "${packages[@]}"; do
      [[ "$(dpkg-query --showformat='${Version}' --show "$name")" == "$package_version" ]]
    done
    openssl list -providers -provider default -provider legacy
    python -I -c 'import ssl; assert ssl.OPENSSL_VERSION_INFO[:3] == (3, 5, 9); assert ssl.create_default_context().get_ca_certs()'
    ;;
  *)
    echo "Usage: prepare_openssl.sh --prepare NEW_SOURCE_DIR | --build NEW_OUTPUT_DIR | --install PACKAGE_DIR" >&2
    exit 2
    ;;
esac
