"""JarvisLive — orchestration du moteur vocal et dispatch des outils.

Ce module orchestre les interactions temps réel, conserve les handlers
internes (mémoire, partage d'écran, UI, tâches) et délègue l'exécution des 26 outils
au tool_dispatcher centralisé sans aucun import direct vers actions/ ni ui/.

Références :
    TRD.md §3.2 (Cible V1)
    DEVELOPMENT_PHASES.md P4 (V1-LIVE-01, V1-LIVE-02)
    BACKEND_CONTRACT.md C-01, C-08, C-17
"""

from __future__ import annotations

import asyncio
import importlib
import threading
from typing import Any

from google.genai import types

from core.action_verifier import ActionVerifier
from core.audio_io import AudioIO
from core.autonomy_manager import AutonomyManager
from core.context_engine import ContextEngine
from core.hotkey_listener import HotkeyListener
from core.notification_manager import NotificationManager
from core.screen_share_worker import ScreenShareWorker
from core.session_manager import SessionManager
from core.tools import TOOL_DECLARATIONS
from core.ui_port import UiPort
from core.utils import BASE_DIR
from logs.action_logger import ActionLogger
from memory.memory_manager import update_memory


def _load_optional_component(dotted_path: str, *args, **kwargs) -> Any:
    """Charge un composant auxiliaire dynamiquement sans import statique."""
    try:
        module_path, class_name = dotted_path.rsplit(":", 1)
        mod = importlib.import_module(module_path)
        cls = getattr(mod, class_name)
        return cls(*args, **kwargs)
    except Exception as e:
        print(f"[JARVIS] ⚠️ Composant optionnel non chargé ({dotted_path}): {e}")
        return None


