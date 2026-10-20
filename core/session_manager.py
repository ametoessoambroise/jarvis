"""Session Manager — cycle de vie, boucles asynchrones et reconnexion bornée.

Gère la connexion et la supervision de la session Gemini Live (ou faux provider de test),
la classification des erreurs fatales vs transitoires, et l'orchestration des tâches
d'entrée/sortie audio et d'outils détachés.

Références :
    BACKEND_CONTRACT.md C-01 (SessionManager)
    DEVELOPMENT_PHASES.md P4 (V1-LIVE-01, V1-LIVE-02)
    RISKS.md R-O14 (concurrence, reconnexion, outils détachés)
"""

from __future__ import annotations

import asyncio
import logging
import traceback
from typing import Any, Callable

from core.audio_io import AudioDeviceError, AudioIO
from core.background_loops import poll_notifications_loop, screen_share_loop
from core.tools import TOOL_DECLARATIONS
from core.ui_port import UiPort
from core.utils import (
    BASE_DIR,
    LIVE_MODEL,
    _clean_transcript,
    _get_api_key,
    _load_system_prompt,
)
from memory.memory_manager import format_memory_for_prompt, load_memory

logger = logging.getLogger("jarvis.session")

_FATAL_PATTERNS = (
    "UNAUTHENTICATED",
    "API_KEY_INVALID",
    "PERMISSION_DENIED",
    "INVALID_ARGUMENT",
    "API_KEY_EXPIRED",
    "CONFIG_MISSING",
    "CONFIG_ERROR",
)


