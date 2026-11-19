#!/usr/bin/env python3
"""Produce public, unreviewed Gitleaks build metadata; never publish the binary."""
from __future__ import annotations

import argparse
from contextlib import redirect_stderr, redirect_stdout
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.parse
import urllib.request

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
REPORT_PATCH = HERE / "gitleaks-report-permissions.patch"
OUTPUTS = ("candidate-receipt.json", "go.mod", "go.sum", "modules.json",
           "module-closure.json", "gitleaks-LICENSE.txt")
MARKER = "OFFLINE_GITLEAKS_CANDIDATE "
MAX_FILE_BYTES = 512 * 1024
MAX_TOTAL_BYTES = 2 * 1024 * 1024
CHUNK_CHARACTERS = 2048
STAGES = {"preflight", "inputs", "archives", "toolchain", "resolution",
          "closure", "build", "fixture", "metadata"}
MODULE_PATH = re.compile(r"[A-Za-z0-9._~/-]+\Z")
VERSION = re.compile(r"v[0-9][A-Za-z0-9.+-]*\Z")
H1 = re.compile(r"h1:[A-Za-z0-9+/]{43}=\Z")


class CandidateError(RuntimeError):
    """A fixed public stage label; child output is never included."""

    def __init__(self, stage, *, receipt_ready=False):
        super().__init__(stage)
        self.receipt_ready = receipt_ready


def require(condition, label):
    if not condition:
        raise CandidateError(label)


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "inputs")
        result[key] = value
    return result


def json_bytes(value):
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def git_blob(payload):
    return hashlib.sha1(
        f"blob {len(payload)}\0".encode("ascii") + payload,
        usedforsecurity=False,
    ).hexdigest()


def file_record(payload):
    return {"size_bytes": len(payload), "sha256": hashlib.sha256(payload).hexdigest(),
            "git_blob_sha1": git_blob(payload)}


def regular(path, maximum=MAX_FILE_BYTES):
    info = path.lstat()
    require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1
            and info.st_size <= maximum, "metadata")
    return path.read_bytes()


def load_catalog():
    raw = regular(HERE / "gitleaks-build-sources.json")
    catalog = json.loads(raw, object_pairs_hook=unique_object)
    require(catalog["schema_version"] == 1 and catalog["reviewed"] is False
            and catalog["kind"] == "unreviewed-gitleaks-source-build-candidate", "inputs")
    source, toolchain = catalog["source"], catalog["toolchain"]
    require(re.fullmatch(r"[0-9a-f]{40}", source["commit"]) is not None, "inputs")
    require(source["url"] == "https://codeload.github.com/gitleaks/gitleaks/tar.gz/"
            + source["commit"] and source["prefix"] == "gitleaks-" + source["commit"], "inputs")
    require(toolchain["version"] == "go1.27.4" and toolchain["prefix"] == "go"
            and toolchain["url"] == "https://go.dev/dl/go1.27.4.linux-amd64.tar.gz", "inputs")
    for record in (source, toolchain, source["license"]):
        require(type(record["size_bytes"]) is int and record["size_bytes"] > 0
                and re.fullmatch(r"[0-9a-f]{64}", record["sha256"]) is not None, "inputs")
    updates = catalog["updates"]
    require(len(updates) == 8 and sum(x["requested"] is True for x in updates) == 7
            and len({x["path"] for x in updates}) == 8, "inputs")
    for update in updates:
        require(MODULE_PATH.fullmatch(update["path"])
                and VERSION.fullmatch(update["before"])
                and VERSION.fullmatch(update["after"]), "inputs")
        if update["requested"]:
            require(H1.fullmatch(update["sum"]) and H1.fullmatch(update["go_mod_sum"]), "inputs")
    require(catalog["build"] == {"kind": "local-source-build", "version": "8.30.1",
            "tag": "gore2regex", "goos": "linux", "goarch": "amd64",
            "goamd64": "v1", "cgo_enabled": "0"}, "inputs")
    return catalog, hashlib.sha256(raw).hexdigest()


