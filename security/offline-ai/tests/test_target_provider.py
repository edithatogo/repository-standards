from security import target_provider

def test_no_adapter_fails_closed(monkeypatch, tmp_path):
    monkeypatch.setenv("SECURITY_AGENT_WORKSPACE", str(tmp_path))
    monkeypatch.delenv("SECURITY_AGENT_ADAPTER", raising=False)
    assert target_provider.call_api("hi") == {"error": "Local agent evaluation unavailable"}

def test_inside_workspace_executes(monkeypatch, tmp_path):
    adapter = tmp_path / "adapter.py"
    adapter.write_text('def respond(prompt, vars):\n    return "SAFE:" + prompt\n')
    monkeypatch.setenv("SECURITY_AGENT_WORKSPACE", str(tmp_path))
    monkeypatch.setenv("SECURITY_AGENT_ADAPTER", str(adapter))
    assert target_provider.call_api("hi", {}, {"vars": {}}) == {"output": "SAFE:hi"}

def test_outside_workspace_rejected(monkeypatch, tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    outside = tmp_path / "outside.py"
    outside.write_text('def respond(prompt, vars): return "bad"\n')
    monkeypatch.setenv("SECURITY_AGENT_WORKSPACE", str(root))
    monkeypatch.setenv("SECURITY_AGENT_ADAPTER", str(outside))
    assert "error" in target_provider.call_api("hi")

def test_symlink_rejected(monkeypatch, tmp_path):
    adapter = tmp_path / "adapter.py"
    adapter.write_text('def respond(prompt, vars): return "bad"\n')
    link = tmp_path / "link.py"
    link.symlink_to(adapter)
    monkeypatch.setenv("SECURITY_AGENT_WORKSPACE", str(tmp_path))
    monkeypatch.setenv("SECURITY_AGENT_ADAPTER", str(link))
    assert "error" in target_provider.call_api("hi")

def test_exception_message_not_exposed(monkeypatch, tmp_path):
    adapter = tmp_path / "adapter.py"
    adapter.write_text('def respond(prompt, vars): raise RuntimeError("CANARY-ABCDEFGH")\n')
    monkeypatch.setenv("SECURITY_AGENT_WORKSPACE", str(tmp_path))
    monkeypatch.setenv("SECURITY_AGENT_ADAPTER", str(adapter))
    assert target_provider.call_api("hi") == {"error": "Local agent evaluation unavailable"}
