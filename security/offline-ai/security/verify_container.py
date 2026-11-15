"""Verify the controls actually applied to the scanner's running container.

This is a strict cgroup-v2 Docker profile. The process's own cgroup must expose
finite limits; an incidental limit on a shared ancestor is not qualification.
This check does not establish host firewall policy or runner eligibility.
"""
from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import sys


PROC_ROOT = Path("/proc")
FILESYSTEM_ROOT = Path("/")
MESSAGE = "Scanner container verification failed"
TOOLS = ("gitleaks", "opengrep", "python", "promptfoo", "git", "node")
CAPABILITIES = ("CapInh", "CapPrm", "CapEff", "CapBnd", "CapAmb")


class ContainerIsolationError(RuntimeError):
    """A fixed, value-free failure suitable for scanner logs."""


def _fail():
    raise ContainerIsolationError(MESSAGE)


def _read_proc(name, maximum):
    with (PROC_ROOT / "self" / name).open("rb") as stream:
        value = stream.read(maximum + 1)
    if len(value) > maximum:
        _fail()
    return value.decode("utf-8")


def _path(value):
    if (not value.startswith("/") or value.startswith("//")
            or any(ord(character) < 32 or ord(character) == 127 for character in value)):
        _fail()
    path = PurePosixPath(value)
    if str(path) != value or ".." in path.parts:
        _fail()
    return path


def _mount_path(value):
    escapes = {"040": " ", "011": "\t", "012": "\n", "134": "\\"}
    if re.search(r"\\(?!040|011|012|134)", value):
        _fail()
    return _path(re.sub(r"\\(040|011|012|134)",
                        lambda match: escapes[match.group(1)], value))


@dataclass(frozen=True)
class Mount:
    root: PurePosixPath
    point: PurePosixPath
    options: frozenset[str]
    filesystem: str


def _mounts(value):
    records = []
    identifiers = set()
    for line in value.splitlines():
        fields = line.split()
        if fields.count("-") != 1:
            _fail()
        separator = fields.index("-")
        if separator < 6 or len(fields) != separator + 4:
            _fail()
        if (not fields[0].isdigit() or not fields[1].isdigit()
                or not re.fullmatch(r"[0-9]+:[0-9]+", fields[2])
                or fields[0] in identifiers):
            _fail()
        identifiers.add(fields[0])
        options = frozenset(fields[5].split(","))
        if not options or "" in options or len(options & {"ro", "rw"}) != 1:
            _fail()
        records.append(Mount(_mount_path(fields[3]), _mount_path(fields[4]),
                             options, fields[separator + 1]))
    if not records:
        _fail()
    return records


def _identity(value):
    required = {"Uid", "Gid", "NoNewPrivs", *CAPABILITIES}
    fields = {}
    for line in value.splitlines():
        name, separator, text = line.partition(":")
        if name in required:
            if not separator or name in fields:
                _fail()
            fields[name] = text.strip()
    if fields.keys() != required or fields["NoNewPrivs"] != "1":
        _fail()
    if os.geteuid() != 65534 or os.getegid() != 65534:
        _fail()
    for name in ("Uid", "Gid"):
        if fields[name].split() != ["65534"] * 4:
            _fail()
    for name in CAPABILITIES:
        if not re.fullmatch(r"[0-9a-fA-F]{1,16}", fields[name]) or int(fields[name], 16):
            _fail()


def _readonly_policy(mounts):
    for point in (PurePosixPath("/"), PurePosixPath("/policy")):
        matching = [mount for mount in mounts if mount.point == point]
        if len(matching) != 1 or "ro" not in matching[0].options:
            _fail()
    for mount in mounts:
        if mount.point.is_relative_to("/policy") and "ro" not in mount.options:
            _fail()


def _cgroup_directory(mounts, membership):
    lines = membership.splitlines()
    if len(lines) != 1 or not lines[0].startswith("0::"):
        _fail()
    member = _path(lines[0][3:])
    candidates = [mount for mount in mounts if mount.filesystem == "cgroup2"]
    if len(candidates) != 1:
        _fail()
    mount = candidates[0]
    if "ro" not in mount.options:
        _fail()
    # Bind mounts over controls or subtrees could substitute another group's
    # limits. Docker's private cgroup-v2 mount needs no such nested mounts.
    if any(other is not mount and other.point.is_relative_to(mount.point)
           for other in mounts):
        _fail()
    try:
        relative = member.relative_to(mount.root)
    except ValueError:
        _fail()
    return mount.point / relative


def _read_control(path):
    """Resolve every directory without following symlinks; never read a FIFO."""
    directory = os.open(FILESYSTEM_ROOT,
                        os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        for component in path.parts[1:-1]:
            child = os.open(component,
                            os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
                            dir_fd=directory)
            os.close(directory)
            directory = child
        descriptor = os.open(path.name,
                             os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC,
                             dir_fd=directory)
        try:
            if not stat.S_ISREG(os.fstat(descriptor).st_mode):
                _fail()
            value = os.read(descriptor, 4097)
        finally:
            os.close(descriptor)
    finally:
        os.close(directory)
    if len(value) > 4096:
        _fail()
    return value.decode("ascii").strip()


def _positive_integer(value):
    if not re.fullmatch(r"[1-9][0-9]{0,19}", value):
        _fail()
    return int(value)


def _limits(directory):
    memory = _positive_integer(_read_control(directory / "memory.max"))
    pids = _positive_integer(_read_control(directory / "pids.max"))
    cpu = _read_control(directory / "cpu.max").split()
    if len(cpu) != 2:
        _fail()
    quota, period = (_positive_integer(value) for value in cpu)
    if memory > 8 * 1024 ** 3 or pids > 256 or quota > 4 * period:
        _fail()


def verify_container():
    """Check the real process, mount table and its own cgroup; no host mutation."""
    try:
        if sys.version_info[:3] != (3, 15, 2) or not all(shutil.which(name) for name in TOOLS):
            _fail()
        _identity(_read_proc("status", 65536))
        mounts = _mounts(_read_proc("mountinfo", 1024 * 1024))
        _readonly_policy(mounts)
        directory = _cgroup_directory(mounts, _read_proc("cgroup", 4096))
        _limits(directory)
    except (OSError, UnicodeError, ValueError):
        raise ContainerIsolationError(MESSAGE) from None


def main(argv=None):
    try:
        if (sys.argv[1:] if argv is None else argv):
            _fail()
        verify_container()
    except ContainerIsolationError:
        print(MESSAGE, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
