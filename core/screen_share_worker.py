"""
Screen Share Worker — diff-based screen capture utility.
Captures the screen, applies privacy filters, and returns compressed
JPEG bytes only when the screen has actually changed.

This module does NOT own a thread or event loop.  It is called
periodically from the async loop inside JarvisLive.
"""

from __future__ import annotations

import hashlib
import json
from io import BytesIO
from pathlib import Path

try:
    import mss
    import mss.tools
    _MSS = True
except ImportError:
    _MSS = False

try:
    from PIL import Image
    _PIL = True
except ImportError:
    _PIL = False

from core.utils import BASE_DIR
from core.privacy_guard import apply_privacy_filter

_PROFILES_PATH = BASE_DIR / "config" / "app_profiles.json"


def _capture_settings() -> dict:
    """Load capture settings from app_profiles.json."""
    try:
        if _PROFILES_PATH.exists():
            cfg = json.loads(_PROFILES_PATH.read_text(encoding="utf-8"))
            return cfg.get("capture", {})
    except Exception:
        pass
    return {}


class ScreenShareWorker:
    """
    Stateful capture utility.
    Call ``capture_frame(inspector)`` periodically; it returns compressed
    JPEG bytes when the screen has changed, or ``None`` when it hasn't
    (or when the active app is blacklisted).
    """

    def __init__(self):
        self._last_hash: str = ""
        self.active: bool    = False
        self.frames_sent: int = 0

    # ── Main capture method (CPU-bound — run in executor) ────────────

    def capture_frame(self, inspector) -> bytes | None:
        """
        Capture, filter, diff-check, compress.
        *inspector* must be a ``UIInspector`` instance.
        Returns JPEG bytes or None.
        """
        if not self.active or not _MSS or not _PIL:
            return None

        settings = _capture_settings()
        width    = settings.get("width",   640)
        height   = settings.get("height",  360)
        quality  = settings.get("jpeg_quality", 50)

        try:
            # 1. Capture
            with mss.mss() as sct:
                monitors = sct.monitors
                mon = monitors[1] if len(monitors) > 1 else monitors[0]
                raw = sct.grab(mon)

            img = Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")
            img = img.resize((width, height), Image.LANCZOS)

            # 2. Privacy filter
            window_info = inspector.get_active_window_info()
            elements    = inspector.get_active_window_elements()

            filtered = apply_privacy_filter(
                img,
                window_info.get("title", ""),
                window_info.get("process", ""),
                elements,
            )

            if filtered is None:
                # App is blacklisted — skip
                return None

            # 3. Compress
            buf = BytesIO()
            filtered.save(buf, format="JPEG", quality=quality, optimize=False)
            img_bytes = buf.getvalue()

            # 4. Diff check
            current_hash = hashlib.md5(img_bytes).hexdigest()
            if current_hash == self._last_hash:
                return None   # screen unchanged

            self._last_hash = current_hash
            self.frames_sent += 1
            return img_bytes

        except Exception as e:
            print(f"[ScreenShareWorker] ⚠️  capture error: {e}")
            return None

    def reset(self):
        """Clear state (e.g. on session reconnect)."""
        self._last_hash = ""
        self.frames_sent = 0
