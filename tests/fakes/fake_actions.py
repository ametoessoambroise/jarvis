"""Fake actions registry for testing tool dispatch without side effects."""
from typing import Callable, Any


class FakeActionRegistry:
    """Provides fake handlers for tool execution tests."""

    def __init__(self):
        self._handlers: dict[str, Callable[[dict], Any]] = {}
        self.calls: list[tuple[str, dict]] = []

    def register(self, name: str, handler: Callable[[dict], Any]) -> None:
        """Register a fake action handler."""
        self._handlers[name] = handler

    def execute(self, name: str, parameters: dict) -> Any:
        """Execute a registered fake action and record the call."""
        self.calls.append((name, parameters))
        if name not in self._handlers:
            return f"Fake action '{name}' executed with {parameters}"
        return self._handlers[name](parameters)

    def register_constant(self, name: str, result: Any) -> None:
        """Register a fake action that returns a constant."""
        self.register(name, lambda _: result)

    def register_error(self, name: str, error: Exception) -> None:
        """Register a fake action that raises an exception."""
        def _err(_):
            raise error
        self.register(name, _err)

    def clear(self) -> None:
        """Clear registered handlers and recorded calls."""
        self._handlers.clear()
        self.calls.clear()