class JarvisLive:
    """Cœur applicatif supervisant les interactions vocales et les outils."""

    def __init__(self, ui: UiPort):
        self.ui = ui
        self._loop: asyncio.AbstractEventLoop | None = None
        self._is_speaking = False
        self._speaking_lock = threading.Lock()
        self.ui.on_text_command = self._on_text_command

        # Composants d'infrastructure core
        self.notification_manager = NotificationManager(BASE_DIR)
        self.screen_share_worker = ScreenShareWorker()
        self.action_verifier = ActionVerifier()
        self.logger = ActionLogger()
        self.autonomy_manager = AutonomyManager()
        self.context_engine = ContextEngine()
        self.screen_share_active = False

        # Composants chargés dynamiquement sans imports statiques interdits
        self.ui_inspector = _load_optional_component("actions.ui_inspector:UIInspector")
        self.browser_inspector = _load_optional_component("actions.browser_inspector:BrowserInspector")
        self.overlay = _load_optional_component("ui.screen_overlay:ScreenOverlay")
        self.tray = _load_optional_component("ui.tray_indicator:TrayIndicator", self._on_tray_stop_screen_share)
        self.hotkey_listener = HotkeyListener(self)

        # SessionManager délégué
        self.audio_io = AudioIO()
        self.session_manager = SessionManager(
            ui=self.ui,
            audio_io=self.audio_io,
            tool_executor=self._execute_tool,
            notification_manager=self.notification_manager,
            screen_share_worker=self.screen_share_worker,
            ui_inspector=self.ui_inspector,
            hotkey_listener=self.hotkey_listener,
        )

    @property
    def session(self) -> Any | None:
        return self.session_manager.session

    def _on_tray_stop_screen_share(self) -> None:
        self.screen_share_active = False
        self.session_manager.screen_share_active = False
        if self.tray and hasattr(self.tray, "hide"):
            self.tray.hide()
        self.screen_share_worker.reset()
        self.speak("Screen sharing stopped.")

    def _on_text_command(self, text: str) -> None:
        if not self._loop:
            self._loop = asyncio.get_event_loop()
        asyncio.run_coroutine_threadsafe(
            self.session_manager.send_text_command(text),
            self._loop,
        )

    def set_speaking(self, value: bool) -> None:
        with self._speaking_lock:
            self._is_speaking = value
        self.session_manager.set_speaking(value)

    def speak(self, text: str) -> None:
        """Envoie un message texte/vocal dans la session active."""
        self._on_text_command(text)

    def speak_error(self, tool_name: str, error: Any) -> None:
        short = str(error)[:120]
        self.ui.write_log(f"ERR: {tool_name} — {short}")
        self.speak(f"Sir, {tool_name} encountered an error. {short}")

    async def _execute_tool(self, fc) -> types.FunctionResponse:
        """Exécute un outil Gemini via le dispatcher centralisé ou un handler interne."""
        name = fc.name
        args = dict(fc.args or {})

        print(f"[JARVIS] 🔧 {name}  {args}")
        self.ui.set_state("THINKING")

        # ── Handlers internes ─────────────────────────────────────────────────
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
            internal_result = await self._handle_send_message(args)
        elif name == "file_processor":
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
        from core.tool_dispatcher import dispatch
        from core.tool_registry import _REGISTRY

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

    # ── Implémentation des Handlers internes ──────────────────────────────────

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
        from agent.task_queue import TaskPriority, get_queue

        action  = (args.get("action") or "submit").strip().lower()
        task_id = (args.get("task_id") or "").strip()
        queue   = get_queue()

        if action == "status":
            if not task_id:
                return "Please provide a task_id to check status."
            status = queue.get_status(task_id)
            if status is None:
                return f"No task found with ID '{task_id}'."
            return (
                f"Task [{task_id}] — status: {status['status']}. "
                f"Goal: {status['goal'][:80]}. "
                + (f"Result: {str(status['result'])[:120]}." if status['result'] else "")
                + (f" Error: {status['error'][:80]}." if status['error'] else "")
            )

        if action == "cancel":
            if not task_id:
                return "Please provide a task_id to cancel."
            success = queue.cancel(task_id)
            return (
                f"Task [{task_id}] cancelled." if success
                else f"Could not cancel task [{task_id}] — not found or already terminal."
            )

        if action == "list":
            statuses = queue.get_all_statuses()
            if not statuses:
                return "No tasks in the queue."
            lines = [f"• [{s['task_id']}] {s['status']:10s} — {s['goal']}" for s in statuses]
            return "Tasks:\n" + "\n".join(lines)

        # Default: submit
        priority_map = {
            "low":    TaskPriority.LOW,
            "normal": TaskPriority.NORMAL,
            "high":   TaskPriority.HIGH,
        }
        priority = priority_map.get(
            (args.get("priority") or "normal").lower(), TaskPriority.NORMAL
        )
        goal = args.get("goal", "").strip()
        if not goal:
            return "Please provide a goal for the task."
        new_id = queue.submit(goal=goal, priority=priority, speak=self.speak)
        return f"Task started (ID: {new_id})."


    async def _handle_toggle_screen_share(self, args: dict) -> str:
        state = args.get("state", "off").lower()
        if state == "on":
            self.screen_share_active = True
            self.session_manager.screen_share_active = True
            self.screen_share_worker.active = True
            if self.tray and hasattr(self.tray, "show_active"):
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

        if self.overlay and hasattr(self.overlay, "show_click_preview"):
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
            lambda: self.logger.log(
                action, {"x": x, "y": y, "name": elem_name}, val, success
            ),
        )
        return f"Action {action} at ({x},{y}) executed. Verified: {success}"

    async def _handle_shutdown_jarvis(self, args: dict) -> str:
        self.ui.write_log("SYS: Shutdown requested.")
        self.speak("Goodbye, sir.")

        async def _shutdown():
            await asyncio.sleep(1.0)
            await self.shutdown(grace_s=5.0)

        asyncio.create_task(_shutdown())
        return "Shutting down."

    async def _handle_screen_process(self, args: dict) -> str:
        from core.tool_dispatcher import dispatch
        from core.tool_registry import _REGISTRY

        spec = _REGISTRY.get("screen_process")
        if spec:
            threading.Thread(
                target=lambda: dispatch(spec, args, {"player": self.ui}),
                daemon=True,
            ).start()
        return "Vision module activated. Stay completely silent — vision module will speak directly."

    async def _handle_manage_autonomy(self, args: dict) -> str:
        from core.tool_dispatcher import dispatch
        from core.tool_registry import _REGISTRY

        loop = asyncio.get_event_loop()
        spec = _REGISTRY.get("manage_autonomy")
        if spec:
            res = await loop.run_in_executor(
                None, lambda: dispatch(spec, args, {"player": self.ui, "jarvis": self})
            )
            return res.message or "Autonomy settings updated."
        return "manage_autonomy tool not found."

    async def _handle_send_message(self, args: dict) -> str:
        from core.tool_dispatcher import dispatch
        from core.tool_registry import _REGISTRY

        loop = asyncio.get_event_loop()
        receiver = args.get("receiver") or args.get("contact") or args.get("to")
        platform = args.get("platform", "whatsapp")
        if receiver:
            try:
                ctx_spec = _REGISTRY.get("get_context")
                if ctx_spec:
                    ctx_args = {"contact": receiver, "app": platform}
                    ctx_res = await loop.run_in_executor(
                        None,
                        lambda: dispatch(ctx_spec, ctx_args, {"player": self.ui}),
                    )
                    if ctx_res and ctx_res.message:
                        self.ui.write_log(f"[GetContext] {ctx_res.message[:200]}")
            except Exception as e:
                self.ui.write_log(f"[GetContext] failed: {e}")

        spec = _REGISTRY.get("send_message")
        if spec:
            res = await loop.run_in_executor(
                None, lambda: dispatch(spec, args, {"player": self.ui})
            )
            return res.message or f"Message sent to {args.get('receiver')}."
        return "send_message tool not found."

    async def _handle_file_processor(self, args: dict) -> str:
        from core.tool_dispatcher import dispatch
        from core.tool_registry import _REGISTRY

        loop = asyncio.get_event_loop()
        if not args.get("file_path") and self.ui.current_file:
            args["file_path"] = self.ui.current_file

        spec = _REGISTRY.get("file_processor")
        if spec:
            res = await loop.run_in_executor(
                None,
                lambda: dispatch(spec, args, {"player": self.ui, "speak": self.speak}),
            )
            return res.message or "Done."
        return "file_processor tool not found."

    async def run(self) -> None:
        """Démarre la session Live en déléguant à SessionManager."""
        self._loop = asyncio.get_running_loop()
        await self.autonomy_manager.start()
        try:
            await self.session_manager.run()
        finally:
            await self.autonomy_manager.stop()

    async def shutdown(self, grace_s: float = 5.0) -> None:
        """Arrêt coopératif ordonné."""
        if self.tray and hasattr(self.tray, "hide"):
            try:
                self.tray.hide()
            except Exception:
                pass
        await self.session_manager.shutdown(grace_s=grace_s)
        await self.autonomy_manager.stop()
