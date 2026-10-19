"""Deterministic clock for testing time-dependent logic."""
import time
from typing import Callable


class FakeClock:
    """A controllable clock for deterministic tests."""

    def __init__(self, start_time: float = 1700000000.0):
        self._current_time = start_time

    def time(self) -> float:
        """Return the current fake time."""
        return self._current_time

    def advance(self, seconds: float) -> None:
        """Advance the clock by a given number of seconds."""
        if seconds < 0:
            raise ValueError("Cannot move clock backward")
        self._current_time += seconds

    def sleep(self, seconds: float) -> None:
        """Advance time instead of blocking."""
        self.advance(seconds)

    def patch_time(self, monkeypatch) -> None:
        """Monkeypatch the standard time.time with this fake clock."""
        monkeypatch.setattr(time, "time", self.time)