def download(record, destination):
    digest, count, start = hashlib.sha256(), 0, time.monotonic()
    with urllib.request.urlopen(record["url"], timeout=45) as response:
        parsed = urllib.parse.urlsplit(response.geturl())
        require(parsed.scheme == "https" and parsed.hostname in
                {"go.dev", "dl.google.com", "codeload.github.com"}, "archives")
        with destination.open("xb") as output:
            while chunk := response.read(1024 * 1024):
                count += len(chunk)
                require(count <= record["size_bytes"]
                        and time.monotonic() - start <= 240, "archives")
                digest.update(chunk)
                output.write(chunk)
    require(count == record["size_bytes"]
            and digest.hexdigest() == record["sha256"], "archives")


def unpack(archive, destination, prefix, omitted_links=()):
    """Never create links or execute archive members."""
    destination.mkdir(mode=0o700)
    omitted = {record["path"]: record for record in omitted_links}
    seen, skipped, count, expanded = set(), set(), 0, 0
    with tarfile.open(archive, "r:gz") as source:
        for member in source:
            name = member.name.rstrip("/")
            parts = PurePosixPath(name)
            require(name and str(parts) == name and not parts.is_absolute()
                    and ".." not in parts.parts and parts.parts[0] == prefix
                    and name not in seen and len(seen) < 40000, "archives")
            seen.add(name)
            relative = PurePosixPath(*parts.parts[1:])
            if relative == PurePosixPath("."):
                require(member.isdir(), "archives")
                continue
            relative_name = relative.as_posix()
            if member.issym():
                record = omitted.get(relative_name)
                require(record is not None and member.linkname == record["target"]
                        and git_blob(member.linkname.encode()) == record["git_blob_sha1"],
                        "archives")
                skipped.add(relative_name)
                continue
            require(member.isdir() or member.isreg(), "archives")
            output = destination / relative_name
            if member.isdir():
                output.mkdir(mode=0o700, parents=True, exist_ok=True)
                continue
            expanded += member.size
            require(0 <= member.size <= 256 * 1024 * 1024
                    and expanded <= 1024 * 1024 * 1024, "archives")
            output.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            with source.extractfile(member) as incoming, output.open("xb") as outgoing:
                shutil.copyfileobj(incoming, outgoing)
            require(output.stat().st_size == member.size, "archives")
            output.chmod(0o700 if member.mode & 0o111 else 0o600)
            count += 1
    require(skipped == set(omitted), "archives")
    return {"regular_files": count, "omitted_symlinks": sorted(skipped),
            "expanded_bytes": expanded}


def expected_go_mod(original, catalog):
    text = original.decode("utf-8")
    changes = [(f"go {catalog['go_minimum_before']}\n",
                f"go {catalog['go_minimum_after']}\n")]
    changes.extend((f"{x['path']} {x['before']}", f"{x['path']} {x['after']}")
                   for x in catalog["updates"])
    for before, after in changes:
        require(text.count(before) == 1, "resolution")
        text = text.replace(before, after, 1)
    return text.encode("utf-8")


def assert_go_mod(path, expected):
    require(regular(path) == expected, "resolution")


def environment(work, *, offline=False):
    """Construct an allowlist; inherit no credentials, GO flags, or Git config."""
    return {
        "PATH": "/usr/bin:/bin", "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8",
        "TMPDIR": str(work / "tmp"), "GOTMPDIR": str(work / "tmp"),
        "GOPATH": str(work / "gopath"), "GOMODCACHE": str(work / "modcache"),
        "GOCACHE": str(work / "buildcache"), "GOTOOLCHAIN": "local",
        "GOENV": "off", "GOWORK": "off", "GOTELEMETRY": "off",
        "GOPROXY": "off" if offline else "https://proxy.golang.org",
        "GOSUMDB": "off" if offline else "sum.golang.org",
        "GOPRIVATE": "", "GONOSUMDB": "", "GONOPROXY": "", "GOINSECURE": "",
        "GOVCS": "*:off", "GOOS": "linux", "GOARCH": "amd64", "GOAMD64": "v1",
        "CGO_ENABLED": "0", "GOMAXPROCS": "2",
        "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CONFIG_COUNT": "1", "GIT_CONFIG_KEY_0": "core.hooksPath",
        "GIT_CONFIG_VALUE_0": os.devnull, "GIT_TERMINAL_PROMPT": "0",
    }


