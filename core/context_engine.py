"""Context engine for proactive session awareness and environment tracking."""

from __future__ import annotations

from collections import deque
from datetime import datetime, timedelta
from typing import Deque


class ContextEngine:
    """Tracks recent context events, window titles, and proactive suggestions."""

    def __init__(self, max_entries: int = 20):
        self.history: Deque[str] = deque(maxlen=max_entries)
        self._suggestion_cooldown = timedelta(seconds=300)  # default 5 minutes cooldown
        self._last_suggestion: str | None = None
        self._last_suggestion_ts: datetime = datetime.min

    def record_context(self, context_text: str) -> None:
        """Record a new context entry from active window title or other environment cues."""
        if context_text is None:
            context_text = ""

        context_text = context_text.strip()
        if not context_text:
            return

        if self.history and self.history[-1].lower() == context_text.lower():
            return

        self.history.append(context_text)

    def get_recent_context(self, limit: int = 5) -> list[str]:
        """Return the most recent context entries."""
        return list(self.history)[-limit:]

    def summarize_context(self) -> str:
        """Generate a compact summary of current context for prompt injection."""
        if not self.history:
            return "No recent context available."

        lines = ["Recent workspace context:"]
        for idx, entry in enumerate(self.get_recent_context(), start=1):
            lines.append(f"{idx}. {entry}")
        return "\n".join(lines)

    def get_context_payload(self) -> dict[str, str]:
        """Return structured context that other systems can consume."""
        return {
            "recent_context": self.summarize_context(),
            "last_entry": self.history[-1] if self.history else "",
        }

    def generate_suggestion(self) -> str | None:
        """Create a simple, privacy-preserving suggestion string based on recent context.

        This is intentionally lightweight: it never sends raw sensitive data, just
        concise hints like "open app X" or "play music" based on window titles.
        """
        if not self.history:
            return None

        recent = list(self.history)[-3:]
        last = recent[-1]
        if not last:
            return None

        low = last.lower()
        candidate: str | None = None

        if any(k in low for k in ("youtube", "spotify", "music", "video")):
            candidate = "It looks like you're watching or listening to media. Would you like me to open a playlist or play music for you?"
        elif any(k in low for k in ("mail", "outlook", "gmail", "inbox")):
            candidate = "I see your email client is active. Shall I check for important unread messages?"
        elif any(k in low for k in ("word", "excel", "powerpoint", "docs", "sheets")):
            candidate = "You're working on documents. Want me to create a quick outline or save a backup?"
        elif len(set(recent)) >= 2:
            joined = ", ".join(x for x in recent if x)
            candidate = f"Recent activity includes: {joined}. Do you want me to assist with any of these?"

        if not candidate:
            return None

        # Avoid repeating the same suggestion within the cooldown window
        now = datetime.now()
        if (
            candidate == self._last_suggestion
            and (now - self._last_suggestion_ts) < self._suggestion_cooldown
        ):
            return None
        self._last_suggestion = candidate
        self._last_suggestion_ts = now
        return candidate
