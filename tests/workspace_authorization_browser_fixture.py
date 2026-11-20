"""Supply synthetic server-side claims to the production workspace adapter."""

from functools import lru_cache
import json
import socket

from pytest import MonkeyPatch


@lru_cache(maxsize=1)
def _configure(identity_file, unexpected_requests):
    from src import dashboard, workspace_authorization

    def claims():
        return json.loads(identity_file.read_text(encoding="utf-8"))

    def loopback_only(connect):
        def wrapped(sock, address):
            if isinstance(address, tuple) and address[0] not in {"127.0.0.1", "::1", "localhost"}:
                with unexpected_requests.open("a", encoding="utf-8") as log:
                    log.write("Unexpected outbound request\n")
                raise AssertionError("Workspace browser checks run offline")
            return connect(sock, address)
        return wrapped

    # The process provides the identity claim, never a browser query or widget.
    # Keep the hooks installed across Streamlit reruns and callbacks.
    patch = MonkeyPatch()
    patch.setattr(workspace_authorization, "trusted_user_claims", claims)
    patch.setattr(socket.socket, "connect", loopback_only(socket.socket.connect))
    patch.setattr(socket.socket, "connect_ex", loopback_only(socket.socket.connect_ex))
    return dashboard.main


def run(identity_file, unexpected_requests):
    _configure(identity_file, unexpected_requests)()
