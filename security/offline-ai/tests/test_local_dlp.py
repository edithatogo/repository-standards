import pytest
from security import local_dlp as dlp

def test_fail_closed_without_local_model(monkeypatch, tmp_path):
    dlp._engine.cache_clear()
    monkeypatch.setenv("GLINER_MODEL_DIR", str(tmp_path))
    with pytest.raises(dlp.DLPUnavailable):
        dlp.redact_sensitive_data("CANARY-ABCDEFGH")

def test_deterministic_redaction_with_mock_engine(monkeypatch):
    class Mock:
        def analyze(self, **kwargs): return []
    monkeypatch.setattr(dlp, "_engine", lambda: Mock())
    class Result:
        def __init__(self, **kw): self.start=kw["start"]; self.end=kw["end"]
    class Anonymizer:
        def anonymize(self, text, analyzer_results, operators):
            for match in sorted(analyzer_results, key=lambda v: v.start, reverse=True):
                text=text[:match.start]+"[REDACTED]"+text[match.end:]
            return type("Output", (), {"text": text})()
    # Placeholder packages in tests only, not a substitute for production model checks.
    import sys, types
    analyzer = types.ModuleType("presidio_analyzer")
    analyzer.RecognizerResult = Result
    anonymizer = types.ModuleType("presidio_anonymizer")
    anonymizer.AnonymizerEngine = Anonymizer
    entities = types.ModuleType("presidio_anonymizer.entities")
    entities.OperatorConfig = lambda *a, **kw: None
    monkeypatch.setitem(sys.modules,"presidio_analyzer",analyzer)
    monkeypatch.setitem(sys.modules,"presidio_anonymizer",anonymizer)
    monkeypatch.setitem(sys.modules,"presidio_anonymizer.entities",entities)
    out = dlp.sanitize_context({"input": "jane@example.test CANARY-ABCDEFGH ABC1235 ZBN77VL 2123 4567 01"})
    assert all(secret not in out["input"] for secret in ("jane@example.test", "CANARY-", "ABC1235", "ZBN77VL", "2123 4567 01"))