def run(command, *, cwd, env, stage, timeout=600, umask=-1):
    completed = subprocess.run(command, cwd=cwd, env=env, stdin=subprocess.DEVNULL,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               check=False, timeout=timeout, umask=umask)
    require(completed.returncode == 0 and len(completed.stdout) <= 8 * 1024 * 1024
            and len(completed.stderr) <= 1024 * 1024, stage)
    return completed.stdout


def apply_report_permissions(source, patch, env):
    target = source / "cmd/root.go"
    require(hashlib.sha256(regular(target)).hexdigest() == patch["before_sha256"], "inputs")
    require(hashlib.sha256(regular(REPORT_PATCH)).hexdigest() == patch["sha256"], "inputs")
    # The catalog pins both file versions, so the patch needs no context lines.
    run(["git", "apply", "--unidiff-zero", "--whitespace=error-all",
         "--include=cmd/root.go", str(REPORT_PATCH)],
        cwd=source, env=env, stage="inputs", timeout=30)
    require(hashlib.sha256(regular(target)).hexdigest() == patch["after_sha256"], "inputs")


def objects(payload):
    text, decoder, result = payload.decode("utf-8"), json.JSONDecoder(
        object_pairs_hook=unique_object), []
    while text.strip():
        text = text.lstrip()
        value, end = decoder.raw_decode(text)
        require(isinstance(value, dict) and len(result) < 1000, "closure")
        result.append(value)
        text = text[end:]
    return result


def module_url(path, version, suffix):
    escaped = "".join("!" + c.lower() if "A" <= c <= "Z" else c for c in path)
    return ("https://proxy.golang.org/" + urllib.parse.quote(escaped, safe="/!")
            + "/@v/" + urllib.parse.quote(version, safe="+!") + "." + suffix)


def module_closure(selected, downloads, cache, catalog, go_sum):
    require(len(selected) == catalog["selected_module_entries"], "closure")
    main = [x for x in selected if x.get("Main") is True]
    require(len(main) == 1 and main[0]["Path"] == catalog["source"]["module"], "closure")
    require(all(not x.get("Replace") and not x.get("Error") for x in selected), "closure")
    required = {}
    for entry in selected:
        if entry.get("Main"):
            continue
        name, version = entry["Path"], entry["Version"]
        require(MODULE_PATH.fullmatch(name) and VERSION.fullmatch(version)
                and name not in required, "closure")
        required[name] = version
    downloaded = {}
    for entry in downloads:
        require(not entry.get("Error") and not entry.get("Replace")
                and entry["Path"] not in downloaded, "closure")
        downloaded[entry["Path"]] = entry
    require(set(downloaded) == set(required), "closure")
    sums = {}
    for line in go_sum.decode("utf-8").splitlines():
        parts = line.split()
        require(len(parts) == 3 and (parts[0], parts[1]) not in sums
                and H1.fullmatch(parts[2]), "closure")
        sums[(parts[0], parts[1])] = parts[2]
    result = []
    for name, version in sorted(required.items()):
        entry = downloaded[name]
        require(entry["Version"] == version and H1.fullmatch(entry["Sum"])
                and H1.fullmatch(entry["GoModSum"]), "closure")
        require(sums.get((name, version)) == entry["Sum"]
                and sums.get((name, version + "/go.mod")) == entry["GoModSum"], "closure")
        files = {}
        for key, suffix in (("Info", "info"), ("GoMod", "mod"), ("Zip", "zip")):
            path = Path(entry[key])
            require(path.resolve().is_relative_to(cache.resolve())
                    and not path.is_symlink(), "closure")
            info = path.stat()
            require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1
                    and 0 < info.st_size <= 256 * 1024 * 1024, "closure")
            with path.open("rb") as stream:
                digest = hashlib.file_digest(stream, "sha256").hexdigest()
            files[suffix] = {"url": module_url(name, version, suffix),
                             "size_bytes": info.st_size, "sha256": digest}
        info = json.loads(Path(entry["Info"]).read_bytes(), object_pairs_hook=unique_object)
        require(info["Version"] == version, "closure")
        result.append({"path": name, "version": version, "sum": entry["Sum"],
                       "go_mod_sum": entry["GoModSum"], "files": files})
    by_name = {x["path"]: x for x in result}
    for update in catalog["updates"]:
        record = by_name.get(update["path"], {})
        require(record.get("version") == update["after"], "closure")
        if update["requested"]:
            require(record.get("sum") == update["sum"]
                    and record.get("go_mod_sum") == update["go_mod_sum"], "closure")
    normalized = [{"path": catalog["source"]["module"], "main": True}]
    normalized.extend({k: x[k] for k in ("path", "version", "sum", "go_mod_sum")}
                      for x in result)
    return normalized, result


