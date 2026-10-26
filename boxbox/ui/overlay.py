"""Nakładka na grę do nagrań: okno zawsze na wierzchu z celem okrążenia i zadaniem w zakręcie.

Jednocześnie nagrywa telemetrię (jedno gniazdo UDP; drugi program na tym samym
porcie nie dostałby pakietów). Gra musi działać w trybie okna bez ramki, nie
w pełnym ekranie, inaczej okno nie będzie widoczne.

Użycie: python -m boxbox.ui.overlay --name bahrajn-tt --plan plany/bahrajn-tt.json
"""
import argparse
import sys
import threading
import time
import tkinter as tk
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path

from boxbox.coach.laps import Lap, LapRecorder
from boxbox.telemetry.record import recording_path
from boxbox.telemetry.recording import RecordingWriter
from boxbox.telemetry.udp import DEFAULT_PORT, listen
from boxbox.tracks.detect import SpeedSample, detect_corners
from boxbox.ui.overlay_model import (
    GUIDE_DIR, OverlayView, SessionPlan, TrackGuide, build_view, calibrate_guide, load_guide_for, load_plan,
    save_guide,
)

BG = "#101010"
FG = "#f2f2f2"
ACCENT = "#ff2d2d"
CYAN = "#19e6e6"


class Receiver(threading.Thread):
    """Odbiera UDP w tle, zapisuje nagranie i aktualizuje stan pod blokadą."""

    def __init__(self, port: int, writer: RecordingWriter | None) -> None:
        super().__init__(daemon=True)
        self.port = port
        self.writer = writer
        self.recorder = LapRecorder()
        self.state = self.recorder.state
        self.completed: list[Lap] = []  # pełne okrążenia do kalibracji przewodnika
        self.lock = threading.Lock()
        self.stop = threading.Event()
        self.packets = 0
        self.error: str | None = None

    def run(self) -> None:
        start = time.monotonic()
        try:
            for data in listen(self.port, stop=self.stop):
                if self.writer is not None:
                    if self.packets == 0:
                        start = time.monotonic()
                    self.writer.write(time.monotonic() - start, data)
                with self.lock:
                    done = self.recorder.feed(data)
                    if done is not None:
                        self.completed.append(done)
                    self.packets += 1
        except OSError as exc:
            self.error = f"port {self.port}: {exc}"
        finally:
            if self.writer is not None:
                self.writer.close()


