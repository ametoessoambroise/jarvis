import asyncio
import threading
import traceback

import sounddevice as sd
from google import genai
from google.genai import types

from ui import JarvisUI
from memory.memory_manager import load_memory, update_memory, format_memory_for_prompt

from actions.file_processor import file_processor
from actions.flight_finder import flight_finder
from actions.open_app import open_app
from actions.weather_report import weather_action
from actions.send_message import send_message
from actions.get_context import get_context
from actions.reminder import reminder
from actions.computer_settings import computer_settings
from actions.screen_processor import screen_process
from actions.youtube_video import youtube_video
from actions.desktop import desktop_control
from actions.browser_control import browser_control
from actions.file_controller import file_controller
from actions.code_helper import code_helper
from actions.dev_agent import dev_agent
from actions.iot_control import iot_control
from actions.manage_autonomy import manage_autonomy
from actions.system_optimizer import system_optimizer
from actions.web_search import web_search as web_search_action
from actions.computer_control import computer_control
from actions.game_updater import game_updater

from core.context_engine import ContextEngine
from core.utils import _get_api_key, _load_system_prompt, _clean_transcript, LIVE_MODEL
from core.utils import SEND_SAMPLE_RATE, RECEIVE_SAMPLE_RATE, CHANNELS, CHUNK_SIZE
from core.tools import TOOL_DECLARATIONS
from core.autonomy_manager import AutonomyManager, IdeaPriority, IdeaStatus

from core.screen_share_worker import ScreenShareWorker
from actions.ui_inspector import UIInspector
from actions.browser_inspector import BrowserInspector
from ui.screen_overlay import ScreenOverlay
from core.action_verifier import ActionVerifier
from logs.action_logger import ActionLogger
from ui.tray_indicator import TrayIndicator
from core.hotkey_listener import HotkeyListener


