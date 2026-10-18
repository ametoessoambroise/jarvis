"""
UI Inspector — extracts the accessibility tree of the active window.
Uses pywinauto's UIA backend to list interactive controls with precise coordinates.
"""

from __future__ import annotations

import threading
from typing import Optional

try:
    import win32gui
    import win32process
    _WIN32 = True
except ImportError:
    _WIN32 = False

try:
    import psutil
    _PSUTIL = True
except ImportError:
    _PSUTIL = False

try:
    from pywinauto import Desktop
    _PYWINAUTO = True
except ImportError:
    _PYWINAUTO = False


INTERACTIVE_TYPES = {
    "Button", "Edit", "CheckBox", "Hyperlink",
    "ComboBox", "MenuItem", "TabItem", "ListItem",
}
MAX_ELEMENTS = 50

_lock = threading.Lock()


class UIInspector:
    """Extracts interactive UI elements from the active foreground window."""

    # ── Active window info ───────────────────────────────────────────

    def get_active_window_info(self) -> dict:
        """Return title and process name of the foreground window."""
        if not _WIN32:
            return {"title": "", "process": "", "hwnd": 0}

        try:
            hwnd  = win32gui.GetForegroundWindow()
            title = win32gui.GetWindowText(hwnd)
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            proc_name = ""
            if _PSUTIL:
                try:
                    proc_name = psutil.Process(pid).name()
                except Exception:
                    pass
            return {"title": title, "process": proc_name, "hwnd": hwnd}
        except Exception as e:
            print(f"[UIInspector] ⚠️  get_active_window_info: {e}")
            return {"title": "", "process": "", "hwnd": 0}

    # ── Element extraction ───────────────────────────────────────────

    def get_active_window_elements(self) -> list[dict]:
        """Extract interactive controls from the active window via UIA."""
        if not _PYWINAUTO:
            return []

        with _lock:
            try:
                desktop = Desktop(backend="uia")
                window  = desktop.active()
                elements: list[dict] = []

                for ctrl in window.descendants():
                    ctype = ctrl.element_info.control_type
                    if ctype not in INTERACTIVE_TYPES:
                        continue

                    rect = ctrl.rectangle()
                    if rect.width() == 0 or rect.height() == 0:
                        continue

                    cx = (rect.left + rect.right)  // 2
                    cy = (rect.top  + rect.bottom) // 2

                    elements.append({
                        "type":        ctype,
                        "name":        ctrl.element_info.name or "",
                        "x":           cx,
                        "y":           cy,
                        "w":           rect.width(),
                        "h":           rect.height(),
                        "is_password": self._is_password_field(ctrl),
                        "enabled":     ctrl.element_info.enabled,
                    })

                    if len(elements) >= MAX_ELEMENTS:
                        break

                return elements

            except Exception as e:
                print(f"[UIInspector] ⚠️  extraction error: {e}")
                return []

    # ── Helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _is_password_field(ctrl) -> bool:
        """Detect if an Edit control is a password field."""
        try:
            vp = ctrl.get_value()
            if vp and all(c == "●" or c == "•" or c == "*" for c in vp):
                return True
        except Exception:
            pass
        try:
            name = (ctrl.element_info.name or "").lower()
            if "password" in name or "mot de passe" in name:
                return True
        except Exception:
            pass
        return False

    def to_context_string(self, elements: list[dict]) -> str:
        """Format elements into a condensed text block for prompt injection."""
        if not elements:
            return "[No interactive elements detected]"

        lines = ["=== Interactive elements on active window ==="]
        for i, el in enumerate(elements):
            state = "✓" if el.get("enabled", True) else "✗"
            pwd   = " [PASSWORD]" if el.get("is_password") else ""
            name  = el.get("name", "") or "(unnamed)"
            lines.append(
                f"  [{state}] #{i} {el['type']} '{name}'{pwd}"
                f" → ({el['x']}, {el['y']})"
            )
        return "\n".join(lines)

    def find_element(
        self,
        elements: list[dict],
        target: str,
    ) -> Optional[dict]:
        """Find the best matching element by name (fuzzy)."""
        if not target or not elements:
            return None

        target_lower = target.lower().strip()

        # 1. Exact match
        for el in elements:
            if (el.get("name") or "").lower() == target_lower:
                return el

        # 2. Substring match
        for el in elements:
            if target_lower in (el.get("name") or "").lower():
                return el

        # 3. Any word match
        words = target_lower.split()
        for el in elements:
            name_lower = (el.get("name") or "").lower()
            if any(w in name_lower for w in words):
                return el

        return None
