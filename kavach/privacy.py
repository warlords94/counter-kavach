"""Identifier masking and the offline network guard."""
import os
import re
import socket

# --- masking -----------------------------------------------------------------

_AADHAAR = re.compile(r"(?<!\d)(\d{4})[ -]?(\d{4})[ -]?(\d{4})(?!\d)")
_PAN = re.compile(r"\b[A-Za-z]{5}\d{4}[A-Za-z]\b")
_ACCOUNT = re.compile(r"(?<![\dX])\d{9,18}(?!\d)")
_PHONE = re.compile(r"(?<!\d)(?:\+?91[ -]?)?[6-9]\d{9}(?!\d)")
_UPI = re.compile(r"\b[\w.\-]{2,}@[a-z][a-z0-9]+\b", re.IGNORECASE)


def _keep_last4(s: str) -> str:
    return "X" * (len(s) - 4) + s[-4:]


def mask_ids(text: str) -> str:
    """Aadhaar and PAN: always masked, whoever they belong to."""
    text = _AADHAAR.sub(lambda m: f"XXXX XXXX {m.group(3)}", text)
    return _PAN.sub(lambda m: _keep_last4(m.group(0)), text)


def mask_customer(text: str) -> str:
    return _ACCOUNT.sub(lambda m: _keep_last4(m.group(0)), mask_ids(text))


def mask_suspect(text: str, suspected_fraud: bool) -> str:
    """Payee account / UPI ID / caller numbers stay in full only for suspected-fraud complaints."""
    if suspected_fraud:
        return text
    text = _PHONE.sub(lambda m: _keep_last4(re.sub(r"\D", "", m.group(0))), text)
    text = _UPI.sub(lambda m: "XXXX@" + m.group(0).split("@", 1)[1], text)
    return _ACCOUNT.sub(lambda m: _keep_last4(m.group(0)), text)


def mask_free_text(text: str, suspected_fraud: bool) -> str:
    return mask_suspect(mask_ids(text), suspected_fraud)


# --- offline guard -------------------------------------------------------------


class NetworkBlockedError(OSError):
    pass


_ORIGINAL = {
    "getaddrinfo": socket.getaddrinfo,
    "create_connection": socket.create_connection,
    "connect": socket.socket.connect,
    "connect_ex": socket.socket.connect_ex,
}
_LOCAL = {"localhost", "localhost.localdomain", "::1", "0.0.0.0", "::", ""}
_active = False


def _is_local(host) -> bool:
    if host is None:
        return True
    if isinstance(host, bytes):
        host = host.decode(errors="ignore")
    h = str(host).lower().strip("[]")
    return h in _LOCAL or h.startswith("127.")


def _check(host) -> None:
    if not _is_local(host):
        raise NetworkBlockedError(f"Offline mode: blocked network access to {host!r}")


def _getaddrinfo(host, *args, **kwargs):
    _check(host)
    return _ORIGINAL["getaddrinfo"](host, *args, **kwargs)


def _create_connection(address, *args, **kwargs):
    _check(address[0])
    return _ORIGINAL["create_connection"](address, *args, **kwargs)


def _connect(self, address):
    if isinstance(address, tuple):
        _check(address[0])
    return _ORIGINAL["connect"](self, address)


def _connect_ex(self, address):
    if isinstance(address, tuple):
        _check(address[0])
    return _ORIGINAL["connect_ex"](self, address)


def install_offline_guard() -> None:
    global _active
    for var in ("HF_HUB_OFFLINE", "TRANSFORMERS_OFFLINE", "HF_DATASETS_OFFLINE"):
        os.environ[var] = "1"
    socket.getaddrinfo = _getaddrinfo
    socket.create_connection = _create_connection
    socket.socket.connect = _connect
    socket.socket.connect_ex = _connect_ex
    _active = True


def uninstall_offline_guard() -> None:
    global _active
    socket.getaddrinfo = _ORIGINAL["getaddrinfo"]
    socket.create_connection = _ORIGINAL["create_connection"]
    for name in ("connect", "connect_ex"):
        if name in socket.socket.__dict__:
            delattr(socket.socket, name)
    _active = False


def install_from_env() -> bool:
    if os.environ.get("OFFLINE", "0") == "1":
        install_offline_guard()
    return _active


def offline_guard_active() -> bool:
    return _active
