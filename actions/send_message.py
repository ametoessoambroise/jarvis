import json
import subprocess
import sys
import time
import uuid
from pathlib import Path

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

try:
    from actions.send_message_utils import generate_tts, convert_audio, download_file
    from actions.image_utils import prepare_sticker

    _MEDIA_UTILS = True
except Exception:
    _MEDIA_UTILS = False


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
            for launcher in [
                ["gtk-launch", app_name.lower()],
                [app_name.lower()],
            ]:
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
        print(f"[SendMessage] ⚠️ Could not open {app_name}: {e}")
        return False


def _open_browser_url(url: str) -> bool:
    import webbrowser

    try:
        webbrowser.open(url)
        time.sleep(4.0)
        return True
    except Exception as e:
        print(f"[SendMessage] ⚠️ Could not open browser: {e}")
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


def _capture_whatsapp_chat_history(receiver: str) -> str:
    """Open WhatsApp, select the chat with the receiver, and copy the latest messages."""
    _require_pyautogui()
    if not _open_app("WhatsApp"):
        return ""

    time.sleep(2.0)
    _search_in_app(receiver)
    pyautogui.press("enter")
    time.sleep(1.5)

    try:
        os_name = settings.get_os()
        select_all = ("command", "a") if os_name == "mac" else ("ctrl", "a")
        pyautogui.hotkey(*select_all)
        time.sleep(0.25)
        history_text = _copy_selection_to_clipboard()
        return history_text or ""
    except Exception as e:
        print(f"[SendMessage] ⚠️ Could not capture WhatsApp chat history: {e}")
        return ""


def _summarize_chat_history(history_text: str, max_lines: int = 20) -> str:
    if not history_text:
        return ""
    lines = [line.strip() for line in history_text.splitlines() if line.strip()]
    if not lines:
        return ""
    return "\n".join(lines[-max_lines:])


def _desktop_send(
    app_name: str, receiver: str, message: str, chat_ready: bool = False
) -> str:
    if not chat_ready and not _open_app(app_name):
        return f"Could not open {app_name}."

    if not chat_ready:
        time.sleep(1.0)
        _search_in_app(receiver)
        pyautogui.press("enter")
        time.sleep(0.8)
    else:
        time.sleep(0.8)

    _paste_text(message)
    time.sleep(0.2)
    pyautogui.press("enter")
    time.sleep(0.3)
    return f"Message sent to {receiver} via {app_name}."


def _open_attachment_dialog() -> bool:
    _require_pyautogui()
    # Most desktop messaging apps use Ctrl+O to attach a file.
    pyautogui.hotkey("ctrl", "o")
    time.sleep(1.0)
    return True


def _attach_file(path: str) -> bool:
    if not _open_attachment_dialog():
        return False
    _paste_text(path)
    time.sleep(0.4)
    pyautogui.press("enter")
    time.sleep(1.2)
    return True


def _ensure_attachment_path(item: dict, temp_dir: Path) -> Path:
    item_type = item.get("type", "document").lower().strip()
    path_value = item.get("path")
    url_value = item.get("url")
    tts_flag = item.get("tts", False)
    mime_hint = item.get("mime")

    if url_value and not path_value:
        download_path = temp_dir / f"download_{uuid.uuid4().hex}"
        suffix = Path(url_value).suffix or ""
        if not suffix:
            suffix = ".bin"
        download_path = download_path.with_suffix(suffix)
        download_file(url_value, str(download_path))
        path_value = str(download_path)

    if not path_value and item_type == "audio" and tts_flag:
        if not item.get("caption"):
            raise ValueError(
                "TTS audio requires caption text or message_text to generate audio."
            )
        output_path = temp_dir / f"tts_{uuid.uuid4().hex}.mp3"
        return Path(
            generate_tts(item.get("caption"), str(output_path), lang="fr", format="mp3")
        )

    if not path_value:
        raise ValueError("Attachment must include a local path or URL.")

    path = Path(path_value)
    if not path.exists():
        raise FileNotFoundError(f"Attachment file not found: {path}")

    if item_type == "sticker":
        sticker_path = temp_dir / f"sticker_{uuid.uuid4().hex}.webp"
        return Path(prepare_sticker(str(path), str(sticker_path)))

    if item_type == "audio" and mime_hint and "wav" in mime_hint.lower():
        target_path = temp_dir / f"audio_{uuid.uuid4().hex}.wav"
        return Path(convert_audio(str(path), str(target_path), format="wav"))

    return path


