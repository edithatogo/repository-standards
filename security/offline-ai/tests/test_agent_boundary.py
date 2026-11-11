import pytest
from security import agent_boundary as boundary
from security.local_dlp import DLPUnavailable

def test_never_invokes_sink_when_sanitizer_fails(monkeypatch):
    invoked = []
    def broken(payload):
        raise RuntimeError("CANARY-SECRET123")
    monkeypatch.setattr(boundary, "sanitize_context", broken)
    with pytest.raises(DLPUnavailable, match="failed closed") as exc:
        boundary.guarded_invoke(invoked.append, {"tool": "CANARY-SECRET123"})
    assert not invoked
    assert "CANARY-" not in str(exc.value)

def test_sends_only_sanitized_payload(monkeypatch):
    monkeypatch.setattr(boundary, "sanitize_context", lambda x: {"message": "[REDACTED]"})
    observed = []
    boundary.guarded_invoke(observed.append, {"message": "CANARY-SECRET123"})
    assert observed == [{"message": "[REDACTED]"}]

def test_double_boundary_redacts_transform_output(monkeypatch):
    calls = []
    def sanitize(x):
        calls.append(x)
        return x.replace("SECRET", "[REDACTED]")
    monkeypatch.setattr(boundary, "sanitize_context", sanitize)
    value = boundary.guarded_transform(lambda safe: safe + " SECRET", "SECRET")
    assert value == "[REDACTED] [REDACTED]"
    assert calls == ["SECRET", "[REDACTED] SECRET"]

def test_sink_errors_are_normalized(monkeypatch):
    monkeypatch.setattr(boundary, "sanitize_context", lambda x: x)
    with pytest.raises(DLPUnavailable, match="Guarded sink failed"):
        boundary.guarded_invoke(lambda x: (_ for _ in ()).throw(ValueError("unavailable")), "safe")

def test_transform_error_text_not_exposed(monkeypatch):
    monkeypatch.setattr(boundary, "sanitize_context", lambda x: x)
    def fail(_):
        raise RuntimeError("CANARY-SECRET123")
    with pytest.raises(DLPUnavailable, match="Guarded transform failed") as exc:
        boundary.guarded_transform(fail, "safe")
    assert "CANARY-" not in str(exc.value)

def test_sink_result_is_sanitized(monkeypatch):
    monkeypatch.setattr(boundary, "sanitize_context", lambda x: x.replace("SECRET", "[REDACTED]"))
    result = boundary.guarded_invoke(lambda _: "SECRET", "safe")
    assert result == "[REDACTED]"

def test_sink_exception_is_normalized(monkeypatch):
    monkeypatch.setattr(boundary, "sanitize_context", lambda x: x)
    def fail(_):
        raise RuntimeError("CANARY-SECRET123")
    with pytest.raises(DLPUnavailable) as exc:
        boundary.guarded_invoke(fail, "safe")
    assert "CANARY-" not in str(exc.value)
