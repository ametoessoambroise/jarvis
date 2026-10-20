"""
Hotkey Listener — allows triggering specific Jarvis actions via keyboard shortcuts.
Includes 'Ctrl+Shift+J' for targeted high-resolution screen analysis.
"""

from __future__ import annotations

import asyncio
import threading
from io import BytesIO

try:
    import keyboard
    import pyautogui
    import mss
    from PIL import Image
    _HOTKEY_ENABLED = True
except ImportError:
    _HOTKEY_ENABLED = False


HOTKEY = "ctrl+shift+j"
ZONE_SIZE = 400  # pixels


class HotkeyListener:
    def __init__(self, jarvis_live):
        self.jarvis_live = jarvis_live
        self._thread = None
        self._started = False
        self._hotkey_ref = None

    def start(self):
        """Démarre l'écouteur de raccourci de manière idempotente."""
        if self._started:
            return

        if not _HOTKEY_ENABLED:
            print("[Hotkey] ⚠️ Missing dependencies (keyboard, pyautogui, mss, PIL). Hotkey disabled.")
            return

        try:
            self._hotkey_ref = keyboard.add_hotkey(HOTKEY, self._on_look_here)
            self._started = True
            print(f"[Hotkey] ✅ Registered {HOTKEY}")
        except Exception as e:
            print(f"[Hotkey] ⚠️ Failed to register hotkey {HOTKEY}: {e}")

    def stop(self):
        """Désenregistre le raccourci clavier proprement."""
        if not self._started:
            return
        if _HOTKEY_ENABLED and self._hotkey_ref is not None:
            try:
                keyboard.remove_hotkey(self._hotkey_ref)
            except Exception as e:
                print(f"[Hotkey] ⚠️ Error removing hotkey: {e}")
            self._hotkey_ref = None
        self._started = False
        print(f"[Hotkey] 🛑 Unregistered {HOTKEY}")


    def _on_look_here(self):
        """Capture high-resolution area around the cursor and send to Gemini."""
        print("[Hotkey] 👁️ Look here triggered!")
        mx, my = pyautogui.position()
        x1 = max(0, mx - ZONE_SIZE // 2)
        y1 = max(0, my - ZONE_SIZE // 2)

        try:
            with mss.mss() as sct:
                monitor = {"top": y1, "left": x1, "width": ZONE_SIZE, "height": ZONE_SIZE}
                raw = sct.grab(monitor)
                img = Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")
                buf = BytesIO()
                img.save(buf, format="JPEG", quality=85)  # High quality for analysis
                img_bytes = buf.getvalue()

            if self.jarvis_live.session and self.jarvis_live._loop:
                asyncio.run_coroutine_threadsafe(
                    self._send_for_analysis(img_bytes),
                    loop=self.jarvis_live._loop
                )
        except Exception as e:
            print(f"[Hotkey] ⚠️ Error during Look Here: {e}")

    async def _send_for_analysis(self, img_bytes: bytes):
        try:
            await self.jarvis_live.session.send_realtime_input(
                media={"mime_type": "image/jpeg", "data": img_bytes}
            )
            await self.jarvis_live.session.send_client_content(
                turns=[{"role": "user", "parts": [{"text": "Analyse detaillement ce que tu vois dans cette zone de l'écran (image jointe). Quelles actions puis-je faire ici ?"}]}],
                turn_complete=True
            )
            self.jarvis_live.ui.write_log("SYS: Sent screen area for analysis.")
        except Exception as e:
             print(f"[Hotkey] ⚠️ Error sending to Gemini: {e}")
