"""Fake components for testing JARVIS without hardware or network."""
from tests.fakes.fake_live_session import FakeLiveSession
from tests.fakes.fake_clock import FakeClock
from tests.fakes.fake_ui import FakeUI
from tests.fakes.fake_actions import FakeActionRegistry

__all__ = ["FakeLiveSession", "FakeClock", "FakeUI", "FakeActionRegistry"]
