"""
Pytest configuration for JARVIS.

Network blocking is enabled by default to prevent accidental API calls.
Integration tests (marked with @pytest.mark.integration) can enable network access.
"""

import socket
import pytest


def pytest_addoption(parser):
    """Add custom command line options."""
    parser.addoption(
        "--allow-network",
        action="store_true",
        default=False,
        help="Allow network access during tests (for integration tests)",
    )


@pytest.fixture(autouse=True)
def block_network(request, monkeypatch):
    """Auto-block network connections for all non-integration tests."""
    if "integration" in request.keywords or request.config.getoption(
        "--allow-network", default=False
    ):
        return

    orig_connect = socket.socket.connect

    def blocked_connect(self, address, *args, **kwargs):
        # Allow internal loopback connections for asyncio Proactor self-pipe on Windows
        if isinstance(address, tuple) and len(address) >= 2:
            host = address[0]
            if host in ("127.0.0.1", "localhost", "::1"):
                return orig_connect(self, address, *args, **kwargs)
        raise RuntimeError("Network access is blocked in tests")

    monkeypatch.setattr(socket.socket, "connect", blocked_connect)

