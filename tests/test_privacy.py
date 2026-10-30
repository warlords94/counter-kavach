import socket

import pytest

from kavach import privacy


def test_mask_aadhaar_keeps_last_four():
    assert privacy.mask_customer("Aadhaar 1234 5678 9012") == "Aadhaar XXXX XXXX 9012"


def test_mask_account_number_keeps_last_four():
    assert privacy.mask_customer("A/c 123456789012345") == "A/c XXXXXXXXXXX2345"


def test_mask_pan_keeps_last_four():
    assert privacy.mask_customer("PAN ABCDE1234F") == "PAN XXXXXX234F"


def test_suspect_identifiers_masked_unless_suspected_fraud():
    text = "caller +91 9876543210 gave UPI fraud.boss@okaxis"
    masked = privacy.mask_suspect(text, suspected_fraud=False)
    assert "9876543210" not in masked and "fraud.boss" not in masked
    assert privacy.mask_suspect(text, suspected_fraud=True) == text


@pytest.fixture
def guard():
    privacy.install_offline_guard()
    yield
    privacy.uninstall_offline_guard()


def test_outbound_connection_blocked_by_ip(guard):
    with pytest.raises(privacy.NetworkBlockedError):
        socket.create_connection(("93.184.216.34", 80), timeout=2)


def test_dns_lookup_blocked(guard):
    with pytest.raises(privacy.NetworkBlockedError):
        socket.getaddrinfo("example.com", 443)


def test_localhost_still_allowed(guard):
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(("127.0.0.1", 0))
    server.listen(1)
    port = server.getsockname()[1]
    client = socket.create_connection(("127.0.0.1", port), timeout=2)
    client.close()
    server.close()


def test_guard_state_reported(guard):
    assert privacy.offline_guard_active()


def test_uninstall_restores_socket():
    privacy.install_offline_guard()
    privacy.uninstall_offline_guard()
    assert not privacy.offline_guard_active()
    assert socket.getaddrinfo is privacy._ORIGINAL["getaddrinfo"]
