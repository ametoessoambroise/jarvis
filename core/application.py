"""Application — point central de composition et cycle de vie de JARVIS.

Ce module assemble l'application en respectant les frontières de couches :
le cœur applicatif reçoit l'UI via le protocole UiPort et orchestre la session,
les outils et l'arrêt coopératif sans dépendance directe vers PyQt6.

Références :
    TRD.md §3.2 (Cible V1)
    DEVELOPMENT_PHASES.md P4 (Application & shutdown)
    RISKS.md R-O23 (arrêt coopératif)
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from core.ui_port import UiPort

logger = logging.getLogger("jarvis.application")


class JarvisApplication:
    """Orchestrateur de cycle de vie et de composition de JARVIS."""

    def __init__(self, ui: UiPort, live_instance: Any = None):
        self.ui = ui

        if live_instance is not None:
            self.live = live_instance
        else:
            from core.jarvis_live import JarvisLive
            self.live = JarvisLive(ui)

        # Câblage de la commande texte
        self.ui.on_text_command = self.live._on_text_command

    async def run(self) -> None:
        """Démarre le moteur applicatif."""
        try:
            await self.live.run()
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error("Error in application run: %s", e)
            self.ui.show_error(f"Application run error: {e}")

    async def shutdown(self, grace_s: float = 5.0) -> None:
        """Arrêt coopératif de l'ensemble de l'application."""
        print("[Application] 🛑 Shutting down JarvisApplication...")
        try:
            if hasattr(self.live, "shutdown"):
                await self.live.shutdown(grace_s=grace_s)
        except Exception as e:
            logger.warning("Error during live shutdown: %s", e)
        print("[Application] 🛑 Application shutdown finished.")
