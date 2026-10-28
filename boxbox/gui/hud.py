"""Nakładka HUD nad grą: przezroczyste okno WebEngine na cały ekran, przepuszcza kliknięcia do gry.

Rysuje hud.html?overlay=1 (ten sam plik co edytor w zakładce HUD F1) i steruje nim przez `window.BoxBoxHUD`.
Układ (pozycje, widoczność, krycie, skala) przychodzi z ustawień; treść z sesji (`HudFrame` budowany w oknie).
Gra musi działać w trybie okna bez ramki; w pełnym ekranie wyłącznym nakładka nie jest widoczna.
"""
import json
from dataclasses import dataclass, field
from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtWebEngineWidgets import QWebEngineView

WEB_DIR = Path(__file__).parent / "web"
RADIO_SECONDS = 8


@dataclass
class HudFrame:
    """Jedna klatka treści nakładki; okno wysyła do strony tylko to, co się zmieniło."""
    mode: str = "waiting"  # waiting | normal
    status: str = "● CZEKAM NA GRĘ"
    corner: str = ""
    meters: float | None = None  # None = brak zakrętu przed autem
    passed: bool = False
    goal: str = ""  # tekst wstęgi POPRAW (pusty = ukryta)
    lap: str = ""  # „OKRĄŻENIE 04”
    delta: str = "—"
    streak_text: str = ""
    streak_pct: float = 0.0
    radio: tuple[float, str] | None = None  # (sekundy sesji, tekst) nowego komunikatu
    lap_end: dict | None = None  # {"lap", "time", "delta", "good", "warn", "out_lap"}
    shape: dict | None = None  # {"points": [[0..1, 0..1], ...], "carIndex": i, "brakeIndex": j} albo None = ukryj
    extra: dict = field(default_factory=dict)


def _js(value: object) -> str:
    return json.dumps(value, ensure_ascii=False)


def _mmss(seconds: float) -> str:
    s = max(0, int(seconds))
    return f"{s // 60:02d}:{s % 60:02d}"


class HudWindow(QWebEngineView):
    def __init__(self, layout: dict | None = None, opacity: int = 70, scale: float = 1.0, screen=None) -> None:
        super().__init__(None)
        self.setWindowFlags(
            Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.WindowTransparentForInput | Qt.WindowType.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setWindowTitle("BoxBox Academy - HUD")
        self.page().setBackgroundColor(Qt.GlobalColor.transparent)
        screen = screen or QGuiApplication.primaryScreen()
        if screen is not None:
            self.setGeometry(screen.geometry())
        layout = dict(layout or {})
        layout.setdefault("opacity", opacity)
        layout.setdefault("scale", int(round(scale * 100)))
        self.layout_doc = layout
        self.ready = False
        self.pending: list[str] = []
        self._last: HudFrame | None = None
        self._lap_end_timer = 0.0
        self.loadFinished.connect(self._on_loaded)
        self.load(QUrl.fromLocalFile(str(WEB_DIR / "hud.html")).toString() + "?overlay=1")

    # --- strona ---
    def _on_loaded(self, ok: bool) -> None:
        self.ready = bool(ok)
        if not ok:
            return
        self.run(f"BoxBoxHUD.importLayout({_js(self.layout_doc)})")
        for code in self.pending:
            self.page().runJavaScript(code)
        self.pending.clear()

    def run(self, code: str) -> None:
        if self.ready:
            self.page().runJavaScript(code)
        else:
            self.pending.append(code)

    def set_layout(self, layout: dict) -> None:
        self.layout_doc = dict(layout)
        self.run(f"BoxBoxHUD.importLayout({_js(self.layout_doc)})")

    # --- treść ---
    def apply(self, f: HudFrame) -> None:
        """Przekłada klatkę na wywołania JS; wysyła tylko różnice względem poprzedniej klatki."""
        p = self._last
        js: list[str] = []
        if p is None or f.mode != p.mode:
            js.append(f"BoxBoxHUD.setMode({_js(f.mode)})")
        if p is None or f.status != p.status:
            js.append(f"BoxBoxHUD.setStatus({_js(f.status)})")
        if p is None or (f.corner, f.meters, f.passed) != (p.corner, p.meters, p.passed):
            js.append(f"BoxBoxHUD.setCorner({_js(f.corner or '—')}, {_js(f.meters if f.meters is not None else 0)})")
            js.append(f"BoxBoxHUD.setGoal({_js(f.meters if f.meters is not None else 9999)}, {_js(bool(f.passed) or not f.goal)}, {_js(f.goal or ' ')})")
        elif p is None or f.goal != p.goal:
            js.append(f"BoxBoxHUD.setGoal({_js(f.meters if f.meters is not None else 9999)}, {_js(bool(f.passed) or not f.goal)}, {_js(f.goal or ' ')})")
        if p is None or (f.lap, f.delta, f.streak_text, round(f.streak_pct)) != (p.lap, p.delta, p.streak_text, round(p.streak_pct)):
            js.append(f"BoxBoxHUD.setTiming({_js(f.lap)}, {_js(f.delta)}, {_js(f.streak_text)}, {_js(round(f.streak_pct))})")
        if f.radio is not None and (p is None or f.radio != p.radio):
            t, text = f.radio
            js.append(f"BoxBoxHUD.showRadio({_js(text)}, {RADIO_SECONDS}, {_js(_mmss(t))})")
        if f.lap_end is not None and (p is None or f.lap_end != p.lap_end):
            e = f.lap_end
            js.append(f"BoxBoxHUD.setLapEnd({_js(e.get('lap', ''))}, {_js(e.get('time', ''))}, {_js(e.get('delta', ''))}, {_js(e.get('good', ''))}, {_js(e.get('warn', ''))})")
            js.append(f"BoxBoxHUD.lapCompleted({{complete: {_js(bool(e.get('complete', True)))}, outLap: {_js(bool(e.get('out_lap', False)))}}})")
            js.append("BoxBoxHUD.newLap()")
        if p is None or f.shape != p.shape:
            js.append(f"BoxBoxHUD.setTrackShape({_js(f.shape)})")
        if js:
            self.run(";".join(js))
        self._last = f


def demo_frame() -> HudFrame:
    """Treść do podglądu „pokaż nakładkę na 5 s”."""
    return HudFrame(
        mode="normal", status="● TRENER · PODGLĄD", corner="T8–T10", meters=120, goal="POPRAW · T1–T2 · HAMUJ 20 M WCZEŚNIEJ",
        lap="OKRĄŻENIE 04", delta="−0,41 s", streak_text="2 / 3 CZYSTYCH", streak_pct=67, radio=(257, "T1–T2: hamowanie za późno, o jakieś dwadzieścia metrów."),
        shape={"points": [[0.15, 0.35], [0.57, 0.10], [0.9, 0.45], [0.54, 0.9], [0.13, 0.68]], "carIndex": 1, "brakeIndex": 3},
    )
