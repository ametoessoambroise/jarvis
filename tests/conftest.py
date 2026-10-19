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


@pytest.fixture
def block_network(monkeypatch):
    """Fixture to block network for specific tests."""

    def blocked_socket(*args, **kwargs):
        raise RuntimeError("Network access is blocked in tests")

    monkeypatch.setattr(socket.socket, blocked_socket)
    return monkeypatch


def pytest_collection_modifyitems(config, items):
    """Auto-mark non-integration tests to block network."""
    if not config.getoption("--allow-network"):
        for item in items:
            if "integration" not in item.keywords:
                item.add_marker(pytest.mark.usefixtures("block_network"))
