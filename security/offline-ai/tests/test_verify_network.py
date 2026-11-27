import pytest
from security import verify_network

def test_loopback_only(monkeypatch):
    monkeypatch.setattr(verify_network.socket, "if_nameindex", lambda: [(1, "lo")])
    verify_network.verify_loopback_only()

@pytest.mark.parametrize("interfaces", [[(1,"lo"),(2,"eth0")], [(1,"tun0")], []])
def test_nonisolated_interfaces_rejected(monkeypatch, interfaces):
    monkeypatch.setattr(verify_network.socket, "if_nameindex", lambda: interfaces)
    with pytest.raises(verify_network.NetworkIsolationError):
        verify_network.verify_loopback_only()

def test_namespace_query_failure_rejected(monkeypatch):
    def crash():
        raise OSError("internal detail")
    monkeypatch.setattr(verify_network.socket, "if_nameindex", crash)
    with pytest.raises(verify_network.NetworkIsolationError) as exc:
        verify_network.verify_loopback_only()
    assert "internal detail" not in str(exc.value)
