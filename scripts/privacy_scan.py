#!/usr/bin/env python3
"""Scan Git text blobs using local Presidio recognizers, without NLP downloads.

The repository profile blocks contextual/structured financial and Australian
identifiers. Contact details are advisory outside data-oriented paths. This is
a targeted repository check, not a clinical de-identification certification.
No matched values, source snippets, or exception details are reported.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import subprocess
from bisect import bisect_right
from collections import Counter
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

MAX_FILE_BYTES = 10 * 1024 * 1024
CHUNK_SIZE = 65536
CHUNK_OVERLAP = 256
MAX_REPORTED_FINDINGS = 1000
MAX_REPORTED_SKIPS = 100
SHA_PATTERN = re.compile(r"[0-9a-fA-F]{40}(?:[0-9a-fA-F]{24})?\Z")
DATA_PARTS = frozenset({"data", "datasets", "fixtures", "exports", "records"})
CONTEXT = {
    "AU_TFN": re.compile(
        r"\b(?:tfn|tax[\s_-]*file(?:[\s_-]*number)?)\b", re.IGNORECASE
    ),
    "AU_MEDICARE": re.compile(r"\bmedicare\b", re.IGNORECASE),
    "CREDIT_CARD": re.compile(
        r"\b(?:credit[\s_-]*card|debit[\s_-]*card|card[\s_-]*(?:number|no|num)|pan|cc[\s_-]*number)\b",
        re.IGNORECASE,
    ),
    "IBAN_CODE": re.compile(
        r"\b(?:iban|international[\s_-]*bank[\s_-]*account)\b", re.IGNORECASE
    ),
}
LIMITATIONS = [
    "Names, addresses, clinical narratives and re-identification risk are not covered by this baseline.",
    "Only selected Git text blobs are scanned; images, binary documents, LFS payloads and submodule contents are not scanned.",
    "Repository checks do not inspect application runtime data or prevent upload before CI executes.",
    "Detection is probabilistic; no findings is not a declaration that data is anonymous or safe to publish.",
]


class ScanError(Exception):
    """A failure described by a fixed, non-sensitive diagnostic code."""


class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        # argparse's default error text can echo user-supplied sensitive values.
        raise ScanError("invalid_arguments")


class RecognizerDiagnostics(logging.Handler):
    """Notice incomplete recognizer execution without retaining logged values."""

    def __init__(self) -> None:
        super().__init__(logging.WARNING)
        self.failed = False

    def emit(self, record: logging.LogRecord) -> None:
        self.failed = True


@contextmanager
def recognizer_diagnostics() -> Iterator[RecognizerDiagnostics]:
    logger = logging.getLogger("presidio-analyzer")
    previous = (logger.handlers[:], logger.level, logger.propagate, logger.disabled)
    diagnostics = RecognizerDiagnostics()
    logger.handlers = [diagnostics]
    logger.setLevel(logging.WARNING)
    logger.propagate = False
    logger.disabled = False
    try:
        yield diagnostics
    finally:
        logger.handlers, logger.level, logger.propagate, logger.disabled = previous


@dataclass(frozen=True)
class Blob:
    path: str
    oid: str
    mode: str


def git_environment() -> dict[str, str]:
    """Do not let an inherited Git override change the repository being read."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env.update(
        {
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_TERMINAL_PROMPT": "0",
        }
    )
    return env


def git_command(root: Path, *args: str) -> list[str]:
    return [
        "git",
        "--no-pager",
        "--no-replace-objects",
        "-C",
        str(root),
        "-c",
        "core.hooksPath=/dev/null",
        "-c",
        "core.fsmonitor=false",
        *args,
    ]


def git(root: Path, *args: str, input_data: bytes | None = None) -> bytes:
    result = subprocess.run(
        git_command(root, *args),
        input=input_data,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        env=git_environment(),
        check=False,
    )
    if result.returncode:
        raise ScanError("git_read_failed")
    return result.stdout


def resolve_commit(root: Path, value: str, *, allow_head: bool = False) -> str:
    if not (allow_head and value == "HEAD") and not SHA_PATTERN.fullmatch(value):
        raise ScanError("invalid_commit_reference")
    resolved = (
        git(root, "rev-parse", "--verify", value + "^{commit}").decode("ascii").strip()
    )
    if not SHA_PATTERN.fullmatch(resolved):
        raise ScanError("invalid_commit_object")
    return resolved


