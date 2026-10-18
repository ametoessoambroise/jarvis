"""
Action Verifier — captures screen state before / after an action
and retries with a fallback strategy if the screen did not change.
"""

from __future__ import annotations

import hashlib
import time
from io import BytesIO

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


class ActionVerifier:
    """Execute an action, verify the screen changed, retry if not."""

    MAX_RETRIES      = 2
    WAIT_AFTER_ACTION = 0.8   # seconds

    def capture_state(self) -> str:
        """Return an MD5 hash of a low-res screenshot."""
        if not _MSS or not _PIL:
            return ""

        try:
            with mss.mss() as sct:
                mon = sct.monitors[1] if len(sct.monitors) > 1 else sct.monitors[0]
                raw = sct.grab(mon)
                img = Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")
                img = img.resize((320, 180), Image.LANCZOS)
                buf = BytesIO()
                img.save(buf, format="JPEG", quality=40)
                return hashlib.md5(buf.getvalue()).hexdigest()
        except Exception:
            return ""

    def execute_with_verification(
        self,
        action_fn,
        fallback_fn=None,
    ) -> bool:
        """
        Run *action_fn*, wait briefly, then check whether the screen changed.
        If unchanged, retry up to MAX_RETRIES times using *fallback_fn*.
        Returns True if the screen changed (action likely succeeded).
        """
        state_before = self.capture_state()
        if not state_before:
            # Cannot verify — just run the action and hope for the best
            action_fn()
            return True

        for attempt in range(self.MAX_RETRIES + 1):
            if attempt == 0:
                action_fn()
            elif fallback_fn:
                print(f"[ActionVerifier] Retry #{attempt} with fallback")
                fallback_fn()
            else:
                break

            time.sleep(self.WAIT_AFTER_ACTION)
            state_after = self.capture_state()

            if state_after != state_before:
                return True   # screen changed → success

        print("[ActionVerifier] ❌ Screen unchanged after retries")
        return False
