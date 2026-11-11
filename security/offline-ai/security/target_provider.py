"""Promptfoo provider for an explicitly selected local agent integration."""
from __future__ import annotations
import importlib.util
import os
from pathlib import Path

def call_api(prompt: str, options: dict | None = None, context: dict | None = None) -> dict[str, str]:
    """Invoke only a Python adapter inside an approved checkout root.

    The runner must supply the actual credential-free, read-only, network-disabled
    sandbox. This path check alone is not an execution sandbox.
    """
    try:
        root = Path(os.environ.get("SECURITY_AGENT_WORKSPACE", "/work")).resolve(strict=True)
        configured = os.environ.get("SECURITY_AGENT_ADAPTER", "")
        if not configured:
            raise ValueError("Missing adapter")
        path = Path(configured)
        if not path.is_absolute() or path.is_symlink():
            raise ValueError("Invalid adapter path")
        path = path.resolve(strict=True)
        if not path.is_relative_to(root) or not path.is_file() or path.suffix != ".py":
            raise ValueError("Adapter outside authorized checkout")
        spec = importlib.util.spec_from_file_location("_offline_security_agent_adapter", path)
        if spec is None or spec.loader is None:
            raise ValueError("Invalid adapter")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        handler = getattr(module, "respond", None)
        if not callable(handler):
            raise ValueError("No respond function")
        result = handler(prompt, (context or {}).get("vars", {}))
        if not isinstance(result, str):
            raise ValueError("Invalid result")
        return {"output": result}
    except Exception:
        return {"error": "Local agent evaluation unavailable"}
