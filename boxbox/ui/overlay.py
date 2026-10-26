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
        guide_out: Path | None = None, scale: float = 1.0, alpha: float = 0.97,
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
            self.root.attributes("-alpha", alpha)
        except tk.TclError:
            pass
        self.root.configure(bg=ACCENT)  # czerwona ramka: wnętrze to osobna ramka z czarnym tłem
        self.root.geometry("+40+40")
        inner = tk.Frame(self.root, bg=BG)
        inner.pack(padx=3, pady=3, fill="both", expand=True)
        wrap = int(520 * scale)

        def font(size: int, bold: bool = False) -> tuple:
            return ("Segoe UI", int(size * scale), "bold") if bold else ("Segoe UI", int(size * scale))

        pad = {"padx": 16, "pady": 3, "anchor": "w"}
        self.l_title = tk.Label(inner, text=plan.title, fg=CYAN, bg=BG, font=font(13, True), wraplength=wrap, justify="left")
        self.l_lap = tk.Label(inner, text="", fg=FG, bg=BG, font=font(30, True))
        self.l_goal = tk.Label(inner, text="", fg=FG, bg=BG, font=font(16), wraplength=wrap, justify="left")
        self.l_corner = tk.Label(inner, text="", fg=CYAN, bg=BG, font=font(38, True))
        self.l_task = tk.Label(inner, text="", fg=ACCENT, bg=BG, font=font(24, True), wraplength=wrap, justify="left")
        self.l_note = tk.Label(inner, text="", fg="#cfcfcf", bg=BG, font=font(13), wraplength=wrap, justify="left")
        self.l_status = tk.Label(inner, text="", fg="#b0b0b0", bg=BG, font=font(11), wraplength=wrap, justify="left")
        for w in (self.l_title, self.l_lap, self.l_goal, self.l_corner, self.l_task, self.l_note, self.l_status):
            w.pack(fill="x", **pad)
        tk.Label(inner, text="przeciągnij, aby przesunąć | Esc zamyka i kończy nagranie", fg="#808080", bg=BG, font=font(9)).pack(fill="x", padx=16, pady=(2, 8), anchor="w")
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


def resolve_plan(plan: str | None, name: str | None, plans_dir: Path) -> Path | None:
    """Plan z argumentu (plik lub nazwa) albo dobrany po pierwszym słowie nazwy nagrania."""
    if plan:
        candidates = [Path(plan), plans_dir / plan, plans_dir / f"{plan}.json"]
        for c in candidates:
            if c.is_file():
                return c
        print(f"Nie ma planu '{plan}'. Dostępne: {', '.join(p.stem for p in sorted(plans_dir.glob('*.json')))}")
        return None
    available = sorted(plans_dir.glob("*.json"))
    if not available:
        print(f"Brak planów w {plans_dir}. Podaj --plan <plik.json>.")
        return None
    key = (name or "").lower().split("-")[0]
    matches = [p for p in available if key and p.stem.lower().startswith(key)]
    if len(matches) == 1:
        return matches[0]
    print("Który plan? " + ", ".join(f"{i + 1}) {p.stem}" for i, p in enumerate(available)))
    try:
        choice = int(input("Numer: ").strip())
        return available[choice - 1]
    except (ValueError, IndexError, EOFError):
        print("Nie wybrano planu.")
        return None


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Nakładka do nagrań BoxBox Academy")
    parser.add_argument(
        "--name", nargs="*", help="nazwa nagrania; kilka słów łączy się myślnikami (bez tego tylko nakładka, bez zapisu)"
    )
    parser.add_argument("--plan", help="plan sesji: plik JSON albo nazwa z katalogu planów (domyślnie wg nazwy nagrania)")
    parser.add_argument("--plans-dir", type=Path, default=Path("plany"))
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--dir", type=Path, default=Path("recordings"))
    parser.add_argument("--guide-dir", type=Path, default=GUIDE_DIR)
    parser.add_argument("--scale", type=float, default=1.0, help="mnożnik wielkości napisów, np. 1.3")
    parser.add_argument("--alpha", type=float, default=0.97, help="krycie okna 0.5-1.0 (1.0 = bez przezroczystości)")
    args = parser.parse_args(argv)

    name = "-".join(args.name) if args.name else None
    plan_path = resolve_plan(args.plan, name, args.plans_dir)
    if plan_path is None:
        return 1
    plan = load_plan(plan_path)
    print(f"Plan: {plan.title} ({plan_path})")
    writer = None
    path = None
    if name:
        args.dir.mkdir(parents=True, exist_ok=True)
        path = recording_path(args.dir, name, datetime.now())
        path.with_suffix(".txt").write_text(
            "Tor:\nAsysty (skrzynia / TC / ABS):\nOkrążenia i błędy (numer okrążenia, zakręt, błąd):\n", encoding="utf-8"
        )
        writer = RecordingWriter(path)
        print(f"Nagrywam do {path}. Zamknij nakładkę (Esc), żeby zakończyć.")
    receiver = Receiver(args.port, writer)
    receiver.start()
    guide_out = path.with_suffix(".guide.json") if path else None
    window = OverlayWindow(
        receiver, plan, args.guide_dir, path.name if path else None, guide_out,
        scale=max(0.5, args.scale), alpha=min(1.0, max(0.5, args.alpha)),
    )
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
