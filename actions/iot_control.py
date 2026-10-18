"""IoT control action module for simple local smart device simulation."""

from __future__ import annotations

from typing import Any


SIMULATED_DEVICES: dict[str, dict[str, Any]] = {
    "living room light": {"status": "off", "level": 0, "type": "light"},
    "bedroom thermostat": {"status": "on", "level": 22, "type": "thermostat"},
    "office speaker": {"status": "off", "level": 50, "type": "speaker"},
}


def iot_control(parameters: dict[str, Any], response=None, player=None) -> str:
    action = (parameters.get("action") or "").strip().lower()
    device_name = (parameters.get("device") or "").strip().lower()
    value = parameters.get("value")
    level = parameters.get("level")

    def find_device(name: str) -> str | None:
        if not name:
            return None
        lower_name = name.lower()
        for device in SIMULATED_DEVICES:
            if lower_name == device.lower() or lower_name in device.lower():
                return device
        return None

    if action == "list_devices":
        devices = ", ".join(sorted(SIMULATED_DEVICES.keys()))
        return f"Simulated IoT devices: {devices}."

    if action == "status":
        if not device_name:
            return "Please provide a device name to query status." 
        device = find_device(device_name)
        if not device:
            return f"No simulated device matched '{device_name}'."
        state = SIMULATED_DEVICES[device]
        return f"{device}: status={state['status']}, level={state['level']}"

    if action in {"turn_on", "turn_off"}:
        if not device_name:
            return "Please provide a device to control." 
        device = find_device(device_name)
        if not device:
            return f"No simulated device matched '{device_name}'."
        SIMULATED_DEVICES[device]["status"] = "on" if action == "turn_on" else "off"
        if action == "turn_on" and SIMULATED_DEVICES[device]["type"] == "light" and SIMULATED_DEVICES[device]["level"] == 0:
            SIMULATED_DEVICES[device]["level"] = 100
        return f"{device} turned {'on' if action == 'turn_on' else 'off'}."

    if action == "set_level":
        if not device_name:
            return "Please provide a device to adjust." 
        device = find_device(device_name)
        if not device:
            return f"No simulated device matched '{device_name}'."
        try:
            level_value = int(level if level is not None else value)
        except (ValueError, TypeError):
            return "Please provide an integer level value for set_level."
        SIMULATED_DEVICES[device]["level"] = max(0, min(level_value, 100))
        if SIMULATED_DEVICES[device]["type"] == "light" and SIMULATED_DEVICES[device]["level"] > 0:
            SIMULATED_DEVICES[device]["status"] = "on"
        return f"{device} level set to {SIMULATED_DEVICES[device]['level']}."

    return (
        "Unknown IoT action. Use list_devices, status, turn_on, turn_off, or set_level."
    )