def _send_with_attachments(
    app_name: str,
    receiver: str,
    message: str,
    attachments: list[dict],
    chat_ready: bool = False,
) -> str:
    if not _MEDIA_UTILS:
        return "Media utilities are not available; cannot prepare attachments."

    temp_dir = settings.paths.root / "temp" / "send_message"
    temp_dir.mkdir(parents=True, exist_ok=True)
    attachment_paths = []

    try:
        for attachment in attachments:
            attachment_paths.append(_ensure_attachment_path(attachment, temp_dir))
    except Exception as e:
        return f"Could not prepare attachments: {e}"

    if not chat_ready and not _open_app(app_name):
        return f"Could not open {app_name}."

    if not chat_ready:
        time.sleep(1.0)
        _search_in_app(receiver)
        pyautogui.press("enter")
        time.sleep(0.8)
    else:
        time.sleep(0.8)

    for attachment_path in attachment_paths:
        if not _attach_file(str(attachment_path)):
            return f"Could not attach {attachment_path}."

    if message:
        _paste_text(message)
        time.sleep(0.2)
    pyautogui.press("enter")
    time.sleep(0.5)
    return f"Sent {len(attachment_paths)} attachment(s) to {receiver} via {app_name}."


def _send_whatsapp(
    receiver: str,
    message: str,
    attachments: list[dict] | None = None,
    chat_ready: bool = False,
) -> str:
    if attachments:
        return _send_with_attachments(
            "WhatsApp", receiver, message, attachments, chat_ready=chat_ready
        )

    return _desktop_send("WhatsApp", receiver, message, chat_ready=chat_ready)


def _send_telegram(
    receiver: str,
    message: str,
    attachments: list[dict] | None = None,
    chat_ready: bool = False,
) -> str:
    if attachments:
        return _send_with_attachments(
            "Telegram", receiver, message, attachments, chat_ready=chat_ready
        )
    return _desktop_send("Telegram", receiver, message, chat_ready=chat_ready)


def _send_signal(
    receiver: str,
    message: str,
    attachments: list[dict] | None = None,
    chat_ready: bool = False,
) -> str:
    if attachments:
        return _send_with_attachments(
            "Signal", receiver, message, attachments, chat_ready=chat_ready
        )
    return _desktop_send("Signal", receiver, message, chat_ready=chat_ready)


def _send_discord(
    receiver: str,
    message: str,
    attachments: list[dict] | None = None,
    chat_ready: bool = False,
) -> str:
    if attachments:
        return _send_with_attachments(
            "Discord", receiver, message, attachments, chat_ready=chat_ready
        )
    return _desktop_send("Discord", receiver, message, chat_ready=chat_ready)


def _send_instagram(
    receiver: str,
    message: str,
    attachments: list[dict] | None = None,
    chat_ready: bool = False,
) -> str:
    if attachments:
        return _send_with_attachments(
            "Instagram", receiver, message, attachments, chat_ready=chat_ready
        )

    _require_pyautogui()

    if not _open_browser_url("https://www.instagram.com/direct/new/"):
        return "Could not open Instagram in browser."

    _paste_text(receiver)
    time.sleep(1.5)

    pyautogui.press("down")
    time.sleep(0.3)
    pyautogui.press("enter")
    time.sleep(0.4)

    for _ in range(4):
        pyautogui.press("tab")
        time.sleep(0.15)
    pyautogui.press("enter")
    time.sleep(2.0)

    _paste_text(message)
    time.sleep(0.2)
    pyautogui.press("enter")
    time.sleep(0.3)

    return f"Message sent to {receiver} via Instagram."


_PLATFORM_MAP = [
    ({"whatsapp", "wp", "wapp"}, _send_whatsapp),
    ({"telegram", "tg"}, _send_telegram),
    ({"instagram", "ig", "insta"}, _send_instagram),
    ({"signal"}, _send_signal),
    ({"discord"}, _send_discord),
]


def _resolve_platform(platform_str: str):
    key = platform_str.lower().strip()
    for keywords, handler in _PLATFORM_MAP:
        if any(k in key for k in keywords):
            return handler
    return lambda r, m, attachments=None, chat_ready=False: _desktop_send(
        platform_str.strip().title(), r, m, chat_ready=chat_ready
    )


def send_message(
    parameters: dict,
    response=None,
    player=None,
    session_memory=None,
) -> str:
    params = parameters or {}
    receiver = params.get("receiver", "").strip()
    message_text = params.get("message_text", "").strip()
    platform = params.get("platform", "whatsapp").strip()
    attachments = params.get("attachments") or []

    if not receiver:
        return "Please specify a recipient."
    if not message_text and not attachments:
        return "Please specify the message content or at least one attachment."
    if not _PYAUTOGUI:
        return "PyAutoGUI is not installed — cannot control the desktop."

    preview = message_text[:50] + ("…" if len(message_text) > 50 else "")
    print(f"[SendMessage] 📨 {platform} → {receiver}: {preview}")
    if player:
        player.write_log(f"[msg] {platform} → {receiver}")

    chat_ready = bool(params.get("chat_ready", False))
    try:
        handler = _resolve_platform(platform)
        result = handler(
            receiver,
            message_text,
            attachments if attachments else None,
            chat_ready=chat_ready,
        )
    except Exception as e:
        result = f"Could not send message: {e}"

    print(
        f"[SendMessage] {'✅' if 'sent' in result.lower() or 'attachment' in result.lower() else '❌'} {result}"
    )
    if player:
        player.write_log(f"[msg] {result}")

    return result
