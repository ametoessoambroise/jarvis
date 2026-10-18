"""
Tray Indicator — shows a system tray icon when screen sharing is active.
"""

from __future__ import annotations

import threading

try:
    import pystray
    from PIL import Image, ImageDraw
    _PYSTRAY = True
except ImportError:
    _PYSTRAY = False


class TrayIndicator:
    def __init__(self, on_stop_callback):
        self.on_stop = on_stop_callback
        self._icon = None

    def show_active(self):
        """Show the 'eye open' icon to indicate active screen sharing."""
        if not _PYSTRAY:
            return
        icon_img = self._create_icon(color="#00BFFF")
        self._run_icon(icon_img, title="JARVIS — Partage d'écran actif")

    def hide(self):
        if self._icon:
            self._icon.stop()
            self._icon = None

    def _create_icon(self, color: str):
        img = Image.new("RGB", (64, 64), color="black")
        draw = ImageDraw.Draw(img)
        draw.ellipse([8, 8, 56, 56], fill=color)
        draw.ellipse([22, 22, 42, 42], fill="black")
        return img

    def _run_icon(self, icon_img, title):
        menu = pystray.Menu(
            pystray.MenuItem("Arrêter le partage", self.on_stop)
        )
        self._icon = pystray.Icon("jarvis", icon_img, title, menu)
        threading.Thread(target=self._icon.run, daemon=True).start()
