#!/usr/bin/env python3
"""Prepare pinned Debian packages online; install those exact bytes offline.

The catalog is reviewed source, never a resolver input. Installation requires
the recorded Python image's real dpkg status and preserves Debian's own records.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import urllib.parse
import urllib.request

HERE = Path(__file__).resolve().parent
CATALOG = "os-packages.json"
CATALOGS = {
    "runtime": CATALOG,
    "git-compiler": "git-compiler-packages.json",
    "openssl-compiler": "openssl-compiler-packages.json",
}
BASE_STATUS = Path("/var/lib/dpkg/status")
ERROR = "Offline OS package preparation failed"
HASH = re.compile(r"[0-9a-f]{64}\Z")
NAME = re.compile(r"[a-z0-9][a-z0-9+.-]*\Z")
VERSION = re.compile(r"[0-9][A-Za-z0-9.+:~\-]*\Z")
ROOTS = {
    "runtime": {"libatomic1", "libgomp1", "libstdc++6", "libgcc-s1", "zlib1g"},
    "git-compiler": {"gcc", "make", "libc6-dev", "zlib1g-dev"},
    "openssl-compiler": {"debhelper", "dpkg-dev", "libzstd-dev", "zlib1g-dev"},
}
QUERY = "${Package}\t${Version}\t${Architecture}\t${db:Status-Abbrev}\n"


class PreparationError(RuntimeError):
    """Details are not printed by the CLI."""


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise PreparationError("duplicate-key")
        result[key] = value
    return result


def digest(path):
    if not stat.S_ISREG(path.lstat().st_mode):
        raise PreparationError("regular-file")
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def read_catalog(path, profile="runtime"):
    digest(path)
    data = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique_object)
    if (data.get("schema_version") != 1 or data.get("distribution") != "trixie"
            or data.get("architecture") != "amd64"
            or not re.fullmatch(r"docker.io/library/python@sha256:[0-9a-f]{64}",
                                data.get("base_image", ""))
            or not HASH.fullmatch(data.get("base_status_sha256", ""))):
        raise PreparationError("catalog")
    if profile == "openssl-compiler" and (
            data.get("base_stage") != "git-compiler"
            or not HASH.fullmatch(data.get("base_catalog_sha256", ""))):
        raise PreparationError("base-catalog")
    packages, baseline = data.get("packages"), data.get("required_base")
    if (not isinstance(packages, list) or not 1 <= len(packages) <= 64
            or not isinstance(baseline, dict) or not 1 <= len(baseline) <= 128):
        raise PreparationError("catalog")
    for name, version in baseline.items():
        if not NAME.fullmatch(name) or not VERSION.fullmatch(version):
            raise PreparationError("catalog")
    names, filenames, total = set(), set(), 0
    max_package_bytes = (32 if profile == "git-compiler" else 16) * 1024 * 1024
    for package in packages:
        name, version = package.get("name", ""), package.get("version", "")
        architecture = package.get("architecture")
        filename, url = package.get("filename", ""), package.get("url", "")
        parsed = urllib.parse.urlsplit(url)
        if (not NAME.fullmatch(name) or not VERSION.fullmatch(version)
                or architecture not in ("amd64", "all")
                or filename != f"{name}_{version.split(':', 1)[-1]}_{architecture}.deb"
                or parsed.scheme != "https" or parsed.netloc != "deb.debian.org"
                or parsed.query or parsed.fragment
                or not re.fullmatch(
                    r"/(?:debian/pool/main|debian-security/pool/updates/main)"
                    r"/[a-z0-9]+/[a-z0-9+.-]+/" + re.escape(filename), parsed.path)
                or not HASH.fullmatch(package.get("sha256", ""))
                or type(package.get("size_bytes")) is not int
                or not 0 < package["size_bytes"] <= max_package_bytes
                or name in names or filename in filenames or name in baseline):
            raise PreparationError("catalog")
        names.add(name)
        filenames.add(filename)
        total += package["size_bytes"]
    installed_names = names | set(baseline)
    if (total > 64 * 1024 * 1024 or not ROOTS[profile] <= installed_names
            or installed_names & {"git", "libcurl3t64-gnutls"}
            or (profile == "runtime" and installed_names & ROOTS["git-compiler"])):
        raise PreparationError("catalog")
    return data


def command(arguments, *, capture=False):
    result = subprocess.run(
        [str(arg) for arg in arguments], stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE if capture else subprocess.DEVNULL,
        stderr=subprocess.DEVNULL, check=True, timeout=300,
        env={"PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
             "LC_ALL": "C", "DEBIAN_FRONTEND": "noninteractive"})
    value = result.stdout or b""
    if len(value) > 65536:
        raise PreparationError("command-output")
    return value


def download(package, path):
    if path.exists() or path.is_symlink():
        raise PreparationError("destination")
    created = False
    try:
        request = urllib.request.Request(
            package["url"], headers={"User-Agent": "offline-ai-os-preparation"})
        with urllib.request.urlopen(request, timeout=90) as response:
            if urllib.parse.urlsplit(response.geturl()).scheme != "https":
                raise PreparationError("download-transport")
            with path.open("xb") as target:
                created = True
                checksum, size = hashlib.sha256(), 0
                while chunk := response.read(1024 * 1024):
                    size += len(chunk)
                    if size > package["size_bytes"]:
                        raise PreparationError("download-size")
                    checksum.update(chunk)
                    target.write(chunk)
        if size != package["size_bytes"] or checksum.hexdigest() != package["sha256"]:
            raise PreparationError("download-integrity")
        path.chmod(0o644)
    except BaseException:
        if created:
            path.unlink(missing_ok=True)
        raise


def verify_packages(directory, catalog):
    debs = directory / "debs"
    if debs.is_symlink() or not debs.is_dir():
        raise PreparationError("package-directory")
    expected = {p["filename"] for p in catalog["packages"]}
    if {p.name for p in debs.iterdir()} != expected:
        raise PreparationError("package-set")
    paths = []
    for package in catalog["packages"]:
        path = debs / package["filename"]
        if digest(path) != package["sha256"] or path.stat().st_size != package["size_bytes"]:
            raise PreparationError("package-integrity")
        raw = command(["dpkg-deb", "--field", path, "Package", "Version", "Architecture"],
                      capture=True)
        fields = unique_object(line.split(": ", 1) for line in raw.decode().splitlines())
        if fields != {"Package": package["name"], "Version": package["version"],
                      "Architecture": package["architecture"]}:
            raise PreparationError("package-identity")
        paths.append(path)
    return paths


def installed_versions(catalog):
    expected = dict(catalog["required_base"])
    expected.update({p["name"]: p["version"] for p in catalog["packages"]})
    raw = command(["dpkg-query", "--show", "--showformat=" + QUERY, *sorted(expected)],
                  capture=True)
    actual = {}
    for line in raw.decode().splitlines():
        name, version, architecture, status = line.split("\t")
        if name in actual or status != "ii " or architecture not in ("amd64", "all"):
            raise PreparationError("installed-status")
        actual[name] = version
    if actual != expected or command(["dpkg", "--audit"], capture=True):
        raise PreparationError("installed-versions")
    return actual


def write_receipt(path, record):
    with path.open("x", encoding="utf-8") as stream:
        os.fchmod(stream.fileno(), 0o600)
        json.dump(record, stream, indent=2, sort_keys=True)
        stream.write("\n")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--destination", type=Path)
    mode.add_argument("--install", type=Path)
    parser.add_argument("--profile", choices=CATALOGS, default="runtime")
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args(argv)
    catalog_name = CATALOGS[args.profile]
    record = {"schema_version": 1, "kind": "offline-os-packages",
              "status": "failed", "last_stage": "preflight",
              "profile": args.profile,
              "release_qualified": False, "runner_registration_qualified": False}
    can_record = False
    try:
        if args.receipt.exists() or args.receipt.is_symlink():
            raise PreparationError("receipt-exists")
        args.receipt.parent.mkdir(parents=True, exist_ok=True)
        can_record = True
        directory = args.install if args.install is not None else HERE
        if directory.is_symlink() or not directory.is_dir():
            raise PreparationError("directory")
        record["last_stage"] = "catalog"
        catalog = read_catalog(directory / catalog_name, args.profile)
        record.update({"base_image": catalog["base_image"],
                       "base_status_sha256": catalog["base_status_sha256"],
                       "catalog_sha256": digest(directory / catalog_name),
                       "preparer_sha256": digest(HERE / "prepare_os_packages.py"),
                       "package_count": len(catalog["packages"])})
        if args.destination is not None:
            record["last_stage"] = "preparation"
            images = json.loads((HERE / "base-images.json").read_text(encoding="utf-8"),
                                object_pairs_hook=unique_object)
            if images["python"]["reference"] != catalog["base_image"]:
                raise PreparationError("base-image")
            if (args.profile == "openssl-compiler"
                    and catalog["base_catalog_sha256"] != digest(HERE / CATALOGS["git-compiler"])):
                raise PreparationError("base-catalog")
            destination = args.destination
            destination.mkdir(mode=0o755)
            (destination / "debs").mkdir(mode=0o755)
            for name in (catalog_name, "prepare_os_packages.py"):
                (destination / name).write_bytes((HERE / name).read_bytes())
                (destination / name).chmod(0o644)
            record["last_stage"] = "downloads"
            for package in catalog["packages"]:
                download(package, destination / "debs" / package["filename"])
            record["last_stage"] = "package-verification"
            verify_packages(destination, catalog)
            record["status"] = "prepared"
        else:
            record["last_stage"] = "base-status"
            if (digest(BASE_STATUS) != catalog["base_status_sha256"]
                    or command(["dpkg", "--print-architecture"], capture=True) != b"amd64\n"):
                raise PreparationError("base-status")
            record["last_stage"] = "package-verification"
            paths = verify_packages(directory, catalog)
            record["last_stage"] = "offline-install"
            command(["dpkg", "--install", *paths])
            record["last_stage"] = "installed-versions"
            record["installed_versions"] = installed_versions(catalog)
            record["status"] = "installed"
        record["last_stage"] = "complete"
    except (Exception, KeyboardInterrupt):
        print(ERROR, file=sys.stderr)
    if can_record:
        try:
            write_receipt(args.receipt, record)
        except (Exception, KeyboardInterrupt):
            print(ERROR, file=sys.stderr)
            return 2
    return 0 if record["status"] in ("prepared", "installed") else 2


if __name__ == "__main__":
    raise SystemExit(main())
