from __future__ import annotations

from typing import Any


def manage_autonomy(parameters: dict[str, Any], response=None, player=None, jarvis=None) -> str:
    action = (parameters.get("action") or "").strip().lower()
    state = (parameters.get("state") or "").strip().lower()
    sensitivity = parameters.get("sensitivity")
    reason = parameters.get("reason") or ""

    if jarvis is None or not hasattr(jarvis, "autonomy_manager"):
        return "Autonomy manager is not available in the current session."

    manager = jarvis.autonomy_manager

    if action in {"disable", "off"} or state == "off":
        return manager.disable()

    if action in {"enable", "on"} or state == "on":
        return manager.enable()

    if action == "status":
        status = manager.get_status()
        return (
            f"Autonomy status: {'enabled' if status['enabled'] else 'disabled'}. "
            f"Sensitivity={status['sensitivity']}. "
            f"Ideas={status['ideas_count']}. "
            f"Active agents={status['active_agents']}. "
            f"Pending ideas={status['pending_ideas']}."
        )

    if action == "set_sensitivity":
        if sensitivity is None:
            return "Please provide a sensitivity value between 1 and 10."
        try:
            level = int(sensitivity)
        except (ValueError, TypeError):
            return "Sensitivity must be an integer between 1 and 10."
        return manager.set_sensitivity(level)

    return (
        "Unknown manage_autonomy action. Use enable, disable, status, or set_sensitivity."
    )
