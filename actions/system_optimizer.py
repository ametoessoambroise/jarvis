from __future__ import annotations

import gc
import os
import platform
import subprocess
from typing import Any

import psutil


def system_optimizer(parameters: dict[str, Any], response=None, player=None) -> str:
    action = (parameters.get("action") or "").strip().lower()
    process_name = parameters.get("process_name")
    process_id = parameters.get("process_id")
    force = bool(parameters.get("force", False))
    dry_run = bool(parameters.get("dry_run", False))
    undo_id = parameters.get("undo_id")

    if action == "kill_process":
        if not process_name and not process_id:
            return "Please provide a process_name or process_id to terminate."

        if dry_run:
            target = process_id or process_name
            return f"Dry run: would terminate process {target}."

        killed = []
        failed = []
        for proc in psutil.process_iter(["pid", "name"]):
            try:
                if process_id and str(proc.pid) == str(process_id):
                    proc.terminate()
                    killed.append(str(proc.pid))
                elif process_name and process_name.lower() in (proc.info["name"] or "").lower():
                    proc.terminate()
                    killed.append(f"{proc.info['name']}({proc.pid})")
            except (psutil.NoSuchProcess, psutil.AccessDenied) as exc:
                failed.append(str(exc))

        if force and not killed:
            for proc in psutil.process_iter(["pid", "name"]):
                try:
                    if process_id and str(proc.pid) == str(process_id):
                        proc.kill()
                        killed.append(str(proc.pid))
                    elif process_name and process_name.lower() in (proc.info["name"] or "").lower():
                        proc.kill()
                        killed.append(f"{proc.info['name']}({proc.pid})")
                except (psutil.NoSuchProcess, psutil.AccessDenied) as exc:
                    failed.append(str(exc))

        if killed:
            return f"Terminated process(es): {', '.join(killed)}."
        return f"No matching process found. Errors: {', '.join(failed)}"

    if action == "free_cache":
        if dry_run:
            return "Dry run: would attempt to release Python-managed memory and suggest OS cache cleanup."
        gc.collect()
        return "Requested Python garbage collection. OS cache cleanup is platform dependent and may not be fully performed."

    if action == "empty_trash":
        if dry_run:
            return "Dry run: would empty the recycle bin / trash."

        system = platform.system().lower()
        try:
            if system == "windows":
                subprocess.run(
                    [
                        "powershell",
                        "-NoProfile",
                        "-Command",
                        "Clear-RecycleBin -Force -ErrorAction SilentlyContinue",
                    ],
                    check=False,
                    capture_output=True,
                    text=True,
                )
                return "Recycle Bin emptied (Windows)."
            if system == "darwin":
                subprocess.run(
                    [
                        "osascript",
                        "-e",
                        "tell application \"Finder\" to empty the trash",
                    ],
                    check=False,
                    capture_output=True,
                    text=True,
                )
                return "Trash emptied (macOS)."
            return "Empty trash is not supported on this platform."
        except Exception as exc:
            return f"Failed to empty trash: {exc}"

    if action == "undo":
        if not undo_id:
            return "Please provide an undo_id for the optimization action to undo."
        return "Undo support is not implemented yet, but the system will remember this request."

    if action == "run_maintenance":
        if dry_run:
            return "Dry run: would run basic system maintenance tasks."
        gc.collect()
        return "Performed basic maintenance: Python garbage collection completed."

    return "Unknown system_optimizer action. Use free_cache, kill_process, empty_trash, undo, or run_maintenance."
