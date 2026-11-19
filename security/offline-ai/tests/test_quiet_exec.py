import sys
from security.quiet_exec import run
from scripts.summarize_policy_test_failures import failure_names

def test_success_is_silent(capsys):
    assert run("pytest", [sys.executable, "-c", 'print("CANARY-SECRET123")']) == 0
    output = capsys.readouterr()
    assert not (output.out or output.err)

def test_failure_is_value_free(capsys):
    command = [sys.executable, "-c", 'import sys; print("CANARY-SECRET123"); sys.exit(9)']
    assert run("opengrep", command) == 2
    output = capsys.readouterr()
    assert "CANARY-" not in output.err
    assert "opengrep" in output.err
    assert not output.out

def test_unavailable_command_fails_closed(capsys):
    assert run("gitleaks-history", ["/path/does/not/exist"]) == 2
    assert "Security control failed" in capsys.readouterr().err

def test_unknown_label_fails_closed(capsys):
    assert run("arbitrary-user-data", [sys.executable, "-c", 'print("bad")']) == 2
    assert "bad" not in capsys.readouterr().err


def test_policy_failure_summary_keeps_only_known_test_names(tmp_path):
    test_file = tmp_path / "test_runtime.py"
    test_file.write_text("def test_known():\n    pass\n", encoding="utf-8")
    report = tmp_path / "report.xml"
    report.write_text(
        """<testsuites><testsuite>
        <testcase classname="trusted.test_runtime" name="test_known[private-parameter]">
          <failure message="hidden details">private traceback</failure>
        </testcase>
        <testcase classname="unknown.module" name="public-looking-name"><error/></testcase>
        </testsuite></testsuites>""",
        encoding="utf-8",
    )
    assert failure_names(report, [test_file], tmp_path) == ["test_runtime.test_known"]
