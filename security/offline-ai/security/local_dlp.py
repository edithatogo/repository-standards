"""Fail-closed local Presidio + GLiNER redaction. No remote inference."""
from __future__ import annotations
import os
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

class DLPUnavailable(RuntimeError):
    pass

CANARY = re.compile(r"CANARY-[A-Z0-9]{6,}")
EMAIL = re.compile(r"(?<![\w.])[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}")
PHONE = re.compile(r"(?<!\d)(?:\+61[ -]?|0)[23478](?:[ -]?\d){8}(?!\d)")

@lru_cache(maxsize=1)
def _engine():
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    model_path = Path(os.environ.get("GLINER_MODEL_DIR", "/opt/models/gliner-pii"))
    if not (model_path / "config.json").is_file():
        raise DLPUnavailable("Required local GLiNER model is unavailable")
    try:
        from gliner import GLiNER
        from presidio_analyzer import AnalyzerEngine, EntityRecognizer, RecognizerRegistry, RecognizerResult
        from presidio_analyzer.nlp_engine import NlpEngine
        class EmptyNlp(NlpEngine):
            engine_name = "offline"
            def load(self): pass
            def is_loaded(self): return True
            def get_supported_languages(self): return ["en"]
            def get_supported_entities(self): return []
            def process_text(self, text, language): return None
            def process_batch(self, texts, language, **kw):
                for item in texts: yield (item, None)
            def is_stopword(self, word, language): return False
            def is_punct(self, word, language): return False
        class LocalRecognizer(EntityRecognizer):
            def __init__(self):
                super().__init__(supported_entities=["PERSON", "LOCATION", "MEDICAL_CONDITION", "ID_NUMBER"], supported_language="en", name="local_gliner")
                self.model = GLiNER.from_pretrained(str(model_path))
            def load(self): pass
            def analyze(self, text, entities, nlp_artifacts=None):
                names = {"person": "PERSON", "location": "LOCATION", "medical condition": "MEDICAL_CONDITION", "identification number": "ID_NUMBER"}
                return [RecognizerResult(entity_type=names[p["label"]], start=p["start"], end=p["end"], score=p.get("score", 0.5)) for p in self.model.predict_entities(text, list(names), threshold=0.25) if p["label"] in names and names[p["label"]] in entities]
        registry = RecognizerRegistry(supported_languages=["en"])
        registry.add_recognizer(LocalRecognizer())
        return AnalyzerEngine(registry=registry, nlp_engine=EmptyNlp(), supported_languages=["en"])
    except Exception as error:
        raise DLPUnavailable("Local analyzer initialization failed") from error

def redact_sensitive_data(value: str) -> str:
    if not isinstance(value, str):
        raise TypeError("Expected string")
    spans = [(m.start(), m.end()) for rule in (CANARY, EMAIL, PHONE) for m in rule.finditer(value)]
    try:
        for result in _engine().analyze(text=value, language="en", score_threshold=0.25):
            spans.append((result.start, result.end))
        from presidio_anonymizer import AnonymizerEngine
        from presidio_analyzer import RecognizerResult
        from presidio_anonymizer.entities import OperatorConfig
        merged = []
        for a, b in sorted(spans):
            if not 0 <= a < b <= len(value): raise DLPUnavailable("Invalid offsets")
            if merged and a <= merged[-1][1]: merged[-1][1] = max(merged[-1][1], b)
            else: merged.append([a,b])
        if not merged: return value
        matches = [RecognizerResult(entity_type="SENSITIVE", start=a, end=b, score=1.0) for a,b in merged]
        return AnonymizerEngine().anonymize(text=value, analyzer_results=matches, operators={"DEFAULT": OperatorConfig("replace", {"new_value": "[REDACTED]"})}).text
    except Exception as error:
        raise DLPUnavailable("Local DLP operation failed closed") from error

def sanitize_context(value: Any) -> Any:
    if isinstance(value, str): return redact_sensitive_data(value)
    if isinstance(value, list): return [sanitize_context(x) for x in value]
    if isinstance(value, tuple): return tuple(sanitize_context(x) for x in value)
    if isinstance(value, dict):
        result = {}
        for k, v in value.items():
            clean_k = redact_sensitive_data(k) if isinstance(k, str) else k
            if clean_k in result: raise DLPUnavailable("Redacted-key collision")
            result[clean_k] = sanitize_context(v)
        return result
    if value is None or isinstance(value, (bool,int,float)): return value
    raise DLPUnavailable("Unsupported object at DLP boundary")
