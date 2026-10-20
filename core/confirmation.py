"""core/confirmation.py — Stopgap confirmation gating for sensitive actions (Phase 7).

Provides pre-execution confirmation for sensitive tools:
- send_message
- file_controller(delete | move outside safe roots)
- system_optimizer(kill_process)
- computer_settings(shutdown | restart | sleep | lock)
- manage_autonomy(enable)
- code_helper(run non-.py)

Returns ResultStatus.DECLINED / ErrorCode.CONFIRMATION_DECLINED upon refusal or timeout.

Architecture note
-----------------
This module lives in ``core/`` and must NOT import from ``ui/``.  The UI layer
(or ``main.py``) is responsible for registering a concrete confirmation handler
via ``set_confirmation_handler`` / ``register_ui_handler`` at startup.  This
keeps the dependency arrow pointing inward (ui → core, never core → ui).
"""

from __future__ import annotations

from typing import Callable

from config import settings

# ---------------------------------------------------------------------------
# Handler registry
# ---------------------------------------------------------------------------
# Either ``None`` (no UI registered yet) or a callable (description, timeout_s) -> bool.
# The ui/ layer (ScreenOverlay) or tests inject their implementation here.
_CUSTOM_HANDLER: Callable[[str, float], bool] | None = None


def set_confirmation_handler(handler: Callable[[str, float], bool] | None) -> None:
    """Register a confirmation handler callable (injected by ui/ or tests).

    Signature:  handler(description: str, timeout_s: float) -> bool
    """
    global _CUSTOM_HANDLER
    _CUSTOM_HANDLER = handler


# Alias kept for backwards-compat / ui integration readability
register_ui_handler = set_confirmation_handler


# ---------------------------------------------------------------------------
# Settings check
# ---------------------------------------------------------------------------

def is_confirmation_enabled() -> bool:
    """Check if critical action confirmation is enabled in settings."""
    cfg = settings.get_settings()
    # Also check legacy or nested privacy key if present
    privacy_cfg = cfg.get("privacy", {})
    if isinstance(privacy_cfg, dict) and "confirm_critical_actions" in privacy_cfg:
        return bool(privacy_cfg["confirm_critical_actions"])
    return bool(cfg.get("confirm_sensitive", True))


# ---------------------------------------------------------------------------
# Sensitivity classification
# ---------------------------------------------------------------------------

def is_sensitive_action(tool_name: str, params: dict) -> tuple[bool, str]:
    """Determines whether a tool call requires explicit user confirmation.

    Returns:
        (is_sensitive, human_readable_description)
    """
    if tool_name == "send_message":
        recipient = params.get("recipient") or params.get("to") or "recipient"
        return True, f"Send message to {recipient}"

    if tool_name == "file_controller":
        action = str(params.get("action", "")).lower()
        path = params.get("path", "")
        if action in ("delete", "delete_file", "delete_folder"):
            return True, f"Permanently delete '{path}'"
        if action in ("move", "copy"):
            dest = params.get("destination", "")
            return True, f"Move/copy '{path}' to '{dest}'"

    if tool_name == "system_optimizer":
        action = str(params.get("action", "")).lower()
        if action == "kill_process":
            # If dry_run is True, no real killing occurs
            dry_run = params.get("dry_run", True)
            if not dry_run:
                proc = params.get("process_name") or params.get("name") or "process"
                return True, f"Terminate process '{proc}'"

    if tool_name == "computer_settings":
        action = str(params.get("action", "")).lower()
        if action in ("shutdown", "restart", "sleep", "lock"):
            return True, f"Perform system action '{action}'"

    if tool_name == "manage_autonomy":
        action = str(params.get("action", "")).lower()
        if action == "enable":
            return True, "Enable autonomous execution mode"

    if tool_name == "code_helper":
        action = str(params.get("action", "")).lower()
        path = str(params.get("path", "")).lower()
        if action == "run" and path and not path.endswith(".py"):
            return True, f"Execute non-Python script '{path}'"

    return False, ""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def request_confirmation(
    description: str,
    timeout_s: float = 10.0,
    x: int = 500,
    y: int = 400,
) -> bool:
    """Request user confirmation before performing a sensitive action.

    Resolution order:
    1. If confirmation is disabled in settings → auto-approve (return True).
    2. If a handler has been registered (by ui/ or tests) → delegate to it.
    3. Otherwise → safe refusal (return False), and log a warning.

    NOTE: This function never imports from ``ui/`` directly.  The UI layer
    must call ``register_ui_handler`` at startup to wire up the overlay.
    """
    if not is_confirmation_enabled():
        return True

    if _CUSTOM_HANDLER is not None:
        try:
            return bool(_CUSTOM_HANDLER(description, timeout_s))
        except Exception as e:
            print(f"[Confirmation] ⚠️ Handler failed: {e}")
            return False

    # No handler registered — fail safe (deny by default)
    print(
        f"[Confirmation] ⚠️ No UI handler registered for '{description}' "
        "— action denied by default. Register a handler via "
        "core.confirmation.register_ui_handler() at startup."
    )
    return False