class OverlayWindow:
    def __init__(
        self, receiver: Receiver, plan: SessionPlan, guide_dir: Path, recording_name: str | None,
        guide_out: Path | None = None,
    ) -> None:
        self.receiver = receiver
        self.plan = plan
        self.guide_dir = guide_dir
        self.guide: TrackGuide | None = None
        self.guide_track_id: int | None = None
        self.calibrated = False
        self.guide_out = guide_out  # dokąd zapisać skalibrowany przewodnik
        self.recording_name = recording_name
        self.root = tk.Tk()
        self.root.title("BoxBox Academy - nagranie")
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        try:
            self.root.attributes("-alpha", 0.88)
        except tk.TclError:
            pass
        self.root.configure(bg=BG)
        self.root.geometry("+40+40")
        pad = {"padx": 14, "pady": 2, "anchor": "w"}
        self.l_title = tk.Label(self.root, text=plan.title, fg=CYAN, bg=BG, font=("Segoe UI", 11, "bold"))
        self.l_lap = tk.Label(self.root, text="", fg=FG, bg=BG, font=("Segoe UI", 22, "bold"))
        self.l_goal = tk.Label(self.root, text="", fg=FG, bg=BG, font=("Segoe UI", 12), wraplength=420, justify="left")
        self.l_corner = tk.Label(self.root, text="", fg=CYAN, bg=BG, font=("Segoe UI", 26, "bold"))
        self.l_task = tk.Label(self.root, text="", fg=ACCENT, bg=BG, font=("Segoe UI", 18, "bold"), wraplength=420, justify="left")
        self.l_note = tk.Label(self.root, text="", fg="#bbbbbb", bg=BG, font=("Segoe UI", 10), wraplength=420, justify="left")
        self.l_status = tk.Label(self.root, text="", fg="#9a9a9a", bg=BG, font=("Segoe UI", 9), wraplength=420, justify="left")
        for w in (self.l_title, self.l_lap, self.l_goal, self.l_corner, self.l_task, self.l_note, self.l_status):
            w.pack(fill="x", **pad)
        tk.Label(self.root, text="przeciągnij, aby przesunąć | Esc zamyka i kończy nagranie", fg="#666666", bg=BG, font=("Segoe UI", 8)).pack(fill="x", padx=14, pady=(2, 8), anchor="w")
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
        with self.receiver.lock:
            state = self.receiver.state
            packets = self.receiver.packets
            if state.session is not None and state.session.track_id != self.guide_track_id:
                self.guide_track_id = state.session.track_id
                self.guide = load_guide_for(state.session.track_id, self.guide_dir)
                self.calibrated = False
            if self.guide is not None and not self.calibrated and state.session is not None:
                self._try_calibrate(self.receiver.completed, float(state.session.track_length_m))
            view = build_view(state, self.plan, self.guide, packets, self.recording_name)
        self.apply(view)
        if self.receiver.error:
            self.l_status.configure(text=self.receiver.error, fg=ACCENT)
        if not self.closed:
            self.root.after(100, self.refresh)

    def _try_calibrate(self, laps: list[Lap], track_length_m: float) -> None:
        """Pierwsze pełne okrążenie: strefy hamowania gracza przesuwają zakręty z przewodnika."""
        assert self.guide is not None
        for lap in laps:
            if not lap.is_complete(track_length_m):
                continue
            samples = [SpeedSample(s.distance_m, s.speed_kmh, s.throttle, s.brake) for s in lap.samples]
            zones = detect_corners(samples, track_length_m)
            if len(zones) < 3:
                continue
            self.guide = calibrate_guide(self.guide, zones)
            self.calibrated = True
            if self.guide_out is not None:
                try:
                    save_guide(self.guide, self.guide_out)
                except OSError:
                    pass
            return

    def apply(self, view: OverlayView) -> None:
        self.l_lap.configure(text=view.lap_line)
        self.l_goal.configure(text=view.goal_line)
        self.l_corner.configure(text=view.corner_line)
        self.l_task.configure(text=view.task_line)
        self.l_note.configure(text=view.note_line)
        self.l_status.configure(text=view.status_line)

    def close(self) -> None:
        self.closed = True
        self.receiver.stop.set()
        self.root.destroy()

    def run(self) -> None:
        self.refresh()
        self.root.mainloop()


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Nakładka do nagrań BoxBox Academy")
    parser.add_argument("--name", help="nazwa nagrania (bez tego tylko nakładka, bez zapisu)")
    parser.add_argument("--plan", type=Path, required=True, help="plik JSON z planem sesji")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--dir", type=Path, default=Path("recordings"))
    parser.add_argument("--guide-dir", type=Path, default=GUIDE_DIR)
    args = parser.parse_args(argv)

    plan = load_plan(args.plan)
    writer = None
    path = None
    if args.name:
        args.dir.mkdir(parents=True, exist_ok=True)
        path = recording_path(args.dir, args.name, datetime.now())
        path.with_suffix(".txt").write_text(
            "Tor:\nAsysty (skrzynia / TC / ABS):\nOkrążenia i błędy (numer okrążenia, zakręt, błąd):\n", encoding="utf-8"
        )
        writer = RecordingWriter(path)
        print(f"Nagrywam do {path}. Zamknij nakładkę (Esc), żeby zakończyć.")
    receiver = Receiver(args.port, writer)
    receiver.start()
    guide_out = path.with_suffix(".guide.json") if path else None
    window = OverlayWindow(receiver, plan, args.guide_dir, path.name if path else None, guide_out)
    window.run()
    receiver.stop.set()
    receiver.join(timeout=3)
    if path is not None:
        if receiver.packets == 0:
            path.unlink(missing_ok=True)
            path.with_suffix(".txt").unlink(missing_ok=True)
            print("Nie odebrano żadnego pakietu - sprawdź ustawienia telemetrii w grze.", file=sys.stderr)
            return 1
        print(f"Zapisano {receiver.packets} pakietów. Uzupełnij notatki: {path.with_suffix('.txt')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
