"""Fake Live session for testing voice/session loops without connecting to Gemini."""
import asyncio
from dataclasses import dataclass, field
from typing import Any, AsyncIterator


@dataclass
class FakeServerContent:
    """Simulated message from the live model."""

    data: bytes | None = None
    text: str | None = None
    tool_call: Any | None = None
    turn_complete: bool = False
    interrupted: bool = False


class FakeLiveSession:
    """Simulates a live session with in-memory queues."""

    def __init__(self, responses_to_emit: list[Any] | None = None):
        self.sent_realtime_inputs: list[dict] = []
        self.sent_client_contents: list[dict] = []
        self.sent_tool_responses: list[Any] = []
        self._responses_to_emit = responses_to_emit or []
        self._receive_queue: asyncio.Queue = asyncio.Queue()
        self.closed: bool = False

        for resp in self._responses_to_emit:
            self._receive_queue.put_nowait(resp)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.closed = True

    async def send_realtime_input(self, media: dict) -> None:
        """Record realtime audio chunks sent."""
        self.sent_realtime_inputs.append(media)

    async def send_client_content(self, turns: Any, turn_complete: bool = True) -> None:
        """Record client contents sent."""
        self.sent_client_contents.append({"turns": turns, "turn_complete": turn_complete})

    async def send_tool_response(self, function_responses: Any) -> None:
        """Record tool responses sent back to the model."""
        self.sent_tool_responses.append(function_responses)

    def queue_response(self, response: Any) -> None:
        """Enqueue a response for receive() to yield."""
        self._receive_queue.put_nowait(response)

    async def receive(self) -> AsyncIterator[Any]:
        """Yield responses until empty or cancelled."""
        while not self.closed and not self._receive_queue.empty():
            yield await self._receive_queue.get()

    async def close(self) -> None:
        """Close the session."""
        self.closed = True
