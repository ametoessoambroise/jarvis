"""UiPort protocol — interface d'inversion de dépendance pour l'UI.

Ce module définit le contrat strict que tout composant UI (ex. JarvisUI)
doit satisfaire pour dialoguer avec le cœur de JARVIS.
Aucun module de core/ ne doit importer directement ui/ : tout passe par UiPort.

Référence :
    BACKEND_CONTRACT.md C-17 (UiPort / UiEvents)
    DEVELOPMENT_PHASES.md P4 (règle d'architecture V1-LIVE-01)
"""

from __future__ import annotations

from typing import Callable, Protocol, runtime_checkable


@runtime_checkable
class UiPort(Protocol):
    """Protocole découplant le moteur applicatif de l'interface utilisateur."""

    @property
    def muted(self) -> bool:
        """Indique si le microphone est coupé par l'utilisateur."""
        ...

    @property
    def current_file(self) -> str | None:
        """Dernier fichier déposé dans la zone de dépôt (drag & drop), ou None."""
        ...

    on_text_command: Callable[[str], None] | None
    """Callback appelé par l'UI lorsqu'une commande texte est saisie par l'utilisateur."""

    def write_log(self, text: str) -> None:
        """Ajoute une ligne dans le journal d'activité de l'UI."""
        ...

    def set_state(self, state: str) -> None:
        """Met à jour l'état visuel du HUD (LISTENING, THINKING, SPEAKING, MUTED, etc.)."""
        ...

    def show_error(self, message: str) -> None:
        """Affiche un message d'erreur clair et actionnable dans l'interface."""
        ...