class SessionManager:
    """Gestionnaire de session de haut niveau découplé de l'UI concrète."""

    def __init__(
        self,
        ui: UiPort,
        audio_io: AudioIO | None = None,
        tool_executor: Callable[[Any], Any] | None = None,
        notification_manager: Any = None,
        screen_share_worker: Any = None,
        ui_inspector: Any = None,
        hotkey_listener: Any = None,
        client: Any = None,
        max_reconnect: int = 5,
    ):
        self.ui = ui
        self.audio_io = audio_io or AudioIO()
        self.tool_executor = tool_executor
        self.notification_manager = notification_manager
        self.screen_share_worker = screen_share_worker
        self.ui_inspector = ui_inspector
        self.hotkey_listener = hotkey_listener
        self.custom_client = client
        self.max_reconnect = max_reconnect

        self.session: Any | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._is_speaking = False
        self._speaking_lock = asyncio.Lock() if asyncio.get_event_loop().is_running() else None
        self._turn_done_event: asyncio.Event | None = None
        self._shutdown_requested = False
        self._active_tasks: set[asyncio.Task] = set()
        self.screen_share_active = False

    def is_speaking(self) -> bool:
        return self._is_speaking

    def set_speaking(self, value: bool) -> None:
        self._is_speaking = value
        if value:
            self.ui.set_state("SPEAKING")
        elif not self.ui.muted:
            self.ui.set_state("LISTENING")

    def is_muted(self) -> bool:
        return self.ui.muted

    def build_config(self) -> Any:
        """Construit la configuration LiveConnectConfig."""
        from datetime import datetime
        import json
        from google.genai import types

        memory = load_memory()
        mem_str = format_memory_for_prompt(memory)
        sys_prompt = _load_system_prompt()

        now = datetime.now()
        time_str = now.strftime("%A, %B %d, %Y — %I:%M %p")
        time_ctx = (
            f"[CURRENT DATE & TIME]\n"
            f"Right now it is: {time_str}\n"
            f"Use this to calculate exact times for reminders.\n\n"
        )

        parts = [time_ctx]
        if mem_str:
            parts.append(mem_str)

        try:
            cfg_path = BASE_DIR / "config" / "notifications_config.json"
            if cfg_path.exists():
                cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
                notif_cfg_str = (
                    f"[NOTIFICATION SYSTEM CONFIGURATION]\n"
                    f"You are connected to a system notification listener. When the user receives a notification, you will be alerted.\n"
                    f"Rules and allowed apps:\n"
                    f"{json.dumps(cfg, indent=2)}\n"
                    f"If a notification is received, decide whether you need to reply to the sender using the `send_message` tool or tell the user about it, depending on the app, sender, and content. Follow the rules defined above.\n\n"
                )
                parts.append(notif_cfg_str)
        except Exception as e:
            logger.warning("Error loading notification config for system prompt: %s", e)

        parts.append(sys_prompt)

        return types.LiveConnectConfig(
            response_modalities=["AUDIO"],
            output_audio_transcription={},
            input_audio_transcription={},
            system_instruction="\n".join(parts),
            tools=[{"function_declarations": TOOL_DECLARATIONS}],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Charon")
                )
            ),
        )

    async def send_text_command(self, text: str) -> bool:
        """Envoie une commande texte au modèle."""
        if not self.session or not self._loop:
            self.ui.write_log("SYS: Pas de connexion active — commande texte non envoyée.")
            return False

        try:
            await self.session.send_client_content(
                turns={"parts": [{"text": text}]}, turn_complete=True
            )
            return True
        except Exception as e:
            logger.error("Failed to send text command: %s", e)
            self.ui.write_log(f"ERR: Échec envoi commande texte: {e}")
            return False

    async def _execute_tool_detached(self, function_call: Any) -> None:
        """Exécute un outil dans une tâche détachée et renvoie la réponse sans bloquer receive()."""
        try:
            if not self.tool_executor:
                return
            fn_res = await self.tool_executor(function_call)
            if self.session and fn_res:
                await self.session.send_tool_response(function_responses=[fn_res])
        except Exception as e:
            logger.error("Error executing detached tool %s: %s", getattr(function_call, "name", "unknown"), e)

    async def _receive_loop(self) -> None:
        """Reçoit les réponses audio, texte et tool_call de la session."""
        print("[JARVIS] 👂 Recv started")
        out_buf: list[str] = []
        in_buf: list[str] = []

        try:
            while not self._shutdown_requested:
                async for response in self.session.receive():
                    if self._shutdown_requested:
                        break

                    # Audio entrant
                    if response.data:
                        if self._turn_done_event and self._turn_done_event.is_set():
                            self._turn_done_event.clear()
                        self.audio_io.audio_in_queue.put_nowait(response.data)

                    # Transcription
                    if response.server_content:
                        sc = response.server_content
                        if sc.output_transcription and sc.output_transcription.text:
                            txt = _clean_transcript(sc.output_transcription.text)
                            if txt:
                                out_buf.append(txt)

                        if sc.input_transcription and sc.input_transcription.text:
                            txt = _clean_transcript(sc.input_transcription.text)
                            if txt:
                                in_buf.append(txt)

                        if sc.turn_complete:
                            if self._turn_done_event:
                                self._turn_done_event.set()

                            full_in = " ".join(in_buf).strip()
                            if full_in:
                                self.ui.write_log(f"You: {full_in}")
                            in_buf.clear()

                            full_out = " ".join(out_buf).strip()
                            if full_out:
                                self.ui.write_log(f"Jarvis: {full_out}")
                            out_buf.clear()

                    # Outils : exécutés en tâches détachées pour NE PAS bloquer la réception audio
                    if response.tool_call:
                        for fc in response.tool_call.function_calls:
                            print(f"[JARVIS] 📞 {fc.name}")
                            # Planifier en tâche détachée
                            task = asyncio.create_task(self._execute_tool_detached(fc))
                            self._active_tasks.add(task)
                            task.add_done_callback(self._active_tasks.discard)

        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"[JARVIS] ❌ Recv error: {e}")
            raise

    async def run(self) -> None:
        """Boucle principale de cycle de vie avec reconnexion bornée."""
        self._loop = asyncio.get_running_loop()
        self.audio_io.reset_queues(self._loop)
        self._turn_done_event = asyncio.Event()

        # Obtention du client
        if self.custom_client is not None:
            client = self.custom_client
        else:
            from google import genai
            try:
                api_key = _get_api_key()
            except Exception as exc:
                self.ui.set_state("NOT_CONFIGURED")
                self.ui.show_error(f"Clé API manquante ou invalide: {exc}")
                return
            client = genai.Client(
                api_key=api_key, http_options={"api_version": "v1alpha"}
            )

        reconnect_count = 0

        while reconnect_count < self.max_reconnect and not self._shutdown_requested:
            try:
                print("[JARVIS] 🔌 Connecting...")
                self.ui.set_state("THINKING")
                config = self.build_config()

                try:
                    async with (
                        client.aio.live.connect(
                            model=LIVE_MODEL, config=config
                        ) as session,
                        asyncio.TaskGroup() as tg,
                    ):
                        self.session = session
                        reconnect_count = 0  # Succès : réinitialisation du compteur

                        print("[JARVIS] ✅ Connected.")
                        self.ui.set_state("LISTENING")
                        self.ui.write_log("SYS: JARVIS online.")

                        # Démarrage des composants auxiliaires
                        if self.notification_manager:
                            await self.notification_manager.initialize()

                        if self.hotkey_listener:
                            self.hotkey_listener.start()

                        # Enregistrement des boucles dans le TaskGroup
                        tg.create_task(self.audio_io.send_realtime_loop(session))
                        tg.create_task(
                            self.audio_io.listen_mic_loop(
                                self._loop, self.is_speaking, self.is_muted
                            )
                        )
                        tg.create_task(self._receive_loop())
                        tg.create_task(
                            self.audio_io.play_audio_loop(
                                self.set_speaking, self._turn_done_event
                            )
                        )
                        if self.notification_manager:
                            tg.create_task(
                                poll_notifications_loop(
                                    self.notification_manager,
                                    lambda: self.session,
                                    self.ui,
                                )
                            )
                        if self.screen_share_worker and self.ui_inspector:
                            tg.create_task(
                                screen_share_loop(
                                    self.screen_share_worker,
                                    self.ui_inspector,
                                    lambda: self.session,
                                    lambda: self.screen_share_active,
                                    self._loop,
                                )
                            )
                finally:
                    self.session = None
                    if self.hotkey_listener:
                        self.hotkey_listener.stop()

            except AudioDeviceError as ade:
                # Erreur matérielle : inutile de spammer la reconnexion réseau
                print(f"[JARVIS] ❌ Erreur audio fatale: {ade}")
                self.ui.set_state("ERROR")
                self.ui.show_error(f"Problème matériel audio: {ade}")
                break

            except Exception as e:
                err_str = str(e)
                print(f"[JARVIS] ❌ Session exception: {err_str}")

                # Vérifier si l'erreur est fatale (auth/permissions/arguments)
                is_fatal = any(pat in err_str.upper() for pat in _FATAL_PATTERNS)
                if is_fatal or self._shutdown_requested:
                    self.ui.set_state("ERROR")
                    self.ui.show_error(f"Erreur fatale: {err_str}")
                    break

                reconnect_count += 1
                if reconnect_count < self.max_reconnect:
                    wait_s = min(3 * reconnect_count, 30)
                    self.ui.set_state("OFFLINE")
                    self.ui.write_log(
                        f"SYS: Connexion perdue. Tentative {reconnect_count}/{self.max_reconnect} dans {wait_s}s..."
                    )
                    await asyncio.sleep(wait_s)
                else:
                    self.ui.set_state("ERROR")
                    self.ui.show_error(
                        f"Impossible de se reconnecter après {self.max_reconnect} tentatives. Redémarrez JARVIS."
                    )

    async def shutdown(self, grace_s: float = 5.0) -> None:
        """Arrêt coopératif propre de la session et des tâches en cours."""
        self._shutdown_requested = True
        print("[JARVIS] 🛑 Shutdown initiated...")

        # Arrêt hotkey
        if self.hotkey_listener:
            try:
                self.hotkey_listener.stop()
            except Exception:
                pass

        # Annulation des tâches détachées
        for t in list(self._active_tasks):
            t.cancel()

        # Fermeture session
        if self.session:
            try:
                # Laisser un court délai coopératif
                await asyncio.sleep(0.1)
            except Exception:
                pass
            self.session = None

        self.ui.set_state("OFFLINE")
        print("[JARVIS] 🛑 Shutdown complete.")
