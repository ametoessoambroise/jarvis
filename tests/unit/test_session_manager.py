"""Unit tests for SessionManager (P4 / BACKEND_CONTRACT.md C-01 / TRD.md §5.1)."""

import asyncio
from contextlib import asynccontextmanager
import pytest

from core.session_manager import SessionManager
from tests.fakes.fake_ui import FakeUI
from tests.fakes.fake_live_session import FakeLiveSession


class FakeLiveConnector:
    """Simule client.aio.live.connect."""

    def __init__(self, session_to_return=None, exception_to_raise=None):
        self.session_to_return = session_to_return or FakeLiveSession()
        self.exception_to_raise = exception_to_raise
        self.connect_count = 0

    @asynccontextmanager
    async def connect(self, model: str, config: any):
        self.connect_count += 1
        if self.exception_to_raise:
            if callable(self.exception_to_raise):
                raise self.exception_to_raise()
            raise self.exception_to_raise
        yield self.session_to_return


class FakeGenaiClient:
    """Simule le client Google Genai."""

    def __init__(self, connector: FakeLiveConnector):
        class _Aio:
            class _Live:
                def __init__(self, conn):
                    self.connect = conn.connect
            def __init__(self, conn):
                self.live = _Aio._Live(conn)
        self.aio = _Aio(connector)


@pytest.mark.asyncio
async def test_session_manager_fatal_auth_error_no_reconnect():
    """Une erreur d'authentification fatale ne doit PAS déclencher de reconnexion."""
    ui = FakeUI()
    connector = FakeLiveConnector(exception_to_raise=RuntimeError("UNAUTHENTICATED: Invalid API key"))
    client = FakeGenaiClient(connector)

    sm = SessionManager(ui=ui, client=client, max_reconnect=5)
    await sm.run()

    # Doit avoir tenté 1 seule fois
    assert connector.connect_count == 1
    assert ui.current_state == "ERROR"
    assert any("Erreur fatale" in err for err in ui.errors)


@pytest.mark.asyncio
async def test_session_manager_reconnect_bounded():
    """Une erreur réseau transitoire doit reconnecter jusqu'à max_reconnect, puis s'arrêter en ERROR."""
    ui = FakeUI()
    connector = FakeLiveConnector(exception_to_raise=RuntimeError("Connection reset by peer"))
    client = FakeGenaiClient(connector)

    sm = SessionManager(ui=ui, client=client, max_reconnect=3)
    
    # Pour le test, on court-circuite le temps de sommeil
    original_sleep = asyncio.sleep
    async def fast_sleep(s):
        await original_sleep(0.001)

    asyncio.sleep = fast_sleep
    try:
        await sm.run()
    finally:
        asyncio.sleep = original_sleep

    # Doit avoir tenté exactement 3 fois
    assert connector.connect_count == 3
    assert ui.current_state == "ERROR"
    assert any("Impossible de se reconnecter" in err for err in ui.errors)


@pytest.mark.asyncio
async def test_send_text_command_without_session():
    """send_text_command sans session retourne False et prévient l'UI."""
    ui = FakeUI()
    sm = SessionManager(ui=ui)
    res = await sm.send_text_command("Hello")
    assert res is False
    assert any("Pas de connexion active" in log for log in ui.logs)


@pytest.mark.asyncio
async def test_session_shutdown_sets_offline():
    """shutdown() positionne l'état OFFLINE et marque l'arrêt."""
    ui = FakeUI()
    sm = SessionManager(ui=ui)
    await sm.shutdown()
    assert ui.current_state == "OFFLINE"
