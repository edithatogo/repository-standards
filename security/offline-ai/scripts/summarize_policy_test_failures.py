"""Report trusted policy test names without logging JUnit details."""

from __future__ import annotations

import ast
import sys
from pathlib import Path
from xml.etree import ElementTree

MAX_REPORT_BYTES = 2 * 1024 * 1024
TESTS = Path(__file__).resolve().parents[1] / "tests"


def failure_names(
    report: Path, test_files: list[Path], root: Path = TESTS
) -> list[str]:
    known = {}
    for path in test_files:
        if (
            path.parent.resolve() != root
            or not path.name.startswith("test_")
            or path.suffix != ".py"
        ):
            raise ValueError("Unexpected policy test file")
        source = ast.parse(path.read_bytes())
        known[path.stem] = {
            node.name
            for node in source.body
            if isinstance(node, ast.FunctionDef) and node.name.startswith("test_")
        }
    with report.open("rb") as stream:
        payload = stream.read(MAX_REPORT_BYTES + 1)
    if len(payload) > MAX_REPORT_BYTES:
        raise ValueError("Policy test report too large")
    failures = set()
    for case in ElementTree.fromstring(payload).iter("testcase"):
        if case.find("failure") is None and case.find("error") is None:
            continue
        module = case.get("classname", "").rsplit(".", 1)[-1]
        name = case.get("name", "").partition("[")[0]
        if module in known:
            failures.add(f"{module}.{name}" if name in known[module] else module)
    return sorted(failures)


def main() -> None:
    try:
        report, *test_files = map(Path, sys.argv[1:])
        names = failure_names(report, test_files)
    except (OSError, ValueError, SyntaxError, ElementTree.ParseError):
        names = []
    if not names:
        print("No policy test failure could be identified")
    for name in names:
        print(f"Offline policy test failed {name}")


if __name__ == "__main__":
    main()
