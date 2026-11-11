"""Real offline detector smoke test; intentionally no mocked dependencies.

Requires the pre-provisioned model, Presidio, GLiNER and Anonymizer in the
isolated scanner image. Fails CI if any required component is absent.
"""
from __future__ import annotations
import os
from pathlib import Path

from security.local_dlp import DLPUnavailable, redact_sensitive_data, sanitize_context

def test_real_model_is_locally_available():
    root = Path(os.environ.get("GLINER_MODEL_DIR", "/opt/models/gliner-pii"))
    assert (root / "config.json").is_file(), "GLiNER model missing from offline image"
    from gliner import GLiNER  # noqa: F401
    from presidio_analyzer import AnalyzerEngine  # noqa: F401
    from presidio_anonymizer import AnonymizerEngine  # noqa: F401

def test_real_stack_redacts_email_canary_and_nested_tool_response():
    synthetic = {
        "rag_chunk": "Contact jane@example.test.",
        "mcp_result": {"body": "CANARY-A1B2C3D4"},
    }
    clean = sanitize_context(synthetic)
    assert "jane@example.test" not in clean["rag_chunk"]
    assert "CANARY-A1B2C3D4" not in clean["mcp_result"]["body"]
    assert "[REDACTED]" in clean["rag_chunk"]
    assert "[REDACTED]" in clean["mcp_result"]["body"]

def test_real_detector_does_not_silently_return_raw_when_error(monkeypatch):
    from security import local_dlp
    def broken(*args, **kwargs):
        raise RuntimeError("synthetic engine fault")
    monkeypatch.setattr(local_dlp, "_engine", broken)
    import pytest
    with pytest.raises(DLPUnavailable):
        redact_sensitive_data("CANARY-A1B2C3D4")
