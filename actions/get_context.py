"""Get context tool — captures chat history from messaging apps like WhatsApp."""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from config import settings

try:
    import pyautogui

    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 0.06
    _PYAUTOGUI = True
except ImportError:
    _PYAUTOGUI = False

try:
    import pyperclip

    _PYPERCLIP = True
except ImportError:
    _PYPERCLIP = False


def _require_pyautogui():
    if not _PYAUTOGUI:
        raise RuntimeError("PyAutoGUI not installed. Run: pip install pyautogui")


def _paste_text(text: str) -> None:
    _require_pyautogui()
    os_name = settings.get_os()
    paste_hotkey = ("command", "v") if os_name == "mac" else ("ctrl", "v")

    if _PYPERCLIP:
        pyperclip.copy(text)
        time.sleep(0.15)
        pyautogui.hotkey(*paste_hotkey)
        time.sleep(0.1)
    else:
        pyautogui.write(text, interval=0.03)


def _clear_and_paste(text: str) -> None:
    _require_pyautogui()
    os_name = settings.get_os()
    select_all = ("command", "a") if os_name == "mac" else ("ctrl", "a")
    pyautogui.hotkey(*select_all)
    time.sleep(0.1)
    pyautogui.press("delete")
    time.sleep(0.1)
    _paste_text(text)


def _open_app(app_name: str) -> bool:
    _require_pyautogui()
    os_name = settings.get_os()

    try:
        if os_name == "windows":
            pyautogui.press("win")
            time.sleep(0.5)
            _paste_text(app_name)
            time.sleep(0.6)
            pyautogui.press("enter")
            time.sleep(2.5)
            return True
        elif os_name == "mac":
            result = subprocess.run(
                ["open", "-a", app_name],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode != 0:
                result = subprocess.run(
                    ["open", "-a", f"{app_name}.app"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
            time.sleep(2.5)
            return result.returncode == 0
        else:
            launched = False
            for launcher in [["gtk-launch", app_name.lower()], [app_name.lower()]]:
                try:
                    subprocess.Popen(
                        launcher,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                    launched = True
                    break
                except FileNotFoundError:
                    continue
            time.sleep(2.5)
            return launched
    except Exception as e:
        print(f"[GetContext] ⚠️ Could not open {app_name}: {e}")
        return False


def _search_in_app(query: str) -> None:
    _require_pyautogui()
    os_name = settings.get_os()
    search_hotkey = ("command", "f") if os_name == "mac" else ("ctrl", "f")
    pyautogui.hotkey(*search_hotkey)
    time.sleep(0.5)
    _clear_and_paste(query)
    time.sleep(1.0)


def _copy_selection_to_clipboard() -> str:
    _require_pyautogui()
    if not _PYPERCLIP:
        raise RuntimeError("Pyperclip is required to copy chat history.")

    os_name = settings.get_os()
    copy_hotkey = ("command", "c") if os_name == "mac" else ("ctrl", "c")
    pyautogui.hotkey(*copy_hotkey)
    time.sleep(0.25)
    return pyperclip.paste()


def _capture_whatsapp_context(contact: str) -> str:
    """Open WhatsApp, navigate to contact, and capture the latest messages."""
    _require_pyautogui()
    if not _open_app("WhatsApp"):
        return "ERROR: Could not open WhatsApp."

    time.sleep(2.0)
    _search_in_app(contact)
    pyautogui.press("enter")
    time.sleep(2.0)  # Wait for chat to load

    try:
        # Try to capture chat by clicking in the chat area and selecting text
        # Click in the chat area to ensure focus
        pyautogui.click(640, 400)  # Approximate center of chat area
        time.sleep(0.3)

        # Scroll to top to capture full history
        for _ in range(5):
            pyautogui.scroll(10)  # Scroll up
            time.sleep(0.2)

        time.sleep(0.5)

        os_name = settings.get_os()
        select_all = ("command", "a") if os_name == "mac" else ("ctrl", "a")
        pyautogui.hotkey(*select_all)
        time.sleep(0.5)

        history_text = _copy_selection_to_clipboard()

        if history_text and len(history_text) > 10:
            print(f"[GetContext] ✅ Captured {len(history_text)} chars from {contact}")
            return history_text
        else:
            print(
                f"[GetContext] ⚠️ Capture returned empty or minimal text for {contact}"
            )
            return "ERROR: Could not capture messages. The chat may be empty or selection failed."

    except Exception as e:
        print(f"[GetContext] ❌ Exception capturing context: {e}")
        return f"ERROR: {e}"


def _capture_telegram_context(contact: str) -> str:
    """Open Telegram, navigate to contact, and capture recent messages."""
    _require_pyautogui()
    if not _open_app("Telegram"):
        return "ERROR: Could not open Telegram."

    time.sleep(2.0)
    _search_in_app(contact)
    pyautogui.press("enter")
    time.sleep(1.5)

    try:
        os_name = settings.get_os()
        select_all = ("command", "a") if os_name == "mac" else ("ctrl", "a")
        pyautogui.hotkey(*select_all)
        time.sleep(0.25)
        history_text = _copy_selection_to_clipboard()
        return history_text or "No messages captured."
    except Exception as e:
        print(f"[GetContext] ⚠️ Could not capture context: {e}")
        return f"ERROR: {e}"


def _summarize_context(context_text: str, max_lines: int = 20) -> str:
    """Summarize context by keeping the latest N lines."""
    if not context_text or context_text.startswith("ERROR"):
        return context_text
    lines = [line.strip() for line in context_text.splitlines() if line.strip()]
    if not lines:
        return "No context available."
    return "\n".join(lines[-max_lines:])


def get_context(
    parameters: dict[str, Any],
    response=None,
    player=None,
    session_memory=None,
) -> str:
    """
    Retrieve conversation context from a messaging app (WhatsApp, Telegram, etc.).

    Parameters:
      - app: The messaging app (whatsapp, telegram, etc.)
      - contact: The contact/person whose chat to retrieve
      - lines: Max number of lines to return (default 20)
    """
    app = (parameters.get("app") or "whatsapp").strip().lower()
    contact = (parameters.get("contact") or "").strip()
    lines = parameters.get("lines", 20)

    if not contact:
        return "ERROR: Please provide a contact name."

    try:
        lines = int(lines)
    except (ValueError, TypeError):
        lines = 20

    print(f"[GetContext] 📖 Capturing context from {app.capitalize()} for {contact}...")
    if player:
        player.write_log(f"[context] {app} → {contact}")

    # Dispatch to the appropriate app handler
    if app in {"whatsapp", "wa", "wapp"}:
        raw_context = _capture_whatsapp_context(contact)
    elif app in {"telegram", "tg"}:
        raw_context = _capture_telegram_context(contact)
    else:
        return f"ERROR: Unsupported app '{app}'. Supported: WhatsApp, Telegram."

    # Summarize and return structured payload
    summary = _summarize_context(raw_context, max_lines=lines)

    ok = True
    if not raw_context or (
        isinstance(raw_context, str) and raw_context.startswith("ERROR")
    ):
        ok = False

    payload = {
        "ok": ok,
        "app": app,
        "contact": contact,
        "summary": summary,
        "raw": raw_context,
        "chat_ready": ok,
    }

    if player:
        player.write_log(
            f"[context] {'✅' if ok else '❌'} {contact} context captured."
        )

    return payload