def fixture(work, binary, env):
    path = ROOT / "security/offline-ai/scripts/verify_gitleaks.py"
    require(not path.is_symlink() and path.resolve().is_relative_to(ROOT), "fixture")
    spec = importlib.util.spec_from_file_location("_trusted_gitleaks_fixture", path)
    module = importlib.util.module_from_spec(spec)
    original = dict(os.environ)
    fixture_env = dict(env, PATH=str(binary.parent) + ":/usr/bin:/bin")
    try:
        os.environ.clear()
        os.environ.update(fixture_env)
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            spec.loader.exec_module(module)
            module.qualify(ROOT / "security/offline-ai/.gitleaks.toml")
    finally:
        os.environ.clear()
        os.environ.update(original)


def check_report_permissions(work, binary, env):
    clean = work / "clean-scan"
    clean.mkdir()
    (clean / "example.txt").write_text("Public test input only.\n", encoding="utf-8")
    new_report, existing_report = work / "new-report.json", work / "existing-report.json"
    existing_report.write_text("[]\n", encoding="utf-8")
    existing_report.chmod(0o644)
    for report in (new_report, existing_report):
        run([str(binary), "dir", str(clean), "--redact=100", "--report-format", "json",
             "--report-path", str(report)],
            cwd=work, env=env, stage="fixture", timeout=60, umask=0o022)
        require(stat.S_IMODE(report.lstat().st_mode) == 0o600
                and json.loads(regular(report)) in ([], None), "fixture")


