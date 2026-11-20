"""Fail closed unless the scanner is in a loopback-only network namespace."""
from __future__ import annotations
import socket

class NetworkIsolationError(RuntimeError):
    pass

def verify_loopback_only() -> None:
    try:
        names = {name for _, name in socket.if_nameindex()}
    except OSError:
        raise NetworkIsolationError("Network namespace verification failed") from None
    if not names or names != {"lo"}:
        raise NetworkIsolationError("Scanner is not in a loopback-only network namespace")

if __name__ == "__main__":
    verify_loopback_only()
