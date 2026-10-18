import asyncio
import os
import sys
import threading

from ui import JarvisUI
from core.jarvis_live import JarvisLive
from core.file_watcher import watch_and_restart


def run_jarvis(ui: JarvisUI):
    """Run the Jarvis instance inside a daemon thread."""

    def runner():
        ui.wait_for_api_key()
        jarvis = JarvisLive(ui)
        try:
            asyncio.run(jarvis.run())
        except KeyboardInterrupt:
            print("\n🔴 Shutting down...")

    thread = threading.Thread(target=runner, daemon=True)
    thread.start()
    ui.root.mainloop()


def main():
    watch_mode = "--watch" in sys.argv or "-w" in sys.argv

    if watch_mode:
        print("[JARVIS] 👁️  Running in WATCH mode. Code changes will auto-restart.")

        def restart_callback():
            """Replace the current process with a fresh copy — true hot-reload."""
            print("[JARVIS] ⚠️  Restarting process...")
            # os.execv replaces the running process image in-place,
            # preserving the same PID contract expected by the OS.
            os.execv(sys.executable, [sys.executable] + sys.argv)

        watcher_thread = threading.Thread(
            target=lambda: watch_and_restart(restart_callback, check_interval=2),
            daemon=False,
        )
        watcher_thread.start()

    ui = JarvisUI("face.png")
    run_jarvis(ui)


if __name__ == "__main__":
    main()