def emit_public_metadata(destination, *, complete):
    names = OUTPUTS if complete else ("candidate-receipt.json",)
    require({p.name for p in destination.iterdir()} == set(names), "metadata")
    payloads = {name: regular(destination / name) for name in names}
    require(sum(map(len, payloads.values())) <= MAX_TOTAL_BYTES, "metadata")
    texts = {name: payload.decode("utf-8") for name, payload in payloads.items()}
    require(all("\0" not in value for value in texts.values()), "metadata")
    records = [{"path": name, "encoding": "utf-8", **file_record(payloads[name]),
                "chunks": (len(texts[name]) + CHUNK_CHARACTERS - 1) // CHUNK_CHARACTERS}
               for name in names]
    common = {"schema_version": 1, "artifact": "offline-gitleaks-candidate"}
    def emit(value):
        print(MARKER + json.dumps({**common, **value}, ensure_ascii=True,
                                  sort_keys=True, separators=(",", ":")))
    emit({"kind": "manifest", "files": records})
    for record in records:
        for index in range(record["chunks"]):
            emit({"kind": "chunk", "path": record["path"], "encoding": "utf-8",
                  "sha256": record["sha256"], "git_blob_sha1": record["git_blob_sha1"],
                  "size_bytes": record["size_bytes"], "index": index,
                  "total": record["chunks"],
                  "data": texts[record["path"]][index * CHUNK_CHARACTERS:
                                               (index + 1) * CHUNK_CHARACTERS]})
    emit({"kind": "complete", "files": len(records),
          "total_bytes": sum(map(len, payloads.values()))})


def candidate(destination, *, local_binary=None):
    require(not destination.exists() and not destination.is_symlink(), "preflight")
    destination.mkdir(mode=0o700, parents=True)
    receipt = {"schema_version": 1, "kind": "unreviewed-gitleaks-build-candidate",
               "status": "started", "last_stage": "preflight", "reviewed": False,
               "image_qualified": False, "vulnerability_review_qualified": False,
               "release_qualified": False, "runner_registration_qualified": False,
               "binary_published": False}
    def save():
        (destination / "candidate-receipt.json").write_bytes(json_bytes(receipt))
    save()
    try:
        require(sys.version_info[:3] == (3, 15, 2), "preflight")
        receipt["last_stage"] = "inputs"
        catalog, catalog_hash = load_catalog()
        receipt["catalog_sha256"] = catalog_hash
        receipt["source"] = catalog["source"]
        receipt["toolchain"] = catalog["toolchain"]
        with tempfile.TemporaryDirectory(prefix="offline-gitleaks-candidate-") as temporary:
            work = Path(temporary)
            (work / "tmp").mkdir()
            env = environment(work)
            head = run(["git", "-C", str(ROOT), "rev-parse", "HEAD"],
                       cwd=ROOT, env=env, stage="inputs", timeout=30).decode().strip()
            require(re.fullmatch(r"[0-9a-f]{40}", head) is not None, "inputs")
            receipt["candidate_policy_commit"] = head
            receipt["input_sha256"] = {
                str(path.relative_to(ROOT)): hashlib.sha256(regular(path)).hexdigest()
                for path in (Path(__file__).resolve(), HERE / "gitleaks-build-sources.json",
                             REPORT_PATCH,
                             ROOT / "security/offline-ai/scripts/verify_gitleaks.py",
                             ROOT / "security/offline-ai/.gitleaks.toml")}
            receipt["last_stage"] = "archives"
            source, toolchain = work / "source", work / "toolchain"
            for key, output in (("source", source), ("toolchain", toolchain)):
                archive = work / (key + ".tar.gz")
                download(catalog[key], archive)
                result = unpack(archive, output, catalog[key]["prefix"],
                                catalog[key].get("omitted_symlinks", ()))
                archive.unlink()
                if key == "source":
                    require(result["regular_files"] == catalog["source"]["regular_files"], "archives")
                    receipt["source_extraction"] = result
            original = regular(source / "go.mod")
            require(git_blob(original) == catalog["source"]["original_go_mod_blob_sha1"]
                    and git_blob(regular(source / "go.sum"))
                    == catalog["source"]["original_go_sum_blob_sha1"], "inputs")
            expected = expected_go_mod(original, catalog)
            license_bytes = regular(source / catalog["source"]["license"]["path"])
            require(len(license_bytes) == catalog["source"]["license"]["size_bytes"]
                    and hashlib.sha256(license_bytes).hexdigest()
                    == catalog["source"]["license"]["sha256"], "archives")
            report_patch = catalog["report_permissions_patch"]
            apply_report_permissions(source, report_patch, env)
            receipt["report_permissions_patch"] = report_patch
            receipt["last_stage"] = "toolchain"
            go = str(toolchain / "bin/go")
            actual = run([go, "version"], cwd=source, env=env, stage="toolchain", timeout=30)
            require(actual.decode().strip() == "go version go1.27.4 linux/amd64", "toolchain")
            receipt["last_stage"] = "resolution"
            run([go, "get", *[x["path"] + "@" + x["after"] for x in catalog["updates"]
                             if x["requested"]]], cwd=source, env=env, stage="resolution")
            assert_go_mod(source / "go.mod", expected)
            selected = objects(run([go, "list", "-mod=readonly", "-m", "-json", "all"],
                                   cwd=source, env=env, stage="closure"))
            receipt["last_stage"] = "closure"
            downloads = objects(run([go, "mod", "download", "-json", "all"],
                                    cwd=source, env=env, stage="closure"))
            run([go, "mod", "verify"], cwd=source, env=env, stage="closure")
            assert_go_mod(source / "go.mod", expected)
            go_sum = regular(source / "go.sum")
            modules, closure = module_closure(selected, downloads, work / "modcache",
                                              catalog, go_sum)
            receipt["module_closure_verified"] = True
            receipt["last_stage"] = "build"
            offline = environment(work, offline=True)
            output = work / "binary"
            output.mkdir()
            binary = output / "gitleaks"
            flags = ["-mod=readonly", "-trimpath", "-buildvcs=false",
                     "-tags=gore2regex", "-ldflags=-s -w -buildid= "
                     "-X=github.com/zricethezav/gitleaks/v8/version.Version=8.30.1"]
            # A cold compile takes longer on emulated Linux x86-64 runners.
            run([go, "build", *flags, "-o", str(binary), "."],
                cwd=source, env=offline, stage="build", timeout=1800)
            assert_go_mod(source / "go.mod", expected)
            require(regular(source / "go.sum") == go_sum, "build")
            version = run([str(binary), "version"], cwd=source, env=offline,
                          stage="build", timeout=30).decode().strip()
            require(version == "8.30.1", "build")
            details = run([go, "version", "-m", str(binary)], cwd=source, env=offline,
                          stage="build", timeout=30).decode()
            require(details.splitlines()[0].endswith(": go1.27.4"), "build")
            fields = [line.strip().split("\t") for line in details.splitlines()[1:]]
            compiled = {x[1]: x[2] for x in fields if len(x) >= 3 and x[0] == "dep"}
            settings = {x[1] for x in fields if len(x) >= 2 and x[0] == "build"}
            require(all(compiled.get(x["path"]) == x["after"] for x in catalog["updates"])
                    and {"CGO_ENABLED=0", "GOOS=linux", "GOARCH=amd64", "GOAMD64=v1"}
                    <= settings, "build")
            with binary.open("rb") as stream:
                binary_digest = hashlib.file_digest(stream, "sha256").hexdigest()
            receipt["build"] = {**catalog["build"], "compiler": "go1.27.4", "flags": flags,
                                "binary_sha256": binary_digest,
                                "binary_size_bytes": binary.stat().st_size,
                                "module_versions": compiled,
                                "build_settings": sorted(settings),
                                "network_module_lookup": False}
            receipt["last_stage"] = "fixture"
            fixture(work, binary, offline)
            receipt["fixture"] = {"status": "passed", "kind": "existing-clean-and-canary-git"}
            check_report_permissions(work, binary, offline)
            receipt["report_permissions"] = {"status": "passed", "mode": "0600",
                                             "paths": ["new", "existing"]}
            receipt["last_stage"] = "metadata"
            payloads = {"go.mod": expected, "go.sum": go_sum, "modules.json": json_bytes(modules),
                        "module-closure.json": json_bytes(closure),
                        "gitleaks-LICENSE.txt": license_bytes}
            require(all(len(x) <= MAX_FILE_BYTES for x in payloads.values())
                    and sum(map(len, payloads.values())) <= MAX_TOTAL_BYTES - MAX_FILE_BYTES,
                    "metadata")
            for name, payload in payloads.items():
                (destination / name).write_bytes(payload)
            receipt["files"] = [{"path": name, **file_record(payload)}
                                for name, payload in payloads.items()]
            receipt["status"] = "candidate_complete"
            receipt["last_stage"] = "complete"
            # The optional sink is used only by the evidence-only image build.
            # The binary is never included in public candidate metadata.
            if local_binary is not None:
                local_binary(binary, payloads, receipt)
            save()
        return receipt
    except (Exception, KeyboardInterrupt):
        stage = receipt["last_stage"]
        receipt["status"] = "failed"
        receipt["failed_stage"] = stage if stage in STAGES else "metadata"
        for name in OUTPUTS[1:]:
            path = destination / name
            if path.exists() or path.is_symlink():
                path.unlink()
        save()
        raise CandidateError(receipt["failed_stage"], receipt_ready=True) from None


class SafeParser(argparse.ArgumentParser):
    def error(self, message):
        raise CandidateError("preflight")


def main():
    destination = None
    try:
        parser = SafeParser(description=__doc__)
        parser.add_argument("--destination", required=True, type=Path)
        destination = parser.parse_args().destination.absolute()
        candidate(destination)
        emit_public_metadata(destination, complete=True)
        return 0
    except (Exception, KeyboardInterrupt) as error:
        if (isinstance(error, CandidateError) and error.receipt_ready
                and destination is not None
                and (destination / "candidate-receipt.json").is_file()):
            try:
                emit_public_metadata(destination, complete=False)
            except Exception:
                pass
        print("Offline Gitleaks candidate failed; review the fixed-stage receipt", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
