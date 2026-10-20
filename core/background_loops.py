"""Background loops — boucles asynchrones supervisées (notifications, partage d'écran).

Ce module extrait et isole les tâches de fond périodiques de JarvisLive
afin de découpler le cycle de vie de la session de la logique de fond.

Références :
    TRD.md §1.4, §3.2
    DEVELOPMENT_PHASES.md P4
    APP_FLOW.md F-19 (partage d'écran), F-15 (notifications)
"""

from __future__ import annotations

import asyncio
from typing import Any, Callable

from core.ui_port import UiPort


async def poll_notifications_loop(
    notification_manager: Any,
    get_session_fn: Callable[[], Any | None],
    ui: UiPort,
    poll_interval_s: float = 1.5,
) -> None:
    """Boucle asynchrone surveillant les notifications système reçues."""
    print("[JARVIS] 🔔 Notification polling loop started")
    while True:
        try:
            session = get_session_fn()
            if notification_manager and notification_manager.initialized and session:
                new_notifs = await notification_manager.poll_new_notifications()
                if new_notifs:
                    for notif in new_notifs:
                        app = notif.get("app", "App")
                        title = notif.get("title", "")
                        body = notif.get("body", "")

                        prompt = (
                            f"[NOTIFICATION SYSTEM ALERT]\n"
                            f"Application: {app}\n"
                            f"Sender/Title: {title}\n"
                            f"Message: {body}\n\n"
                            f"Decide how to respond to this notification based on the notification configuration. "
                            f"Call `send_message` to reply to the sender if appropriate, or speak to the user, or ignore if ignored."
                        )
                        print(f"[JARVIS] 🔔 New notification from {app}: {title} - {body}")
                        ui.write_log(f"[notif] {app}: {title}")

                        await session.send_client_content(
                            turns={"parts": [{"text": prompt}]}, turn_complete=True
                        )
        except Exception as e:
            print(f"[JARVIS] Error in notification polling loop: {e}")
        await asyncio.sleep(poll_interval_s)


async def screen_share_loop(
    screen_share_worker: Any,
    ui_inspector: Any,
    get_session_fn: Callable[[], Any | None],
    is_active_fn: Callable[[], bool],
    loop: asyncio.AbstractEventLoop,
) -> None:
    """Boucle asynchrone gérant la capture d'écran périodique avec filtre de confidentialité."""
    print("[JARVIS] 👁️ Screen share loop started")
    while True:
        try:
            session = get_session_fn()
            if is_active_fn() and session:
                # Capture frame in thread executor
                frame_bytes = await loop.run_in_executor(
                    None,
                    lambda: screen_share_worker.capture_frame(ui_inspector),
                )

                if frame_bytes:
                    await session.send_realtime_input(
                        media={"mime_type": "image/jpeg", "data": frame_bytes}
                    )

                    # UI Context
                    elements = await loop.run_in_executor(
                        None, ui_inspector.get_active_window_elements
                    )
                    context_str = await loop.run_in_executor(
                        None, lambda: ui_inspector.to_context_string(elements)
                    )

                    if context_str and context_str != "[No interactive elements detected]":
                        await session.send_client_content(
                            turns={"parts": [{"text": context_str}]},
                            turn_complete=True,
                        )
        except Exception as e:
            print(f"[JARVIS] ⚠️ Error in screen_share_loop: {e}")

        # Fréquence adaptée : 1.5s si actif, 3.0s sinon
        delay = 1.5 if (screen_share_worker and getattr(screen_share_worker, "active", False)) else 3.0
        await asyncio.sleep(delay)
