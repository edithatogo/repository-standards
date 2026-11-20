import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "detect_ai.sh"

@pytest.fixture
def repository(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    return tmp_path

def detect(repo):
    result = subprocess.run(["bash", str(SCRIPT)], cwd=repo, capture_output=True, text=True)
    return result.returncode, result.stdout, result.stderr

def test_docs_only_not_ai(repository):
    (repository / "README.md").write_text("Plain research notes\n")
    subprocess.run(["git", "add", "."], cwd=repository, check=True)
    assert detect(repository)[:2] == (1, "")

def test_agent_import_under_generic_name(repository):
    (repository / "worker.py").write_text("from langchain_core.messages import HumanMessage\n")
    subprocess.run(["git", "add", "."], cwd=repository, check=True)
    assert detect(repository)[:2] == (0, "")

def test_agent_source_filename(repository):
    (repository / "my_agent.py").write_text("pass\n")
    subprocess.run(["git", "add", "."], cwd=repository, check=True)
    assert detect(repository)[:2] == (0, "")

def test_untracked_code_not_scanned(repository):
    (repository / "worker.py").write_text("import langchain\n")
    assert detect(repository)[:2] == (1, "")

def test_no_sensitive_content_in_output(repository):
    (repository / "worker.py").write_text("from langchain_core.messages import HumanMessage\nCANARY-ABCDEFGH\n")
    subprocess.run(["git", "add", "."], cwd=repository, check=True)
    code, out, err = detect(repository)
    assert code == 0
    assert "CANARY-" not in (out + err)

def test_invalid_repository_is_inspection_failure(tmp_path):
    result = subprocess.run(["bash", str(SCRIPT)], cwd=tmp_path, capture_output=True, text=True)
    assert result.returncode == 2