class JarvisLive:

    def __init__(self, ui: JarvisUI):
        self.ui = ui
        self.session = None
        self.audio_in_queue = None
        self.out_queue = None
        self._loop = None
        self._is_speaking = False
        self._speaking_lock = threading.Lock()
        self.ui.on_text_command = self._on_text_command
        self._turn_done_event: asyncio.Event | None = None

        from core.notification_manager import NotificationManager
        from core.utils import BASE_DIR

        self.notification_manager = NotificationManager(BASE_DIR)

        # Screen Share Architecture
        self.screen_share_worker = ScreenShareWorker()
        self.ui_inspector = UIInspector()
        self.browser_inspector = BrowserInspector()
        self.overlay = ScreenOverlay()
        self.action_verifier = ActionVerifier()
        self.logger = ActionLogger()
        self.tray = TrayIndicator(self._on_tray_stop_screen_share)
        self.hotkey_listener = HotkeyListener(self)
        self.autonomy_manager = AutonomyManager()
        self.context_engine = ContextEngine()
        self.screen_share_active = False

    def _on_tray_stop_screen_share(self):
        self.screen_share_active = False
        self.tray.hide()
        self.screen_share_worker.reset()
        self.speak("Screen sharing stopped.")

    def _on_text_command(self, text: str):
        if not self._loop or not self.session:
            return
        asyncio.run_coroutine_threadsafe(
            self.session.send_client_content(
                turns={"parts": [{"text": text}]}, turn_complete=True
            ),
            self._loop,
        )

    def set_speaking(self, value: bool):
        with self._speaking_lock:
            self._is_speaking = value
        if value:
            self.ui.set_state("SPEAKING")
        elif not self.ui.muted:
            self.ui.set_state("LISTENING")

    def speak(self, text: str):
        """Send text to the live session. Delegates to _on_text_command to avoid duplication."""
        self._on_text_command(text)

    def speak_error(self, tool_name: str, error: str):
        short = str(error)[:120]
        self.ui.write_log(f"ERR: {tool_name} — {short}")
        self.speak(f"Sir, {tool_name} encountered an error. {short}")

    def _build_config(self) -> types.LiveConnectConfig:
        from datetime import datetime

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

        # Inject notification configuration into system instruction
        from core.utils import BASE_DIR

        notif_cfg_str = ""
        try:
            cfg_path = BASE_DIR / "config" / "notifications_config.json"
            if cfg_path.exists():
                import json

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
            print(f"Error loading notification config for system prompt: {e}")

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

    async def _execute_tool(self, fc) -> types.FunctionResponse:
        """Exécute un outil Gemini via le dispatcher centralisé.

        Drapeau de retour arrière : JARVIS_USE_LEGACY_EXECUTE=1 (P4 gate).
        """
        import os
        if os.environ.get("JARVIS_USE_LEGACY_EXECUTE") == "1":
            return await self._execute_tool_legacy(fc)

        name = fc.name
        args = dict(fc.args or {})

        print(f"[JARVIS] 🔧 {name}  {args}")
        self.ui.set_state("THINKING")

        # ── Handlers internes (accèdent à self) ──────────────────────────────
        internal_result: str | None = None
        handled_internally = True

        if name == "save_memory":
            internal_result = await self._handle_save_memory(args)
        elif name == "agent_task":
            internal_result = await self._handle_agent_task(args)
        elif name == "toggle_screen_share":
            internal_result = await self._handle_toggle_screen_share(args)
        elif name == "interact_ui":
            internal_result = await self._handle_interact_ui(args)
        elif name == "shutdown_jarvis":
            internal_result = await self._handle_shutdown_jarvis(args)
        elif name == "screen_process":
            internal_result = await self._handle_screen_process(args)
        elif name == "manage_autonomy":
            internal_result = await self._handle_manage_autonomy(args)
        elif name == "send_message":
            # send_message nécessite un pré-appel get_context — géré ici
            internal_result = await self._handle_send_message(args)
        elif name == "file_processor":
            # file_processor utilise self.ui.current_file
            internal_result = await self._handle_file_processor(args)
        else:
            handled_internally = False

        if handled_internally:
            result_str = internal_result or "terminé, non vérifié"
            print(f"[JARVIS] 📤 {name} → {str(result_str)[:80]}")
            if not self.ui.muted:
                self.ui.set_state("LISTENING")
            return types.FunctionResponse(
                id=fc.id, name=name, response={"result": result_str}
            )

        # ── Dispatcher pour les 17 outils restants ───────────────────────────
        from core.tool_registry import _REGISTRY
        from core.tool_dispatcher import dispatch

        loop = asyncio.get_event_loop()
        spec = _REGISTRY.get(name)

        if spec is None:
            result_str = f"Unknown tool: {name}"
        else:
            context = {"player": self.ui, "speak": self.speak}
            tool_result = await loop.run_in_executor(
                None, lambda: dispatch(spec, args, context)
            )
            result_str = tool_result.message

        print(f"[JARVIS] 📤 {name} → {str(result_str)[:80]}")
        if not self.ui.muted:
            self.ui.set_state("LISTENING")
        return types.FunctionResponse(
            id=fc.id, name=name, response={"result": result_str}
        )

    # ── Handlers internes ─────────────────────────────────────────────────────

    async def _handle_save_memory(self, args: dict) -> str:
        category = args.get("category", "notes")
        key = args.get("key", "")
        value = args.get("value", "")
        if key and value:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None, lambda: update_memory({category: {key: {"value": value}}})
            )
            print(f"[Memory] 💾 save_memory: {category}/{key} = {value}")
        return "ok"

    async def _handle_agent_task(self, args: dict) -> str:
        from agent.task_queue import get_queue, TaskPriority
        priority_map = {
            "low": TaskPriority.LOW,
            "normal": TaskPriority.NORMAL,
            "high": TaskPriority.HIGH,
        }
        priority = priority_map.get(
            args.get("priority", "normal").lower(), TaskPriority.NORMAL
        )
        task_id = get_queue().submit(
            goal=args.get("goal", ""), priority=priority, speak=self.speak
        )
        return f"Task started (ID: {task_id})."

    async def _handle_toggle_screen_share(self, args: dict) -> str:
        state = args.get("state", "off").lower()
        if state == "on":
            self.screen_share_active = True
            self.screen_share_worker.active = True
            self.tray.show_active()
            self.ui.write_log("SYS: Screen sharing started.")
            return "Screen sharing is now active. I will receive your screen frames and UI elements."
        else:
            self._on_tray_stop_screen_share()
            return "Screen sharing stopped."

    async def _handle_interact_ui(self, args: dict) -> str:
        import time as _time
        import pyautogui
        action = args.get("action", "")
        x, y = args.get("x"), args.get("y")
        elem_name = args.get("name", "")
        val = args.get("value", "")

        self.overlay.show_click_preview(x, y, label=elem_name or action)

        def _do_action():
            if action == "click":
                pyautogui.click(x, y)
            elif action == "type":
                pyautogui.click(x, y)
                _time.sleep(0.1)
                pyautogui.write(val, interval=0.02)

        loop = asyncio.get_event_loop()
        success = await loop.run_in_executor(
            None, lambda: self.action_verifier.execute_with_verification(_do_action)
        )
        await loop.run_in_executor(
            None,
            lambda: self.logger.log(action, {"x": x, "y": y, "name": elem_name}, val, success),
        )
        return f"Action {action} at ({x},{y}) executed. Verified: {success}"

    async def _handle_shutdown_jarvis(self, args: dict) -> str:
        import os as _os
        self.ui.write_log("SYS: Shutdown requested.")
        self.speak("Goodbye, sir.")

        def _shutdown():
            import time as _time
            _time.sleep(1)
            _os._exit(0)

        threading.Thread(target=_shutdown, daemon=True).start()
        return "Shutting down."

    async def _handle_screen_process(self, args: dict) -> str:
        threading.Thread(
            target=screen_process,
            kwargs={"parameters": args, "response": None, "player": self.ui, "session_memory": None},
            daemon=True,
        ).start()
        return "Vision module activated. Stay completely silent — vision module will speak directly."

    async def _handle_manage_autonomy(self, args: dict) -> str:
        loop = asyncio.get_event_loop()
        r = await loop.run_in_executor(
            None, lambda: manage_autonomy(parameters=args, player=self.ui, jarvis=self)
        )
        return r or "Autonomy settings updated."

    async def _handle_send_message(self, args: dict) -> str:
        """send_message avec pré-appel get_context."""
        loop = asyncio.get_event_loop()
        receiver = args.get("receiver") or args.get("contact") or args.get("to")
        platform = args.get("platform", "whatsapp")
        if receiver:
            try:
                ctx_args = {"contact": receiver, "app": platform}
                ctx_r = await loop.run_in_executor(
                    None,
                    lambda: get_context(
                        parameters=ctx_args, response=None, player=self.ui, session_memory=None
                    ),
                )
                if ctx_r:
                    try:
                        self.ui.write_log(f"[GetContext] {str(ctx_r)[:200]}")
                    except Exception:
                        pass
            except Exception as e:
                try:
                    self.ui.write_log(f"[GetContext] failed: {e}")
                except Exception:
                    pass

        r = await loop.run_in_executor(
            None,
            lambda: send_message(parameters=args, response=None, player=self.ui, session_memory=None),
        )
        return r or f"Message sent to {args.get('receiver')}."

    async def _handle_file_processor(self, args: dict) -> str:
        """file_processor avec injection de self.ui.current_file si absent."""
        loop = asyncio.get_event_loop()
        if not args.get("file_path") and self.ui.current_file:
            args["file_path"] = self.ui.current_file
        r = await loop.run_in_executor(
            None,
            lambda: file_processor(parameters=args, player=self.ui, speak=self.speak),
        )
        return r or "Done."

    async def _execute_tool_legacy(self, fc) -> types.FunctionResponse:
        """Implémentation historique if/elif — drapeau JARVIS_USE_LEGACY_EXECUTE=1.

        Conservée intacte jusqu'à la gate de P4 pour retour arrière rapide.
        """
        name = fc.name
        args = dict(fc.args or {})
        loop = asyncio.get_event_loop()

        print(f"[JARVIS][legacy] 🔧 {name}  {args}")
        self.ui.set_state("THINKING")

        if name == "save_memory":
            category = args.get("category", "notes")
            key = args.get("key", "")
            value = args.get("value", "")
            if key and value:
                await loop.run_in_executor(
                    None, lambda: update_memory({category: {key: {"value": value}}})
                )
                print(f"[Memory] 💾 save_memory: {category}/{key} = {value}")
            if not self.ui.muted:
                self.ui.set_state("LISTENING")
            return types.FunctionResponse(
                id=fc.id, name=name, response={"result": "ok"}
            )

        result = "Done."

        try:
            if name == "open_app":
                r = await loop.run_in_executor(None, lambda: open_app(parameters=args, response=None, player=self.ui))
                result = r or f"Opened {args.get('app_name')}."
            elif name == "weather_report":
                r = await loop.run_in_executor(None, lambda: weather_action(parameters=args, player=self.ui))
                result = r or "Weather delivered."
            elif name == "browser_control":
                r = await loop.run_in_executor(None, lambda: browser_control(parameters=args, player=self.ui))
                result = r or "Done."
            elif name == "file_controller":
                r = await loop.run_in_executor(None, lambda: file_controller(parameters=args, player=self.ui))
                result = r or "Done."
            elif name == "send_message":
                result = await self._handle_send_message(args)
            elif name == "get_context":
                r = await loop.run_in_executor(None, lambda: get_context(parameters=args, response=None, player=self.ui, session_memory=None))
                result = r or "Context retrieved."
            elif name == "reminder":
                r = await loop.run_in_executor(None, lambda: reminder(parameters=args, response=None, player=self.ui))
                result = r or "Reminder set."
            elif name == "youtube_video":
                r = await loop.run_in_executor(None, lambda: youtube_video(parameters=args, response=None, player=self.ui))
                result = r or "Done."
            elif name == "screen_process":
                result = await self._handle_screen_process(args)
            elif name == "computer_settings":
                r = await loop.run_in_executor(None, lambda: computer_settings(parameters=args, response=None, player=self.ui))
                result = r or "Done."
            elif name == "manage_autonomy":
                result = await self._handle_manage_autonomy(args)
            elif name == "system_optimizer":
                r = await loop.run_in_executor(None, lambda: system_optimizer(parameters=args, player=self.ui))
                result = r or "System optimization action executed."
            elif name == "iot_control":
                r = await loop.run_in_executor(None, lambda: iot_control(parameters=args, player=self.ui))
                result = r or "IoT control action completed."
            elif name == "desktop_control":
                r = await loop.run_in_executor(None, lambda: desktop_control(parameters=args, player=self.ui))
                result = r or "Done."
            elif name == "code_helper":
                r = await loop.run_in_executor(None, lambda: code_helper(parameters=args, player=self.ui, speak=self.speak))
                result = r or "Done."
            elif name == "dev_agent":
                r = await loop.run_in_executor(None, lambda: dev_agent(parameters=args, player=self.ui, speak=self.speak))
                result = r or "Done."
            elif name == "agent_task":
                result = await self._handle_agent_task(args)
            elif name == "web_search":
                r = await loop.run_in_executor(None, lambda: web_search_action(parameters=args, player=self.ui))
                result = r or "Done."
            elif name == "file_processor":
                result = await self._handle_file_processor(args)
            elif name == "computer_control":
                r = await loop.run_in_executor(None, lambda: computer_control(parameters=args, player=self.ui))
                result = r or "Done."
            elif name == "game_updater":
                r = await loop.run_in_executor(None, lambda: game_updater(parameters=args, player=self.ui, speak=self.speak))
                result = r or "Done."
            elif name == "flight_finder":
                r = await loop.run_in_executor(None, lambda: flight_finder(parameters=args, player=self.ui))
                result = r or "Done."
            elif name == "toggle_screen_share":
                result = await self._handle_toggle_screen_share(args)
            elif name == "interact_ui":
                result = await self._handle_interact_ui(args)
            elif name == "shutdown_jarvis":
                result = await self._handle_shutdown_jarvis(args)
            else:
                result = f"Unknown tool: {name}"
        except Exception as e:
            result = f"Tool '{name}' failed: {e}"
            traceback.print_exc()
            self.speak_error(name, e)

        if not self.ui.muted:
            self.ui.set_state("LISTENING")

        print(f"[JARVIS][legacy] 📤 {name} → {str(result)[:80]}")
        return types.FunctionResponse(id=fc.id, name=name, response={"result": result})

    async def _send_realtime(self):
        while True:
            msg = await self.out_queue.get()
            await self.session.send_realtime_input(media=msg)

    async def _listen_audio(self):
        print("[JARVIS] 🎤 Mic started")
        loop = asyncio.get_event_loop()

        def callback(indata, frames, time_info, status):
            with self._speaking_lock:
                jarvis_speaking = self._is_speaking
            if not jarvis_speaking and not self.ui.muted:
                data = indata.tobytes()
                loop.call_soon_threadsafe(
                    self.out_queue.put_nowait, {"data": data, "mime_type": "audio/pcm"}
                )

        try:
            with sd.InputStream(
                samplerate=SEND_SAMPLE_RATE,
                channels=CHANNELS,
                dtype="int16",
                blocksize=CHUNK_SIZE,
                callback=callback,
            ):
                print("[JARVIS] 🎤 Mic stream open")
                while True:
                    await asyncio.sleep(0.1)
        except Exception as e:
            print(f"[JARVIS] ❌ Mic: {e}")
            raise

    async def _receive_audio(self):
        print("[JARVIS] 👂 Recv started")
        out_buf, in_buf = [], []

        try:
            while True:
                async for response in self.session.receive():

                    if response.data:
                        if self._turn_done_event and self._turn_done_event.is_set():
                            self._turn_done_event.clear()
                        self.audio_in_queue.put_nowait(response.data)

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
                            in_buf = []

                            full_out = " ".join(out_buf).strip()
                            if full_out:
                                self.ui.write_log(f"Jarvis: {full_out}")
                            out_buf = []

                    if response.tool_call:
                        fn_responses = []
                        for fc in response.tool_call.function_calls:
                            print(f"[JARVIS] 📞 {fc.name}")
                            fr = await self._execute_tool(fc)
                            fn_responses.append(fr)
                        await self.session.send_tool_response(
                            function_responses=fn_responses
                        )
        except Exception as e:
            print(f"[JARVIS] ❌ Recv: {e}")
            traceback.print_exc()
            raise

    async def _play_audio(self):
        print("[JARVIS] 🔊 Play started")

        stream = sd.RawOutputStream(
            samplerate=RECEIVE_SAMPLE_RATE,
            channels=CHANNELS,
            dtype="int16",
            blocksize=CHUNK_SIZE,
        )
        stream.start()

        try:
            while True:
                try:
                    chunk = await asyncio.wait_for(
                        self.audio_in_queue.get(), timeout=0.1
                    )
                except asyncio.TimeoutError:
                    if (
                        self._turn_done_event
                        and self._turn_done_event.is_set()
                        and self.audio_in_queue.empty()
                    ):
                        self.set_speaking(False)
                        self._turn_done_event.clear()
                    continue
                self.set_speaking(True)
                await asyncio.to_thread(stream.write, chunk)
        except Exception as e:
            print(f"[JARVIS] ❌ Play: {e}")
            raise
        finally:
            self.set_speaking(False)
            stream.stop()
            stream.close()

    async def _poll_notifications_loop(self):
        print("[JARVIS] 🔔 Notification polling loop started")
        while True:
            try:
                if self.notification_manager.initialized and self.session:
                    new_notifs = (
                        await self.notification_manager.poll_new_notifications()
                    )
                    if new_notifs:
                        for notif in new_notifs:
                            app = notif["app"]
                            title = notif["title"]
                            body = notif["body"]

                            prompt = (
                                f"[NOTIFICATION SYSTEM ALERT]\n"
                                f"Application: {app}\n"
                                f"Sender/Title: {title}\n"
                                f"Message: {body}\n\n"
                                f"Decide how to respond to this notification based on the notification configuration. Call `send_message` to reply to the sender if appropriate, or speak to the user, or ignore if ignored."
                            )
                            print(
                                f"[JARVIS] 🔔 New notification from {app}: {title} - {body}"
                            )
                            self.ui.write_log(f"[notif] {app}: {title}")

                            await self.session.send_client_content(
                                turns={"parts": [{"text": prompt}]}, turn_complete=True
                            )
            except Exception as e:
                print(f"[JARVIS] Error in notification polling loop: {e}")
            await asyncio.sleep(1.5)

    async def _screen_share_loop(self):
        print("[JARVIS] 👁️ Screen share loop started")
        while True:
            try:
                if self.screen_share_active and self.session:
                    # Capture frame in thread
                    frame_bytes = await self._loop.run_in_executor(
                        None,
                        lambda: self.screen_share_worker.capture_frame(
                            self.ui_inspector
                        ),
                    )

                    if frame_bytes:
                        await self.session.send_realtime_input(
                            media={"mime_type": "image/jpeg", "data": frame_bytes}
                        )

                        # Also send UI Context
                        elements = await self._loop.run_in_executor(
                            None, self.ui_inspector.get_active_window_elements
                        )
                        context_str = await self._loop.run_in_executor(
                            None, lambda: self.ui_inspector.to_context_string(elements)
                        )

                        if (
                            context_str
                            and context_str != "[No interactive elements detected]"
                        ):
                            await self.session.send_client_content(
                                turns={"parts": [{"text": context_str}]},
                                turn_complete=True,
                            )
            except Exception as e:
                print(f"[JARVIS] ⚠️ Error in screen_share_loop: {e}")
            await asyncio.sleep(self.screen_share_worker.active and 1.5 or 3.0)

    def _collect_autonomy_alerts(self) -> list[str]:
        alerts = []
        for idea in self.autonomy_manager.get_all_ideas():
            if idea.error_message:
                alerts.append(f"Idea {idea.id} failed: {idea.error_message}")
            elif idea.priority == IdeaPriority.CRITICAL and idea.status in {
                IdeaStatus.PENDING,
                IdeaStatus.WAITING_DEPENDENCIES,
            }:
                alerts.append(
                    f"Critical idea {idea.id} is still pending with description: {idea.description}"
                )

        return alerts

    async def _context_awareness_loop(self):
        print("[JARVIS] 🌐 Context awareness loop started")
        while True:
            try:
                if self.session:
                    window_info = await self._loop.run_in_executor(
                        None, self.ui_inspector.get_active_window_info
                    )
                    active_window = window_info.get("title", "")
                    self.context_engine.record_context(active_window)
                    suggestion = self.context_engine.generate_suggestion()
                    if suggestion:
                        # Display suggestion in UI instead of terminal
                        try:
                            if self.ui:
                                self.ui.write_log(f"[🌟 Context] {suggestion}")
                        except Exception as e:
                            print(
                                f"[JARVIS] ⚠️ Failed to display context suggestion: {e}"
                            )
                    await asyncio.sleep(5.0)
                    continue

                # Respect enabled state
                if not self.autonomy_manager.enabled:
                    await asyncio.sleep(5.0)
                    continue

                alerts = self._collect_autonomy_alerts()
                if alerts:
                    text = "\n".join(alerts[:5])
                    print(f"[JARVIS] ⚠️ Autonomy alerts:\n{text}")
                    if self.session:
                        # Do not auto-send autonomy alerts to the model; surface to UI instead.
                        try:
                            if self.ui:
                                self.ui.write_log(f"[Autonomy alert] {text}")
                        except Exception as e:
                            print(f"[JARVIS] ⚠️ Failed to display autonomy alert: {e}")
                await asyncio.sleep(10.0)
            except Exception as e:
                print(f"[JARVIS] ⚠️ Error in autonomy loop: {e}")
                await asyncio.sleep(5.0)

    async def run(self):
        client = genai.Client(
            api_key=_get_api_key(), http_options={"api_version": "v1alpha"}
        )

        # Errors that should NOT trigger a reconnect — they require user action.
        _FATAL_PATTERNS = (
            "UNAUTHENTICATED",
            "API_KEY_INVALID",
            "PERMISSION_DENIED",
            "INVALID_ARGUMENT",
            "API_KEY_EXPIRED",
        )
        MAX_RECONNECT = 5
        reconnect_count = 0

        while reconnect_count < MAX_RECONNECT:
            try:
                print("[JARVIS] 🔌 Connecting...")
                self.ui.set_state("THINKING")
                config = self._build_config()

                try:
                    async with (
                        client.aio.live.connect(
                            model=LIVE_MODEL, config=config
                        ) as session,
                        asyncio.TaskGroup() as tg,
                    ):
                        self.session = session
                        self._loop = asyncio.get_event_loop()
                        self.audio_in_queue = asyncio.Queue()
                        self.out_queue = asyncio.Queue(maxsize=10)
                        self._turn_done_event = asyncio.Event()

                        print("[JARVIS] ✅ Connected.")
                        self.ui.set_state("LISTENING")
                        self.ui.write_log("SYS: JARVIS online.")
                        reconnect_count = 0  # reset counter on successful connection

                        # Initialize notification listener if allowed
                        await self.notification_manager.initialize()
                        await self.autonomy_manager.start()

                        self.hotkey_listener.start()

                        tg.create_task(self._send_realtime())
                        tg.create_task(self._listen_audio())
                        tg.create_task(self._receive_audio())
                        tg.create_task(self._play_audio())
                        tg.create_task(self._poll_notifications_loop())
                        tg.create_task(self._screen_share_loop())
                        # tg.create_task(self._context_awareness_loop())
                finally:
                    await self.autonomy_manager.stop()
            except Exception as e:
                error_str = str(e).upper()
                if any(p in error_str for p in _FATAL_PATTERNS):
                    msg = f"SYS: Fatal error — {e}. Check your API key and restart JARVIS."
                    print(f"[JARVIS] 💀 {msg}")
                    self.ui.write_log(msg)
                    self.ui.set_state("ERROR")
                    return  # do not reconnect on fatal auth/permission errors

                reconnect_count += 1
                wait = min(3.0 * reconnect_count, 30.0)
                msg = (
                    f"SYS: Connection error ({e}). "
                    f"Reconnecting in {wait:.0f}s "
                    f"(attempt {reconnect_count}/{MAX_RECONNECT})..."
                )
                print(f"[JARVIS] ❌ {msg}")
                traceback.print_exc()
                self.ui.write_log(msg)
                await asyncio.sleep(wait)

        final_msg = (
            f"SYS: Reached max reconnection attempts ({MAX_RECONNECT}). "
            "Please restart JARVIS."
        )
        print(f"[JARVIS] 🛑 {final_msg}")
        self.ui.write_log(final_msg)
        self.ui.set_state("ERROR")
