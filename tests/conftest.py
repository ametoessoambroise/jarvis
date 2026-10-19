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

    def blocked_connect(*args, **kwargs):
        raise RuntimeError("Network access is blocked in tests")

    monkeypatch.setattr(socket.socket, "connect", blocked_connect)
