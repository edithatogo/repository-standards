"""Explicit fail-closed agent ingress, tool output and egress boundaries.

Not automatic instrumentation. Callers must route each relevant boundary here.
"""
from __future__ import annotations
from collections.abc import Callable
from typing import Any, TypeVar
from .local_dlp import DLPUnavailable, sanitize_context

T = TypeVar("T")

def guarded_invoke(sink: Callable[[Any], T], payload: Any) -> T:
    """Never invoke an external sink if incoming DLP fails."""
    if not callable(sink):
        raise TypeError("sink must be callable")
    try:
        clean = sanitize_context(payload)
    except Exception:
        raise DLPUnavailable("DLP boundary failed closed") from None
    return sink(clean)

def guarded_transform(transform: Callable[[Any], Any], payload: Any) -> Any:
    """Sanitize input and output; suppress exception messages from unsafe transforms."""
    if not callable(transform):
        raise TypeError("transform must be callable")
    try:
        clean = sanitize_context(payload)
    except Exception:
        raise DLPUnavailable("DLP ingress failed closed") from None
    try:
        result = transform(clean)
    except Exception:
        raise DLPUnavailable("Guarded transform failed") from None
    try:
        return sanitize_context(result)
    except Exception:
        raise DLPUnavailable("DLP egress failed closed") from None
