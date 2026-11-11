import json
import socket
import threading
import pytest
from security import dlp_socket

def ask(path, message: bytes) -> dict:
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
        client.settimeout(2)
        client.connect(str(path))
        client.sendall(message)
        result = b""
        while not result.endswith(b"\n"):
            result += client.recv(1024)
        return json.loads(result)

@pytest.fixture
def broker(monkeypatch, tmp_path):
    monkeypatch.setattr(dlp_socket, "sanitize_context",
                        lambda x: "[REDACTED]" if isinstance(x, str) else x)
    path = tmp_path / "dlp.sock"
    server = dlp_socket.OfflineDLPServer(path)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield path
    server.shutdown()
    server.server_close()
    thread.join(timeout=3)

def test_reply_contains_only_sanitized_content(broker):
    assert ask(broker, b'{"payload":"CANARY-ABCDEFGH"}\n') == {"ok": True, "payload": "[REDACTED]"}

def test_duplicate_keys_fail_closed(broker):
    assert ask(broker, b'{"payload":"secret","payload":"safe"}\n') == {"ok": False, "error": "DLP_REJECTED"}

def test_invalid_constants_fail_closed(broker):
    assert ask(broker, b'{"payload":NaN}\n')["ok"] is False

def test_error_does_not_reveal_raw_value(monkeypatch, broker):
    def failure(value):
        raise RuntimeError("CANARY-ABCDEFGH")
    monkeypatch.setattr(dlp_socket, "sanitize_context", failure)
    assert ask(broker, b'{"payload":"CANARY-ABCDEFGH"}\n') == {"ok": False, "error": "DLP_REJECTED"}

def test_oversized_request_fails_closed(broker):
    payload = b'{"payload":"' + b"x" * dlp_socket.MAX_REQUEST_BYTES + b'"}\n'
    assert ask(broker, payload) == {"ok": False, "error": "DLP_REJECTED"}

def test_socket_removed_on_shutdown(tmp_path):
    path = tmp_path / "test.sock"
    server = dlp_socket.OfflineDLPServer(path)
    assert path.exists()
    assert path.stat().st_mode & 0o777 == 0o600
    server.server_close()
    assert not path.exists()

def test_refuses_world_readable_directory(tmp_path):
    root = tmp_path / "public"
    root.mkdir(mode=0o755)
    with pytest.raises(PermissionError):
        dlp_socket.OfflineDLPServer(root / "dlp.sock")
