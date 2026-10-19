"""Fake UI implementation for testing without PyQt6."""
from dataclasses import dataclass, field
from typing import Callable, Any


@dataclass
class FakeUI:
    """Mock/Fake implementation of UI interactions."""

    logs: list[str] = field(default_factory=list)
    states: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    current_state: str = "INITIALISING"
    muted: bool = False
    current_file: str | None = None
    on_text_command: Callable[[str], Any] | None = None

    def write_log(self, text: str) -> None:
        """Capture log messages."""
        self.logs.append(text)

    def set_state(self, state: str) -> None:
        """Track state transitions."""
        self.current_state = state
        self.states.append(state)

    def show_error(self, message: str) -> None:
        """Capture error dialog messages."""
        self.errors.append(message)

    def toggle_mute(self) -> bool:
        """Toggle mute state."""
        self.muted = not self.muted
        return self.muted

    def clear(self) -> None:
        """Clear recorded events."""
        self.logs.clear()
        self.states.clear()
        self.errors.clear()
