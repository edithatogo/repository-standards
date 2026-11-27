"""Real Python Unix socket broker + Node client contract tests (synthetic DLP stub)."""
import json
import os
import subprocess
import threading
from pathlib import Path
import pytest
from security import dlp_socket

NODE_CLIENT = Path(__file__).resolve().parents[1] / "clients/node/dlp-client.mjs"

@pytest.fixture
def broker(monkeypatch, tmp_path):
    monkeypatch.setattr(dlp_socket, "sanitize_context",
                        lambda x: x.replace("SECRET", "[REDACTED]"))
    sock = tmp_path / "dlp.sock"
    server = dlp_socket.OfflineDLPServer(sock)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    yield sock
    server.shutdown()
    server.server_close()
    worker.join(timeout=3)

def invoke_node(socket_path: Path, value: str):
    source = """const {sanitizeViaSocket}=await import(process.env.DLP_CLIENT);
    try { const v=await sanitizeViaSocket(process.env.DLP_VALUE,{socketPath:process.env.DLP_SOCKET});
      process.stdout.write(JSON.stringify({ok:true,result:v})); }
    catch { process.stdout.write(JSON.stringify({ok:false,error:'DLP_REJECTED'})); }"""
    result = subprocess.run(["node", "--input-type=module", "-e", source],
        env={**os.environ, "DLP_CLIENT": NODE_CLIENT.as_uri(),
             "DLP_SOCKET": str(socket_path), "DLP_VALUE": value},
        capture_output=True, text=True, timeout=10, check=True)
    return json.loads(result.stdout)

def test_python_broker_to_node_client(broker):
    assert invoke_node(broker, "SECRET") == {"ok": True, "result": "[REDACTED]"}

def test_python_broker_rejection_to_node_client(broker, monkeypatch):
    def bad(_):
        raise RuntimeError("CANARY-SECRET123")
    monkeypatch.setattr(dlp_socket, "sanitize_context", bad)
    assert invoke_node(broker, "SECRET") == {"ok": False, "error": "DLP_REJECTED"}
