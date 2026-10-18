import json
import os
import re
import sys
from pathlib import Path


def get_base_dir():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


BASE_DIR = get_base_dir()
API_CONFIG_PATH = BASE_DIR / "config" / "api_keys.json"
PROMPT_PATH = BASE_DIR / "core" / "prompt.txt"

# Audio configuration
LIVE_MODEL = "models/gemini-2.5-flash-native-audio-latest"
CHANNELS = 1
SEND_SAMPLE_RATE = 16000
RECEIVE_SAMPLE_RATE = 24000
CHUNK_SIZE = 1024


def _get_api_key() -> str:
    """Return the Gemini API key.

    Priority:
    1. GEMINI_API_KEY environment variable (recommended for production).
    2. config/api_keys.json fallback (local dev only — never commit this file).

    Raises RuntimeError with a clear message if no key can be found.
    """
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not key:
        try:
            with open(API_CONFIG_PATH, "r", encoding="utf-8") as f:
                key = json.load(f).get("gemini_api_key", "").strip()
        except FileNotFoundError:
            raise RuntimeError(
                "Gemini API key not found. "
                "Set the GEMINI_API_KEY environment variable or create config/api_keys.json."
            ) from None
        except (json.JSONDecodeError, OSError) as exc:
            raise RuntimeError(
                f"Could not read config/api_keys.json: {exc}. "
                "Set the GEMINI_API_KEY environment variable instead."
            ) from exc
    if not key:
        raise RuntimeError(
            "Gemini API key is empty. "
            "Set GEMINI_API_KEY or add 'gemini_api_key' to config/api_keys.json."
        )
    return key


def _load_system_prompt() -> str:
    try:
        return PROMPT_PATH.read_text(encoding="utf-8")
    except Exception:
        return (
            "You are JARVIS, Tony Stark's AI assistant. "
            "Be concise, direct, and always use the provided tools to complete tasks. "
            "Never simulate or guess results — always call the appropriate tool."
        )


_CTRL_RE = re.compile(r"<ctrl\d+>", re.IGNORECASE)


def _clean_transcript(text: str) -> str:
    text = _CTRL_RE.sub("", text)
    text = re.sub(r"[\x00-\x08\x0b-\x1f]", "", text)
    return text.strip()
