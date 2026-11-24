#!/usr/bin/env bash
# Build and test the candidate from the pinned source archive in offline scratch.
set -euo pipefail
umask 022

if [[ "$#" -ne 2 ]]; then
    echo "Usage: test_openssl35_backport.sh SOURCE_TAR NEW_BUILD_DIRECTORY" >&2
    exit 2
fi
if [[ "$(uname -sm)" != "Linux x86_64" || "$(id -u)" == 0 ]]; then
    echo "Run the backport build as a non-root user on Linux x64" >&2
    exit 2
fi
# /proc/net describes this process's network namespace even when /sys is shared.
interfaces=$(awk -F: 'NR > 2 {gsub(/[[:space:]]/, "", $1); print $1}' /proc/net/dev)
if [[ "$interfaces" != lo ]]; then
    echo "The OpenSSL build must have a loopback-only network namespace" >&2
    exit 2
fi
echo "Verified unprivileged Linux x64 build with loopback-only networking"

archive=$1
destination=$2
recipe=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
[[ -f "$archive" && ! -L "$archive" ]]
printf '%s  %s\n' a578782cdf05135b5fbee788be505de6b1d9066c1a46fc5b6096b5acd44ad3ed "$archive" |
    sha256sum --check
mkdir -- "$destination"
tar --extract --file "$archive" --directory "$destination" --no-same-owner --no-same-permissions
cd -- "$destination"
stage=$PWD/staged
cd openssl
printf '%s\n' 'b0d127f71a439bf83935fdbcdda3fdd5e38fa8cf66edfe493aa359d8820c087e  crypto/x509/x509_vfy.c' |
    sha256sum --check
patch --batch --forward --fuzz=0 -p1 < "$recipe/openssl35-dane-guard.patch"
printf '%s\n' '3c638f6c64c431a88b2e94c9f3ed12fb9b431778d818e8d1fe0e633c5b98aa1a  crypto/x509/x509_vfy.c' |
    sha256sum --check

perl Configure linux-x86_64 shared enable-unit-test enable-ec_nistp_64_gcc_128 \
    --prefix=/usr --libdir=lib/x86_64-linux-gnu --openssldir=/usr/lib/ssl
make -j2
make -j2 test TESTS='test_verify test_verify_store test_verify_extra test_dane test_sslapi'
make DESTDIR="$stage" install_runtime install_modules
