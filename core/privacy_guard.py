"""
Privacy Guard — blocks capture for sensitive apps, blurs password fields.
First layer of security for the screen-sharing pipeline.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Optional

try:
    from PIL import Image, ImageFilter
    _PIL = True
except ImportError:
    _PIL = False

from core.utils import BASE_DIR

_PROFILES_PATH = BASE_DIR / "config" / "app_profiles.json"

# ── Defaults (used when config file is missing) ──────────────────────

_DEFAULT_BLOCKED_PROCESSES = [
    "keepass.exe", "1password.exe", "bitwarden.exe", "lastpass.exe",
    "keychain", "signal.exe",
]

_DEFAULT_TITLE_PATTERNS = [
    r"mot de passe", r"password", r"connexion sécurisée",
    r"authentification", r"code pin", r"two.factor", r"2fa",
]


# ── Config loader ────────────────────────────────────────────────────

def _load_profiles() -> dict:
    try:
        if _PROFILES_PATH.exists():
            return json.loads(_PROFILES_PATH.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"[Privacy] ⚠️  Could not load app_profiles: {e}")
    return {}


# ── Public API ───────────────────────────────────────────────────────

def is_app_blacklisted(window_title: str, process_name: str) -> bool:
    """Return True if the active application should NOT be captured."""
    cfg = _load_profiles()
    blocked = cfg.get("blocked", {})
    blocked_procs = blocked.get("processes", _DEFAULT_BLOCKED_PROCESSES)
    title_pats    = blocked.get("title_patterns", _DEFAULT_TITLE_PATTERNS)

    proc_lower  = process_name.lower()
    title_lower = window_title.lower()

    for bp in blocked_procs:
        if bp.lower() in proc_lower:
            return True

    for pat in title_pats:
        if re.search(pat, title_lower, re.IGNORECASE):
            return True

    return False


def blur_sensitive_regions(
    image: "Image.Image",
    elements: list[dict],
) -> "Image.Image":
    """Blur password fields detected by the UI inspector."""
    if not _PIL or not elements:
        return image

    img = image.copy()
    for el in elements:
        if not el.get("is_password", False):
            continue
        try:
            cx, cy = el["x"], el["y"]
            w, h   = el.get("w", 120), el.get("h", 30)
            x1 = max(0, cx - w // 2)
            y1 = max(0, cy - h // 2)
            x2 = min(img.width,  x1 + w)
            y2 = min(img.height, y1 + h)
            region  = img.crop((x1, y1, x2, y2))
            blurred = region.filter(ImageFilter.GaussianBlur(radius=15))
            img.paste(blurred, (x1, y1))
        except Exception:
            pass
    return img


def apply_privacy_filter(
    image: "Image.Image",
    window_title: str,
    process_name: str,
    elements: list[dict],
) -> Optional["Image.Image"]:
    """
    Main entry point.
    Returns None if capture should be fully blocked, otherwise the filtered image.
    """
    if is_app_blacklisted(window_title, process_name):
        return None
    return blur_sensitive_regions(image, elements)