def selected_blobs(root: Path, base: str | None, head: str, staged: bool) -> list[Blob]:
    changed: set[bytes] | None = None
    if staged:
        raw = git(root, "ls-files", "--stage", "-z")
        changed = set(
            git(
                root,
                "diff",
                "--cached",
                "--no-renames",
                "--name-only",
                "--diff-filter=ACMRT",
                "-z",
                "--",
            ).split(b"\0")
        )
    else:
        head_oid = resolve_commit(root, head, allow_head=True)
        raw = git(root, "ls-tree", "-r", "-z", "--full-tree", head_oid)
    if base is not None:
        base_oid = resolve_commit(root, base)
        changed = set(
            git(
                root,
                "diff-tree",
                "-r",
                "--no-commit-id",
                "--no-renames",
                "--name-only",
                "--diff-filter=ACMRT",
                "-z",
                base_oid,
                head_oid,
            ).split(b"\0")
        )
    blobs = []
    for row in raw.split(b"\0"):
        if not row:
            continue
        meta, path_raw = row.split(b"\t", 1)
        mode, middle, final = meta.decode("ascii").split(" ")
        if staged:
            if final != "0":
                raise ScanError("unmerged_index")
            oid = middle
        else:
            oid = final
        if changed is not None and path_raw not in changed:
            continue
        if not SHA_PATTERN.fullmatch(oid):
            raise ScanError("invalid_blob_object")
        blobs.append(Blob(path_raw.decode("utf-8", "surrogateescape"), oid, mode))
    return blobs


def blob_sizes(root: Path, blobs: Sequence[Blob]) -> dict[str, int]:
    oids = list(dict.fromkeys(b.oid for b in blobs))
    if not oids:
        return {}
    raw = git(
        root,
        "cat-file",
        "--batch-check=%(objectname) %(objecttype) %(objectsize)",
        input_data=("\n".join(oids) + "\n").encode("ascii"),
    )
    sizes = {}
    for row in raw.decode("ascii").splitlines():
        fields = row.split(" ")
        if len(fields) != 3 or fields[1] != "blob" or not fields[2].isdigit():
            raise ScanError("invalid_blob_metadata")
        sizes[fields[0]] = int(fields[2])
    if set(sizes) != set(oids):
        raise ScanError("incomplete_blob_metadata")
    return sizes


@contextmanager
def blob_reader(root: Path) -> Iterator[Any]:
    """Read immutable blobs in one Git process; no checked-out path is opened."""
    process = subprocess.Popen(
        git_command(root, "cat-file", "--batch"),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        env=git_environment(),
    )
    try:
        yield process
    finally:
        if process.stdin:
            process.stdin.close()
        if process.stdout:
            process.stdout.close()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


def read_blob(process: Any, blob: Blob, size: int) -> bytes:
    if process.stdin is None or process.stdout is None:
        raise ScanError("git_blob_reader_failed")
    process.stdin.write((blob.oid + "\n").encode("ascii"))
    process.stdin.flush()
    expected = f"{blob.oid} blob {size}\n".encode("ascii")
    if process.stdout.readline() != expected:
        raise ScanError("git_blob_read_failed")
    data = process.stdout.read(size)
    if len(data) != size or process.stdout.read(1) != b"\n":
        raise ScanError("incomplete_blob_read")
    return data


def build_recognizers() -> list[Any]:
    """Use upstream pattern/checksum recognizers, with no AnalyzerEngine/NLP model."""
    try:
        import tldextract
        from presidio_analyzer.predefined_recognizers import (
            AuMedicareRecognizer,
            AuTfnRecognizer,
            CreditCardRecognizer,
            EmailRecognizer,
            IbanRecognizer,
            PhoneRecognizer,
        )

        # Upstream EmailRecognizer otherwise refreshes the public-suffix list
        # over HTTP. Reuse its regex and bundled validation data without IO.
        extract_domain = tldextract.TLDExtract(suffix_list_urls=(), cache_dir=None)

        class OfflineEmailRecognizer(EmailRecognizer):
            def validate_result(self, pattern_text: str) -> bool:
                return extract_domain(pattern_text).fqdn != ""

        return [
            AuTfnRecognizer(),
            AuMedicareRecognizer(),
            CreditCardRecognizer(),
            IbanRecognizer(),
            OfflineEmailRecognizer(),
            PhoneRecognizer(supported_regions=["AU", "NZ"]),
        ]
    except (ImportError, OSError):
        raise ScanError("presidio_unavailable") from None


def is_sensitive_path(path: str) -> bool:
    return any(part.casefold() in DATA_PARTS for part in path.split("/")[:-1])


def severity(
    entity: str, text: str, start: int, end: int, sensitive: bool, profile: str
) -> str:
    if profile == "sensitive":
        return "blocking"
    if entity in {"EMAIL_ADDRESS", "PHONE_NUMBER"}:
        return "blocking" if sensitive else "advisory"
    value = text[start:end]
    formatted = bool(re.search(r"[\s-]", value))
    context = text[max(0, start - 96) : min(len(text), end + 96)]
    contextual = bool(CONTEXT[entity].search(context))
    return "blocking" if formatted or contextual else "advisory"


