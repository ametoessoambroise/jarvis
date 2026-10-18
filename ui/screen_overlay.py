"""
Screen Overlay — displays a visual marker on screen before Jarvis acts.
Uses a transparent tkinter Toplevel window rendered in a daemon thread.
"""

from __future__ import annotations

import threading
import time
import tkinter as tk


class ScreenOverlay:
    """Overlay that shows where Jarvis will click / type before executing."""

    def show_click_preview(
        self,
        x: int,
        y: int,
        label: str = "",
        duration: float = 1.2,
    ) -> None:
        """Show a targeting circle at (x, y) for *duration* seconds."""
        t = threading.Thread(
            target=self._render_marker,
            args=(x, y, label, duration),
            daemon=True,
        )
        t.start()
        time.sleep(0.25)  # let overlay appear before the action runs

    # ── Internal renderers ───────────────────────────────────────────

    @staticmethod
    def _render_marker(x: int, y: int, label: str, duration: float):
        try:
            root = tk.Tk()
            root.withdraw()

            size = 64
            top = tk.Toplevel(root)
            top.overrideredirect(True)
            top.attributes("-topmost", True)
            top.attributes("-transparentcolor", "white")
            top.configure(bg="white")
            top.geometry(f"{size}x{size}+{x - size // 2}+{y - size // 2}")

            canvas = tk.Canvas(
                top, width=size, height=size,
                bg="white", highlightthickness=0,
            )
            canvas.pack()

            # outer ring
            canvas.create_oval(4, 4, size - 4, size - 4,
                               outline="#00BFFF", width=3)
            # center dot
            r = 5
            mid = size // 2
            canvas.create_oval(mid - r, mid - r, mid + r, mid + r,
                               fill="#00BFFF", outline="")

            if label:
                canvas.create_text(
                    mid, size - 8,
                    text=label, fill="#00BFFF",
                    font=("Segoe UI", 7, "bold"),
                )

            root.after(int(duration * 1000), root.destroy)
            root.deiconify()
            root.mainloop()
        except Exception as e:
            print(f"[Overlay] ⚠️  render_marker: {e}")

    def confirm_action(
        self,
        x: int,
        y: int,
        description: str,
        timeout: float = 10.0,
    ) -> bool:
        """
        Show a confirmation popup for critical actions.
        Returns True if the user confirms within *timeout* seconds.
        """
        result = {"confirmed": False}
        event  = threading.Event()

        def _render():
            try:
                root = tk.Tk()
                root.title("JARVIS — Confirmation")
                root.attributes("-topmost", True)
                root.resizable(False, False)

                # Center near action point but keep on screen
                root.geometry(f"340x110+{max(0, x - 170)}+{max(0, y - 120)}")

                tk.Label(
                    root,
                    text=f"Action : {description}",
                    wraplength=310, pady=10,
                    font=("Segoe UI", 10),
                ).pack()

                frame = tk.Frame(root)
                frame.pack(pady=5)

                def on_confirm():
                    result["confirmed"] = True
                    root.destroy()
                    event.set()

                def on_cancel():
                    root.destroy()
                    event.set()

                tk.Button(
                    frame, text="✅ Exécuter", command=on_confirm,
                    bg="#00BFFF", fg="white", font=("Segoe UI", 9, "bold"),
                    padx=12, pady=4,
                ).pack(side="left", padx=10)

                tk.Button(
                    frame, text="❌ Annuler", command=on_cancel,
                    font=("Segoe UI", 9), padx=12, pady=4,
                ).pack(side="right", padx=10)

                # Auto-cancel after timeout
                root.after(int(timeout * 1000), lambda: (on_cancel() if not event.is_set() else None))
                root.mainloop()
            except Exception as e:
                print(f"[Overlay] ⚠️  confirm: {e}")
                event.set()

        threading.Thread(target=_render, daemon=True).start()
        event.wait(timeout=timeout + 2)
        return result["confirmed"]
