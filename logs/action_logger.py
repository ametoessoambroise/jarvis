"""
Action Logger — persists every screen-interaction action to a JSONL file
with timestamp, coordinates, result and a small post-action thumbnail.
"""

from __future__ import annotations

import base64
import json
import time
from io import BytesIO
from pathlib import Path

try:
    import mss
    _MSS = True
except ImportError:
    _MSS = False

try:
    from PIL import Image
    _PIL = True
except ImportError:
    _PIL = False

from core.utils import BASE_DIR

LOG_FILE = BASE_DIR / "logs" / "action_history.jsonl"
AUTONOMY_AUDIT_FILE = BASE_DIR / "logs" / "autonomy_audit.jsonl"


class ActionLogger:
    """Append-only JSONL logger for screen interaction actions and autonomy audit events."""

    def __init__(self):
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        AUTONOMY_AUDIT_FILE.parent.mkdir(parents=True, exist_ok=True)

    def log(
        self,
        action_type: str,
        target: dict,
        value: str = "",
        success: bool = True,
    ) -> None:
        entry = {
            "timestamp":   time.strftime("%Y-%m-%dT%H:%M:%S"),
            "action":      action_type,
            "target_name": target.get("name", ""),
            "target_coords": {
                "x": target.get("x"),
                "y": target.get("y"),
            },
            "value":   value if action_type == "type" else None,
            "success": success,
        }

        try:
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception as e:
            print(f"[ActionLogger] ⚠️  write failed: {e}")

    def log_autonomy(
        self,
        action_type: str,
        reason: str,
        details: dict | None = None,
        success: bool = True,
        metadata: dict | None = None,
    ) -> None:
        """Append an autonomy audit entry to the dedicated JSONL audit log."""
        entry = {
            "timestamp":   time.strftime("%Y-%m-%dT%H:%M:%S"),
            "action":      action_type,
            "reason":      reason,
            "details":     details or {},
            "success":     success,
            "metadata":    metadata or {},
        }

        try:
            with open(AUTONOMY_AUDIT_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception as e:
            print(f"[ActionLogger] ⚠️  autonomy audit write failed: {e}")

    # ── Optional thumbnail capture (disabled by default to save disk) ─

    @staticmethod
    def _capture_thumbnail_b64() -> str:
        if not _MSS or not _PIL:
            return ""
        try:
            with mss.mss() as sct:
                mon = sct.monitors[1] if len(sct.monitors) > 1 else sct.monitors[0]
                raw = sct.grab(mon)
                img = Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")
                img = img.resize((320, 180), Image.LANCZOS)
                buf = BytesIO()
                img.save(buf, format="JPEG", quality=25)
                return base64.b64encode(buf.getvalue()).decode()
        except Exception:
            return ""