def analyze_text(
    text: str, path: str, recognizers: Sequence[Any], profile: str
) -> list[dict[str, Any]]:
    seen: set[tuple[str, int, int]] = set()
    counts: Counter[tuple[int, str, str]] = Counter()
    sensitive = is_sensitive_path(path)
    newlines = [i for i, char in enumerate(text) if char == "\n"]
    step = CHUNK_SIZE - CHUNK_OVERLAP
    with recognizer_diagnostics() as diagnostics:
        for offset in range(0, len(text), step):
            chunk = text[offset : offset + CHUNK_SIZE]
            for recognizer in recognizers:
                matches = recognizer.analyze(
                    text=chunk,
                    entities=recognizer.supported_entities,
                    nlp_artifacts=None,
                )
                if diagnostics.failed:
                    raise ScanError("recognizer_incomplete")
                for match in matches:
                    if match.score <= 0:
                        continue
                    start, end = offset + match.start, offset + match.end
                    key = (match.entity_type, start, end)
                    if key in seen:
                        continue
                    seen.add(key)
                    line = bisect_right(newlines, start - 1) + 1
                    level = severity(
                        match.entity_type, text, start, end, sensitive, profile
                    )
                    counts[(line, match.entity_type, level)] += 1
            if offset + CHUNK_SIZE >= len(text):
                break
    return [
        {
            "path": path,
            "line": line,
            "entity": entity,
            "severity": level,
            "count": count,
        }
        for (line, entity, level), count in sorted(counts.items())
    ]


def scan_repository(
    root: Path,
    *,
    base: str | None = None,
    head: str = "HEAD",
    staged: bool = False,
    profile: str = "repository",
    recognizers: Sequence[Any] | None = None,
) -> dict[str, Any]:
    if staged and base is not None:
        raise ScanError("conflicting_scan_scopes")
    if profile not in {"repository", "sensitive"}:
        raise ScanError("invalid_profile")
    if recognizers is None:
        recognizers = build_recognizers()
    blobs = selected_blobs(root, base, head, staged)
    skipped: list[dict[str, str]] = []
    regular = []
    for blob in blobs:
        if blob.mode == "160000":
            skipped.append({"path": blob.path, "reason": "submodule"})
        elif blob.mode == "120000":
            skipped.append({"path": blob.path, "reason": "symlink"})
        elif blob.mode not in {"100644", "100755"}:
            raise ScanError("unsupported_git_mode")
        else:
            regular.append(blob)
    sizes = blob_sizes(root, regular)
    findings: list[dict[str, Any]] = []
    scanned = 0
    with blob_reader(root) as reader:
        for blob in regular:
            size = sizes[blob.oid]
            if size > MAX_FILE_BYTES:
                skipped.append({"path": blob.path, "reason": "oversized"})
                continue
            data = read_blob(reader, blob, size)
            if data.startswith(b"version https://git-lfs.github.com/spec/v1\n"):
                skipped.append({"path": blob.path, "reason": "lfs_pointer"})
                continue
            if b"\0" in data:
                skipped.append({"path": blob.path, "reason": "binary"})
                continue
            try:
                text = data.decode("utf-8-sig")
            except UnicodeDecodeError:
                skipped.append({"path": blob.path, "reason": "non_utf8_or_binary"})
                continue
            findings.extend(analyze_text(text, blob.path, recognizers, profile))
            scanned += 1
    blocked = sum(f["count"] for f in findings if f["severity"] == "blocking")
    advisory = sum(f["count"] for f in findings if f["severity"] == "advisory")
    status = (
        "blocking_findings"
        if blocked
        else "incomplete"
        if skipped
        else "advisory_findings"
        if advisory
        else "no_supported_identifiers_detected"
    )
    return {
        "schema_version": 1,
        "engine": "presidio",
        "profile": profile,
        "scope": "staged" if staged else "changed" if base else "tracked",
        "status": status,
        "files_selected": len(blobs),
        "files_scanned": scanned,
        "blocking_findings": blocked,
        "advisory_findings": advisory,
        "findings": findings[:MAX_REPORTED_FINDINGS],
        "findings_omitted": max(0, len(findings) - MAX_REPORTED_FINDINGS),
        "skipped": skipped[:MAX_REPORTED_SKIPS],
        "skipped_count": len(skipped),
        "skipped_counts_by_reason": dict(
            sorted(Counter(item["reason"] for item in skipped).items())
        ),
        "skipped_omitted": max(0, len(skipped) - MAX_REPORTED_SKIPS),
        "coverage_complete": not skipped,
        "limitations": LIMITATIONS,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = SafeArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--base", help="Full commit SHA: scan changed files in base..head"
    )
    group.add_argument(
        "--staged", action="store_true", help="Scan index blobs, not working-tree files"
    )
    parser.add_argument("--head", default="HEAD", help="HEAD or full commit SHA")
    parser.add_argument(
        "--profile", choices=("repository", "sensitive"), default="repository"
    )
    parser.add_argument("--report", type=Path, help="Optional value-free JSON report")
    try:
        args = parser.parse_args(argv)
        report = scan_repository(
            args.root,
            base=args.base,
            head=args.head,
            staged=args.staged,
            profile=args.profile,
        )
        output = json.dumps(report, ensure_ascii=True, sort_keys=True)
        if args.report is not None:
            args.report.write_text(output + "\n", encoding="utf-8")
        print(output)
        return 1 if report["blocking_findings"] else 0
    except Exception:  # noqa: BLE001 - never print third-party exception data at the public CLI boundary
        # Exception messages may include input values; never disclose them.
        print(
            json.dumps(
                {
                    "schema_version": 1,
                    "engine": "presidio",
                    "status": "error",
                    "error": "privacy_scan_failed",
                }
            )
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
