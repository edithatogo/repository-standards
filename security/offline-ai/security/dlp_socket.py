"""Local-only Unix socket DLP broker. Never binds TCP or logs payloads."""
from __future__ import annotations
import json
import os
import socketserver
import stat
from pathlib import Path
from typing import Any
from .local_dlp import sanitize_context

MAX_REQUEST_BYTES = 1024 * 1024
MAX_RESPONSE_BYTES = 1024 * 1024

def _reject_constant(value: str) -> None:
    raise ValueError("Invalid JSON constant")

def _no_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for key, value in pairs:
        if key in output:
            raise ValueError("Duplicate JSON key")
        output[key] = value
    return output

class DLPRequestHandler(socketserver.StreamRequestHandler):
    """One JSON-line request per connection; fixed value-free failure response."""
    def handle(self) -> None:
        try:
            raw = self.rfile.readline(MAX_REQUEST_BYTES + 1)
            if not raw or len(raw) > MAX_REQUEST_BYTES or not raw.endswith(b"\n"):
                raise ValueError("Request too long or unterminated")
            message = json.loads(raw.decode("utf-8"), parse_constant=_reject_constant,
                                 object_pairs_hook=_no_duplicate_keys)
            if not isinstance(message, dict) or set(message) != {"payload"}:
                raise ValueError("Invalid request envelope")
            result = sanitize_context(message["payload"])
            response = json.dumps({"ok": True, "payload": result}, ensure_ascii=True,
                                  allow_nan=False, separators=(",", ":")).encode() + b"\n"
            if len(response) > MAX_RESPONSE_BYTES:
                raise ValueError("Response too long")
        except Exception:
            response = b'{"ok":false,"error":"DLP_REJECTED"}\n'
        try:
            self.wfile.write(response)
        except OSError:
            pass

class OfflineDLPServer(socketserver.UnixStreamServer):
    allow_reuse_address = False

    def __init__(self, socket_path: Path):
        path = Path(socket_path)
        directory = path.parent
        metadata = directory.stat()
        if (not stat.S_ISDIR(metadata.st_mode) or metadata.st_uid != os.geteuid()
                or metadata.st_mode & 0o077):
            raise PermissionError("DLP socket directory must be privately owned, mode 0700")
        if path.exists() or path.is_symlink():
            raise FileExistsError("DLP socket path already exists")
        old_umask = os.umask(0o077)
        try:
            super().__init__(str(path), DLPRequestHandler)
            os.chmod(path, 0o600)
        finally:
            os.umask(old_umask)
        self.socket_path = path

    def server_close(self):
        super().server_close()
        self.socket_path.unlink(missing_ok=True)

def main():
    path = Path(os.environ.get("DLP_SOCKET_PATH", "/run/offline-dlp/dlp.sock"))
    with OfflineDLPServer(path) as server:
        server.serve_forever(poll_interval=0.2)

if __name__ == "__main__":
    main()
