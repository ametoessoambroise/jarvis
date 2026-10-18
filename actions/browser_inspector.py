"""
Browser Inspector — connects to a Chromium browser via CDP
to extract interactive DOM elements (buttons, inputs, links, etc.).

Requires the browser to be launched with --remote-debugging-port=9222.
Falls back silently if the connection cannot be established.
"""

from __future__ import annotations

import asyncio
from typing import Optional

try:
    from playwright.async_api import async_playwright
    _PLAYWRIGHT = True
except ImportError:
    _PLAYWRIGHT = False


BROWSER_PROCESSES = {"chrome.exe", "msedge.exe", "chromium.exe", "brave.exe"}
CDP_PORT = 9222

_JS_EXTRACT = """
() => {
    const SELS = 'button, input, a, select, textarea, [role="button"], [role="link"]';
    return Array.from(document.querySelectorAll(SELS))
        .filter(el => {
            const r = el.getBoundingClientRect();
            return r.width > 0 && r.height > 0;
        })
        .slice(0, 50)
        .map(el => {
            const r = el.getBoundingClientRect();
            return {
                tag:         el.tagName.toLowerCase(),
                type:        el.type || null,
                name:        (el.innerText || '').trim().slice(0, 80)
                             || el.placeholder || el.name || el.id || el.getAttribute('aria-label') || '',
                x:           Math.round(r.left + r.width  / 2),
                y:           Math.round(r.top  + r.height / 2),
                w:           Math.round(r.width),
                h:           Math.round(r.height),
                is_password: el.type === 'password',
                selector:    el.id ? '#' + el.id
                             : el.className ? '.' + el.className.split(' ')[0]
                             : el.tagName.toLowerCase(),
            };
        });
}
"""


class BrowserInspector:
    """Connect to a Chromium browser via CDP and inspect the active page."""

    def __init__(self):
        self._pw      = None
        self._browser = None
        self._page    = None

    # ── Public helpers ───────────────────────────────────────────────

    @staticmethod
    def is_browser_active(process_name: str) -> bool:
        return process_name.lower() in BROWSER_PROCESSES

    # ── Connection ───────────────────────────────────────────────────

    async def connect(self) -> bool:
        """Try to connect to the browser via CDP.  Returns True on success."""
        if not _PLAYWRIGHT:
            return False
        try:
            if self._pw is None:
                self._pw = await async_playwright().start()
            self._browser = await self._pw.chromium.connect_over_cdp(
                f"http://localhost:{CDP_PORT}",
                timeout=3000,
            )
            contexts = self._browser.contexts
            if contexts and contexts[0].pages:
                self._page = contexts[0].pages[0]
            return self._page is not None
        except Exception as e:
            print(f"[BrowserInspector] CDP connect failed (expected if flag not set): {e}")
            await self.disconnect()
            return False

    async def disconnect(self):
        try:
            if self._browser:
                await self._browser.close()
        except Exception:
            pass
        try:
            if self._pw:
                await self._pw.stop()
        except Exception:
            pass
        self._browser = self._page = self._pw = None

    # ── Element extraction ───────────────────────────────────────────

    async def get_interactive_elements(self) -> list[dict]:
        """Extract interactive DOM elements from the active page."""
        if not self._page:
            connected = await self.connect()
            if not connected:
                return []
        try:
            return await self._page.evaluate(_JS_EXTRACT)
        except Exception as e:
            print(f"[BrowserInspector] ⚠️  DOM extraction failed: {e}")
            return []

    # ── Format for prompt ────────────────────────────────────────────

    @staticmethod
    def to_context_string(elements: list[dict]) -> str:
        if not elements:
            return "[No DOM elements detected]"
        lines = ["=== Browser DOM interactive elements ==="]
        for el in elements:
            pwd = " [PASSWORD]" if el.get("is_password") else ""
            name = el.get("name", "") or "(unnamed)"
            lines.append(
                f"  [{el['tag']}] '{name}'{pwd}"
                f" → ({el['x']}, {el['y']}) sel='{el.get('selector', '')}'"
            )
        return "\n".join(lines)
