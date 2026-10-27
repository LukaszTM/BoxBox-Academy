"""Nakładka trenera: okno zawsze na wierzchu z okrążeniem, najbliższym zakrętem i słowami mechanika.

Telemetrię odbiera wątek w `boxbox.app` (jedno gniazdo UDP dla trenera i nakładki);
okno tylko czyta stan pod blokadą. Gra w trybie okna bez ramki, nie w pełnym ekranie.
"""
import tkinter as tk

from boxbox.ui.overlay import ACCENT, BG, CYAN, FG
from boxbox.ui.overlay_model import GUIDE_DIR, SharedCoachState, TrackGuide, build_coach_view, load_guide_for

class CoachOverlayWindow:
    def __init__(self, shared: SharedCoachState, scale: float = 1.0, alpha: float = 0.97) -> None:
        self.shared = shared
        self.guide: TrackGuide | None = None
        self.guide_track_id: int | None = None
        self.root = tk.Tk()
        self.root.title("BoxBox Academy - trener")
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        try:
            self.root.attributes("-alpha", alpha)
        except tk.TclError:
            pass
        self.root.configure(bg=ACCENT)
        self.root.geometry("+40+40")
        inner = tk.Frame(self.root, bg=BG)
        inner.pack(padx=3, pady=3, fill="both", expand=True)
        wrap = int(560 * scale)

        def font(size: int, bold: bool = False) -> tuple:
            return ("Segoe UI", int(size * scale), "bold") if bold else ("Segoe UI", int(size * scale))

        pad = {"padx": 16, "pady": 3, "anchor": "w"}
        self.l_lap = tk.Label(inner, text="", fg=FG, bg=BG, font=font(26, True))
        self.l_corner = tk.Label(inner, text="", fg=CYAN, bg=BG, font=font(34, True))
        self.l_msg = [
            tk.Label(inner, text="", fg=ACCENT, bg=BG, font=font(20, True), wraplength=wrap, justify="left"),
            tk.Label(inner, text="", fg="#d0d0d0", bg=BG, font=font(14), wraplength=wrap, justify="left"),
            tk.Label(inner, text="", fg="#9a9a9a", bg=BG, font=font(12), wraplength=wrap, justify="left"),
        ]
        self.l_progress = tk.Label(inner, text="", fg="#3ddc3d", bg=BG, font=font(12), wraplength=wrap, justify="left")
        self.l_status = tk.Label(inner, text="", fg="#b0b0b0", bg=BG, font=font(11), wraplength=wrap, justify="left")
        for w in (self.l_lap, self.l_corner, *self.l_msg, self.l_progress, self.l_status):
            w.pack(fill="x", **pad)
        tk.Label(inner, text="przeciągnij, aby przesunąć | Esc zamyka i kończy sesję", fg="#808080", bg=BG, font=font(9)).pack(fill="x", padx=16, pady=(2, 8), anchor="w")
        self._drag: tuple[int, int] | None = None
        self.root.bind("<ButtonPress-1>", self._drag_start)
        self.root.bind("<B1-Motion>", self._drag_move)
        self.root.bind("<Escape>", lambda _e: self.close())
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.closed = False

    def _drag_start(self, event: tk.Event) -> None:  # type: ignore[type-arg]
        self._drag = (event.x, event.y)

    def _drag_move(self, event: tk.Event) -> None:  # type: ignore[type-arg]
        if self._drag:
            x = self.root.winfo_x() + event.x - self._drag[0]
            y = self.root.winfo_y() + event.y - self._drag[1]
            self.root.geometry(f"+{x}+{y}")

    def refresh(self) -> None:
        sh = self.shared
        with sh.lock:
            state = sh.state
            if state.session is not None and state.session.track_id != self.guide_track_id:
                self.guide_track_id = state.session.track_id
                self.guide = load_guide_for(state.session.track_id, GUIDE_DIR)
            view = build_coach_view(state, self.guide, sh.messages, sh.packets, sh.progress_line, sh.recording_name)
            error = sh.error
            stopped = sh.stop.is_set()
        self.l_lap.configure(text=view.lap_line)
        self.l_corner.configure(text=view.corner_line)
        for label, text in zip(self.l_msg, list(view.messages) + ["", "", ""]):
            label.configure(text=text)
        self.l_progress.configure(text=view.progress_line)
        self.l_status.configure(text=error or view.status_line, fg=ACCENT if error else "#b0b0b0")
        if stopped and not self.closed:  # replay się skończył albo błąd portu: zamykamy okno
            self.close()
            return
        if not self.closed:
            self.root.after(100, self.refresh)

    def close(self) -> None:
        self.closed = True
        self.shared.stop.set()
        self.root.destroy()

    def run(self) -> None:
        self.refresh()
        self.root.mainloop()
