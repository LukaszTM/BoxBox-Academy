"""Okno BoxBox Academy: interfejs z makiety (index.html) w Qt WebEngine + mostek do silnika.

Interfejs tylko rysuje; wszystko liczy Python: sesja (CoachSession), sonda portu, baza, eksporty.
Zasada „bez wyskakujących okien”: jedyne systemowe okno to drukowanie (Windows).
"""
import base64
import json
import logging
import os
import subprocess
import sys
import threading
import time
import traceback
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QEvent, QObject, QTimer, QUrl, Signal, Slot
from PySide6.QtGui import QIcon
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QApplication, QMainWindow

from boxbox.coach.analyze import format_time, report_laps
from boxbox.coach.delta import lap_csv
from boxbox.coach.progress import CLEAN_LAPS_TO_ADVANCE
from boxbox.gui import texts
from boxbox.games import adapter
from boxbox.gui.data import DataBuilder, _norm, _resample, _shape_for, to_json
from boxbox.gui.hud import HudFrame, HudWindow, demo_frame
from boxbox.gui.report import session_report_html
from boxbox.gui.probe import ProbeResult, ProbeWorker, probe
from boxbox.gui.settings import Settings
from boxbox.session import CoachSession, SessionConfig
from boxbox.storage.db import Database
from boxbox.tools.bugreport import build_bug_report
from boxbox.tracks.atlas import MIN_FIT_M, fit_path, load_atlas
from boxbox.tracks.atlas import fit as fit_atlas
from boxbox.tracks.model import load_track_by_id
from boxbox.tracks.shape import SHAPE_DIR, shape_path
from boxbox.ui.overlay_model import GUIDE_DIR, build_coach_view, guide_from_track, load_guide_for
from boxbox.voice.player import ClipLibrary, VoicePlayer

log = logging.getLogger("boxbox.gui")
WEB_DIR = Path(__file__).resolve().parent / "web"
ROOT = Path(__file__).resolve().parent.parent.parent
IMAGE_SUFFIXES = (".png", ".jpg", ".jpeg", ".webp", ".bmp")


def photo_folders() -> list[Path]:
    """Obrazy, Pulpit i Pobrane użytkownika, także gdy Windows przeniósł je do OneDrive (znane foldery z rejestru)."""
    home = Path.home()
    folders: list[Path] = []
    if sys.platform.startswith("win"):
        try:
            import winreg

            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders") as key:
                for name in ("My Pictures", "Desktop", "{374DE290-123F-4565-9164-39C4925E467B}"):  # ostatni = Pobrane
                    try:
                        value, _ = winreg.QueryValueEx(key, name)
                        folders.append(Path(os.path.expandvars(value)))
                    except OSError:
                        pass
        except (ImportError, OSError):
            pass
    for base in (home, home / "OneDrive"):
        for name in ("Pictures", "Obrazy", "Desktop", "Pulpit", "Downloads", "Pobrane"):
            folders.append(base / name)
    out: list[Path] = []
    for f in folders:
        if f not in out:
            out.append(f)
    return out


class Bridge(QObject):
    """Obiekt widoczny w JS jako `bridge`. Sloty = akcje z okna, sygnały = dane do okna."""

    dataChanged = Signal(str)
    liveChanged = Signal(str)
    toast = Signal(str)  # informacja na 6 s (pasek pod nagłówkiem)
    notice = Signal(str, str)  # (error|info|success, tekst): błąd zostaje do zamknięcia
    navigateTo = Signal(str)
    photos = Signal(str)

    def __init__(self, window: "WebWindow") -> None:
        super().__init__()
        self.w = window

    @Slot(result=str)
    def getData(self) -> str:
        return to_json(self.w.data.build())

    @Slot(str)
    def startSession(self, payload: str) -> None:
        self.w.start_from_ui(json.loads(payload or "{}"))

    @Slot()
    def stopSession(self) -> None:
        if self.w.session is not None:
            self.w.session.stop()

    @Slot()
    def previewOverlay(self) -> None:
        self.w.preview_overlay()

    @Slot()
    def sessionReport(self) -> None:
        self.w.save_session_report()

    @Slot(str)
    def finishWizard(self, nick: str) -> None:
        s = self.w.settings
        s.nick = nick.strip() or s.nick
        s.wizard_done = True
        self.w.save_settings()
        self.w.push_all()

    @Slot(str)
    def setSetting(self, payload: str) -> None:
        self.w.apply_settings(json.loads(payload or "{}"))

    @Slot()
    def checkTelemetry(self) -> None:
        self.w.check_telemetry()

    @Slot()
    def playSample(self) -> None:
        self.w.play_sample()

    @Slot(str)
    def bugReport(self, description: str) -> None:
        files = build_bug_report(description, self.w.data_dir, Path("recordings"), Path("raporty-bledow"))
        self.w.data.wizard["bugResult"] = "Gotowe: " + ", ".join(str(f) for f in files)
        self.notice.emit("success", f"Raport błędu zapisany: {files[0]}")
        self.w.push_all()

    @Slot()
    def exportCsv(self) -> None:
        self.w.export_csv()

    @Slot()
    def printPdf(self) -> None:
        self.w.print_pdf()

    @Slot(str)
    def saveLicensePng(self, data_url: str) -> None:
        head, _, payload = data_url.partition(",")
        out = self.w.export_dir() / f"plakietka-{datetime.now():%Y-%m-%d_%H%M%S}.png"
        out.write_bytes(base64.b64decode(payload))
        self.notice.emit("success", f"Zapisano plakietkę: {out}")

    @Slot()
    def listPhotos(self) -> None:
        found: list[Path] = []
        seen: set[Path] = set()
        for folder in photo_folders():
            if not folder.is_dir():
                continue
            try:
                entries = sorted(folder.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True)
            except OSError:
                continue
            for p in entries:
                if p.suffix.lower() in IMAGE_SUFFIXES and p.is_file() and p.stat().st_size < 12_000_000 and p.resolve() not in seen:
                    seen.add(p.resolve())
                    found.append(p)
                if len(found) >= 60:
                    break
        out = [{"path": str(p), "name": p.name, "thumb": QUrl.fromLocalFile(str(p)).toString()} for p in found[:60]]
        log.info("zdjęcia: %d plików w %s", len(out), ", ".join(str(f) for f in photo_folders() if f.is_dir()))
        self.photos.emit(json.dumps(out, ensure_ascii=False))

    @Slot(str)
    def setPhoto(self, path: str) -> None:
        self.w.set_photo(path)

    @Slot()
    def openDataDir(self) -> None:
        self._open_folder(self.w.data_dir)

    @Slot()
    def openRecordingsDir(self) -> None:
        self._open_folder(Path("recordings"))

    def _open_folder(self, folder: Path) -> None:
        folder.mkdir(parents=True, exist_ok=True)
        path = str(folder.resolve())
        try:
            if sys.platform.startswith("win"):
                os.startfile(path)  # type: ignore[attr-defined]
            else:
                subprocess.Popen(["xdg-open", path])
        except OSError:
            self.toast.emit(path)

    @Slot(str)
    def selectTrack(self, name: str) -> None:
        self.w.select_track(name)

    @Slot(str)
    def selectAnalysis(self, payload: str) -> None:
        sel = json.loads(payload or "{}")
        d = self.w.data.analysis_sel
        if "session" in sel:
            d["session"] = int(sel["session"])
            d["lap"] = None
        if "lap" in sel:
            d["lap"] = int(sel["lap"])
        if "comp" in sel:
            d["comp"] = sel["comp"]
        self.w.push_all()


class WebWindow(QMainWindow):
    def __init__(self, data_dir: Path = Path("data"), shape_dir: Path | None = None) -> None:
        super().__init__()
        self.setWindowTitle(f"{texts.APP_NAME} {texts.VERSION}")
        self.resize(1480, 960)
        self.setMinimumSize(1180, 760)
        self.data_dir = data_dir
        self.settings_path = data_dir / "settings.json"
        self.settings = Settings.load(self.settings_path)
        self.db_path = data_dir / "boxbox.sqlite"
        self.data = DataBuilder(self.settings, self.db_path, data_dir, **({"shape_dir": shape_dir} if shape_dir else {}))
        self.session: CoachSession | None = None
        self.session_started_at = 0.0
        self.session_ui: dict = {}
        self.overlay: HudWindow | None = None
        self.report_path: Path | None = None  # ostatni zapisany raport PDF sesji
        self._report_page = None
        self.hud_shape: dict | None = None  # minimapa: obrys 0..1 i kształt w świecie gry (do pozycji auta)
        self.guide = None
        self.guide_track_id: int | None = None
        self.player: VoicePlayer | None = None
        self.probe: ProbeWorker | None = None
        self._last_packets = 0
        self._last_packet_at = 0.0
        self._shown = 0
        self.live_messages: list[dict] = []
        self.chart_cache: dict = {"own": [], "ref": [], "mid": "", "end": ""}
        self.view = QWebEngineView()
        self.setCentralWidget(self.view)
        self.bridge = Bridge(self)
        self.channel = QWebChannel()
        self.channel.registerObject("bridge", self.bridge)
        self.view.page().setWebChannel(self.channel)
        self.view.load(QUrl.fromLocalFile(str(WEB_DIR / "index.html")))
        self.view.setAcceptDrops(True)
        self.view.installEventFilter(self)
        QTimer.singleShot(1500, self._watch_drops)
        self.start_probe()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(200)

    def _watch_drops(self) -> None:
        proxy = self.view.focusProxy()  # właściwy widget renderujący powstaje po załadowaniu strony
        if proxy is not None:
            proxy.installEventFilter(self)

    def eventFilter(self, obj, event) -> bool:  # noqa: N802
        et = event.type()
        if et in (QEvent.Type.DragEnter, QEvent.Type.DragMove) and event.mimeData().hasUrls():
            event.acceptProposedAction()
            return True
        if et == QEvent.Type.Drop and event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if url.isLocalFile() and Path(url.toLocalFile()).suffix.lower() in IMAGE_SUFFIXES:
                    self.set_photo(url.toLocalFile())
                    event.acceptProposedAction()
                    return True
            self.bridge.notice.emit("error", "To nie jest obraz (png, jpg, webp).")
            return True
        return super().eventFilter(obj, event)

    # --- ustawienia i dane ---
    def save_settings(self) -> None:
        self.settings.save(self.settings_path)

    def push_all(self) -> None:
        self.bridge.dataChanged.emit(to_json(self.data.build()))

    def push_live(self) -> None:
        self.bridge.liveChanged.emit(to_json({"status": self.data.status, "live": self.data.live}))

    def apply_settings(self, changes: dict) -> None:
        s = self.settings
        for key, value in changes.items():
            if key == "volume":
                s.volume = max(0.3, min(3.0, float(value) / 100))
            elif key == "scale":
                s.overlay_scale = float(value) / 100
                s.hud_layout = {**s.hud_layout, "scale": int(value)}
            elif key == "opacity":
                s.overlay_opacity = int(value)
                s.hud_layout = {**s.hud_layout, "opacity": int(value)}
            elif key == "port":
                s.port = int(value)
                self.data.status["port"] = s.port
                self.start_probe(restart=True)
            elif key == "overlayDefault":
                s.overlay = bool(value)
            elif key == "tutorialDone":
                s.tutorial_done = bool(value)
            elif key == "hud" and isinstance(value, dict):
                s.hud_layout = value
                if "opacity" in value:
                    s.overlay_opacity = int(value["opacity"])
                if "scale" in value:
                    s.overlay_scale = float(value["scale"]) / 100
                if self.overlay is not None:
                    self.overlay.set_layout(value)
            elif key == "quietDefault":
                s.quiet = bool(value)
            elif key == "autoStart":
                s.auto_start = bool(value)
            elif key in ("record", "explain", "consent", "nick"):
                setattr(s, key, value)
        self.save_settings()
        if self.player is not None and "volume" in changes:
            self.player.volume = s.volume
        self.push_all()

    def export_dir(self) -> Path:
        out = self.data_dir / "eksport"
        out.mkdir(parents=True, exist_ok=True)
        return out

    # --- sonda i start automatyczny ---
    def start_probe(self, restart: bool = False) -> None:
        if restart and self.probe is not None:
            self.probe.stop.set()
            self.probe = None
        if self.probe is None or not self.probe.is_alive():
            self.probe = ProbeWorker(self.settings.port)
            self.probe.start()
        self.probe.paused.clear()

    def probe_result(self) -> ProbeResult:
        return self.probe.result if self.probe is not None else ProbeResult()

    def tick(self) -> None:
        if self.session is None:
            r = self.probe_result()
            status = {"connected": r.connected, "busy": r.busy, "track": r.track, "fmt": r.fmt, "rate": int(r.rate), "port": self.settings.port}
            if status != self.data.status:  # bez zmiany nic nie wysyłamy: interfejs nie przerysowuje się w kółko
                self.data.status = status
                self.push_live()
            if r.connected and self.settings.auto_start and self.settings.wizard_done:
                self.start_session_cfg(self._config({}), auto=True)
            return
        self.refresh_live()

    # --- sesja ---
    def _config(self, ui: dict) -> SessionConfig:
        s = self.settings
        name = (ui.get("name") or f"sesja {datetime.now():%d.%m}").strip()
        lesson_id = ui.get("lesson") or None
        return SessionConfig(
            mode="race" if ui.get("mode") == "race" else "coach", port=s.port, db=self.db_path, record=name if ui.get("record", s.record) else None,
            voice=Path(s.voice_dir), volume=s.volume, corner_messages=not ui.get("quiet", s.quiet),
            corner_guidance=not ui.get("quiet", s.quiet),  # „cichy trener” wycisza też komendy w zakrętach
            lesson=lesson_id, lesson_corner=int(ui.get("corner") or 0) or None, explain_mode=s.explain,
        )

    def start_from_ui(self, ui: dict) -> None:
        self.start_session_cfg(self._config(ui), overlay=bool(ui.get("overlay", self.settings.overlay)), name=ui.get("name"))

    def start_session_cfg(self, cfg: SessionConfig, overlay: bool | None = None, name: str | None = None, auto: bool = False) -> None:
        if self.session is not None:
            return
        if self.probe is not None:
            self.probe.paused.set()
        self.live_messages = []
        self._shown = 0
        self.guide = None
        self.guide_track_id = None
        self.chart_cache = {"own": [], "ref": [], "mid": "", "end": ""}
        if cfg.shape_dir is None:  # każda sesja z okna zostawia kształt toru (albo dopasowanie atlasu) do mapy
            cfg.shape_dir = self.data.shape_dir
        if cfg.fit_dir is None:
            cfg.fit_dir = self.data.fit_dir
        self.session = CoachSession(cfg, on_note=lambda text: None)
        self._last_packets = 0
        self._last_packet_at = time.monotonic()
        self.session_started_at = time.monotonic()
        self.session_ui = {"name": name or cfg.record or "sesja", "overlay": self.settings.overlay if overlay is None else overlay, "auto": auto}
        self.session.start_background()
        self.hud_shape = None
        self._hud_laps = 0
        self._fit_thread: threading.Thread | None = None
        self._fit_at = time.monotonic()
        if self.session_ui["overlay"]:
            self.overlay = HudWindow(self.settings.hud_layout, self.settings.overlay_opacity, self.settings.overlay_scale)
            self.overlay.show()
        self.data.summary = None
        if auto:
            self.live_messages.append({"t": 0.0, "text": texts.HOME["auto_started"]})
        self.refresh_live(force_full=True)
        self.bridge.navigateTo.emit("start")

    def _lap_chart(self) -> None:
        """Prędkość ostatniego pełnego okrążenia vs najlepszego (z sesji); liczone tylko po zmianie okrążenia."""
        assert self.session is not None
        laps = [l for l in self.session.recorder.laps if l.samples and not l.pitted]
        if not laps:
            return
        last = laps[-1]
        best = min((l for l in laps if l.lap_time_ms and not l.invalid), key=lambda l: l.lap_time_ms, default=None)
        own = _resample(last.samples, "speed_kmh")
        ref = _resample(best.samples, "speed_kmh") if best is not None and best is not last else []
        hi = max(own + ref) if own else 1
        length = max((s.distance_m for s in last.samples), default=0)
        self.chart_cache = {"own": _norm(own, 0, hi), "ref": _norm(ref, 0, hi) if ref else [], "mid": f"{length / 2:,.0f} m".replace(",", " "), "end": f"{length:,.0f} m".replace(",", " ")}

    def refresh_live(self, force_full: bool = False) -> None:
        session = self.session
        if session is None:
            return
        sh = session.shared
        with sh.lock:
            state = sh.state
            if state.session is not None and state.session.track_id != self.guide_track_id:
                self.guide_track_id = state.session.track_id
                self.guide = load_guide_for(state.session.track_id, GUIDE_DIR)
            if self.guide is None and session.coach is not None:
                self.guide = guide_from_track(session.coach.track)  # tor bez przewodnika: zakręty z pliku toru (także automatycznego)
            view = build_coach_view(state, self.guide, sh.messages, sh.packets, sh.progress_line, sh.recording_name, sh.focus_line)
            error = sh.error
            new = session.messages[self._shown:]
            self._shown = len(session.messages)
            packets = sh.packets
            stopped = sh.stop.is_set()
            lap_count = len(session.recorder.laps)
        for t, text in new:
            self.live_messages.append({"t": t, "text": text})
        if lap_count != self.chart_cache.get("laps"):
            self._lap_chart()
            self.chart_cache["laps"] = lap_count
        lap = state.lap.player if state.lap is not None else None
        progress = session.coach.progress if session.coach is not None else None
        best = session.coach.best_time_ms if session.coach is not None else None
        delta = None
        if session.best_before_ms and best:
            delta = (best - session.best_before_ms) / 1000
        rate = int(packets / max(1.0, time.monotonic() - self.session_started_at))
        self.data.live = {
            "name": self.session_ui.get("name", ""), "elapsed": time.monotonic() - self.session_started_at, "recording": session.recording is not None,
            "recordingName": session.recording.name if session.recording else "", "lesson": session.lesson.title if session.lesson else "",
            "lapLine": view.lap_line, "pit": bool(lap and lap.pit_status), "invalid": bool(lap and lap.current_lap_invalid),
            "corner": view.corner_line.split("  ")[0] if view.corner_line else "", "dist": (view.corner_line.split("  ")[1].replace("za ", "") if "  " in view.corner_line else ("TERAZ" if view.corner_line.endswith("TERAZ") else "")),
            "focus": view.focus_line.replace("Na tym okrążeniu popraw: ", ""), "messages": self.live_messages[-6:],
            "goalText": f"Cel: {CLEAN_LAPS_TO_ADVANCE} czyste okrążenia z rzędu" if progress is not None else "",
            "streak": progress.streak if progress is not None else 0, "needed": CLEAN_LAPS_TO_ADVANCE,
            "best": format_time(best) if best else "", "delta": delta, "laps": lap_count, "rate": rate,
            "cpu": "liczone po sesji", "statusLine": view.status_line, "error": error, "chart": self.chart_cache,
        }
        if self.overlay is not None:
            self.overlay.apply(self._hud_frame(session, state, view, new, lap_count, best, progress))
        if time.monotonic() - self._fit_at > 20 and (self._fit_thread is None or not self._fit_thread.is_alive()):
            self._fit_at = time.monotonic()
            self.fit_atlas_now()
        # koniec bez sygnału
        now = time.monotonic()
        if packets != self._last_packets:
            self._last_packets = packets
            self._last_packet_at = now
        elif self._last_packets > 0 and not session.cfg.replay and now - self._last_packet_at > self.settings.auto_stop_s:
            self.live_messages.append({"t": now - self.session_started_at, "text": texts.HOME["auto_stopped"].format(s=self.settings.auto_stop_s)})
            session.stop()
        if force_full:
            self.push_all()
        else:
            self.push_live()
        if stopped and not session.running:
            self.finish_session()

    # --- dopasowanie atlasu w trakcie sesji (minimapa i mapa działają bez pełnego okrążenia) ---
    def fit_atlas_now(self, wait: bool = False) -> None:
        session = self.session
        if session is None or session.state.session is None:
            return
        track_id = session.state.session.track_id
        length = float(session.state.session.track_length_m)
        fit_file = fit_path(track_id, self.data.fit_dir)
        if fit_file.exists() or shape_path(track_id, self.data.shape_dir).exists() or shape_path(track_id, SHAPE_DIR).exists():
            return
        atlas = load_atlas(track_id)
        if atlas is None:
            return
        with session.shared.lock:
            samples = list(session.shape_sampler.all_samples())
        if not samples or samples[-1][0] - samples[0][0] < MIN_FIT_M:
            return

        def work() -> None:
            try:
                result = fit_atlas(atlas, samples, length)
                if result is not None:
                    result.save(fit_file)
                    self.hud_shape = None  # następna klatka wczyta minimapę
                    log.info("obrys toru %d dopasowany w trakcie sesji: błąd %.1f m", track_id, result.error_m)
            except Exception:  # dopasowanie nie może zepsuć sesji
                log.error("dopasowanie atlasu: %s", traceback.format_exc())

        self._fit_thread = threading.Thread(target=work, daemon=True, name="boxbox-atlas-fit")
        self._fit_thread.start()
        if wait:
            self._fit_thread.join(timeout=30)

    # --- nakładka HUD: klatka z danych sesji ---
    def _hud_shape_for(self, track_id: int) -> dict | None:
        """Obrys do minimapy (0..1, proporcje zachowane) plus kształt w świecie gry; tylko gdy dystans wskazuje punkt obrysu."""
        if self.hud_shape is not None and self.hud_shape.get("track_id") == track_id:
            return self.hud_shape
        shape, source = _shape_for(track_id, [self.data.shape_dir, SHAPE_DIR], self.data.fit_dir)
        self.hud_shape = {"track_id": track_id, "shape": None, "norm": None}
        if shape is not None and shape.points and source != "outline":
            xs = [p.x for p in shape.points]
            zs = [p.z for p in shape.points]
            span = max(max(xs) - min(xs), max(zs) - min(zs)) or 1.0
            ox, oz = (span - (max(xs) - min(xs))) / 2, (span - (max(zs) - min(zs))) / 2
            step = max(1, len(shape.points) // 240)
            pts = shape.points[::step]
            self.hud_shape.update({"shape": shape, "step": step, "n": len(pts),
                                   "norm": {"points": [[round((p.x - min(xs) + ox) / span, 4), round((p.z - min(zs) + oz) / span, 4)] for p in pts]}})
        return self.hud_shape

    def _hud_frame(self, session: CoachSession, state, view, new: list, lap_count: int, best: int | None, progress) -> HudFrame:
        lap = state.lap.player if state.lap is not None else None
        elapsed = time.monotonic() - self.session_started_at
        track = state.session.track_name.upper() if state.session else ""
        rec = " · NAGRYWAM" if session.recording is not None else ""
        if lap is None:
            return HudFrame(mode="waiting", status=f"● CZEKAM NA GRĘ · PORT {self.settings.port}")
        status = f"● TRENER · {track} · {int(elapsed) // 60:02d}:{int(elapsed) % 60:02d}{rec}" if track else f"● TRENER{rec}"
        corner, meters = "", None
        if view.corner_line:
            parts = view.corner_line.split("  ")
            corner = parts[0]
            rest = parts[1] if len(parts) > 1 else ""
            meters = 0.0 if rest == "TERAZ" else (float(rest.replace("za ", "").replace(" m", "")) if rest.startswith("za ") else None)
        goal, goal_meters, passed = "", None, False
        focus = view.focus_line.replace("Na tym okrążeniu popraw: ", "")
        if focus:
            name, _, what = focus.partition(", ")
            goal = f"POPRAW · {name} · {what}".upper()
            if self.guide is not None and lap.lap_distance >= 0:
                gc = next((c for c in self.guide.corners if c.name == name), None)
                if gc is not None:
                    length = self.guide.length_m
                    goal_meters = (gc.apex_m - lap.lap_distance) % length
                    passed = (lap.lap_distance - gc.apex_m) % length < 400
        last_delta = "—"
        laps = [l for l in session.recorder.laps if l.lap_time_ms and not l.pitted]
        ref_ms = session.best_before_ms or (min((l.lap_time_ms for l in laps[:-1] if not l.invalid), default=None) if len(laps) > 1 else None)
        if laps and ref_ms:
            last_delta = f"{(laps[-1].lap_time_ms - ref_ms) / 1000:+.2f} s".replace(".", ",").replace("-", "−")
        streak = progress.streak if progress is not None else 0
        lap_end = None
        if lap_count != getattr(self, "_hud_laps", 0):
            self._hud_laps = lap_count
            if laps and session.recorder.laps and session.recorder.laps[-1] is laps[-1]:
                done = laps[-1]
                msgs = session.messages_by_lap.get(done.number, [])
                warn = f"{msgs[0].corner_name}: {msgs[0].problem.rstrip('.')}" if msgs else ""
                good = "czyste okrążenie" if not msgs and not done.invalid else ""
                lap_end = {"lap": f"OKRĄŻENIE {done.number:02d}", "time": format_time(done.lap_time_ms), "delta": last_delta if last_delta != "—" else "",
                           "good": good, "warn": warn, "complete": not done.invalid, "out_lap": done.pitted}
            elif session.recorder.laps and session.recorder.laps[-1].pitted:
                lap_end = {"lap": f"OKRĄŻENIE {session.recorder.laps[-1].number:02d}", "time": "", "delta": "", "good": "", "warn": "", "complete": False, "out_lap": True}
        shape = car = None
        if state.session is not None:
            hs = self._hud_shape_for(state.session.track_id)
            if hs and hs.get("norm") and lap.lap_distance >= 0:
                shape = hs["norm"]
                sh = hs["shape"]
                idx = int((lap.lap_distance % sh.length_m) / sh.step_m / hs["step"]) % hs["n"]
                brake = None
                if self.guide is not None and corner:
                    gc = next((c for c in self.guide.corners if c.name == corner), None)
                    if gc is not None:
                        brake = int(((gc.apex_m - 80) % sh.length_m) / sh.step_m / hs["step"]) % hs["n"]
                car = (idx, brake)
        return HudFrame(
            mode="normal", status=status, corner=corner, meters=meters, passed=passed, goal=goal,
            lap=f"OKRĄŻENIE {lap.current_lap_num:02d}" + (" · PIT" if lap.pit_status else ""), delta=last_delta,
            streak_text=f"{streak} / {CLEAN_LAPS_TO_ADVANCE} CZYSTYCH" if progress is not None else "",
            streak_pct=100 * streak / CLEAN_LAPS_TO_ADVANCE, radio=(new[-1] if new else None), lap_end=lap_end, shape=shape, car=car,
            extra={"goalMeters": goal_meters},
        )

    def finish_session(self) -> None:
        session, self.session = self.session, None
        if session is None:
            return
        result = session.finish()
        self._hud_laps = 0
        if self.overlay is not None:
            self.overlay.close()
            self.overlay = None
        report = ""
        if not result.state.empty:
            try:
                report = report_laps(result.recorder, session.cfg.track, session.cfg.db, str(session.cfg.replay) if session.cfg.replay else "okno", "best", session.cfg.replay)
            except Exception as exc:  # raport nie może zabić okna
                report = f"Raport po sesji nie powstał: {exc}"
        laps = [l for l in result.recorder.laps if l.samples and not l.pitted and l.lap_time_ms]
        best_ms = min((l.lap_time_ms for l in laps if not l.invalid), default=None)
        lap_rows = []
        notes_by_lap: dict[int, int] = {}
        for m in session.lap_messages:
            notes_by_lap[m.lap] = notes_by_lap.get(m.lap, 0) + 1
        for l in laps:
            d = (l.lap_time_ms - best_ms) / 1000 if best_ms and l.lap_time_ms else None
            lap_rows.append({"number": l.number, "time": format_time(l.lap_time_ms), "delta": f"{d:+.3f}" if d is not None else "", "valid": not l.invalid, "notes": notes_by_lap.get(l.number, 0)})
        corner_rows = []
        if session.coach is not None and session.coach.reference is not None:
            names = {c.number: (c.name or f"Z{c.number}") for c in session.coach.track.corners}
            before = {m.corner: m for m in (session.reference_before or ())}
            for m in session.coach.reference.corners:
                p = before.get(m.corner)
                dt = f"{(m.time_ms - p.time_ms) / 1000:+.2f}" if p else "–"
                corner_rows.append([names.get(m.corner, str(m.corner)), f"{m.min_speed_kmh} km/h", str(m.gear_at_apex),
                                    f"{m.brake_point_m:.0f} m" if m.brake_point_m else "–", f"{m.full_throttle_m:.0f} m" if m.full_throttle_m else "–", dt])
        track_name = result.state.session.track_name if result.state.session else ""
        summary = result.summary
        delta = None
        if best_ms and session.best_before_ms:
            delta = (best_ms - session.best_before_ms) / 1000
        self.data.summary = {
            "name": self.session_ui.get("name", ""), "track": track_name, "trackId": result.state.session.track_id if result.state.session else None,
            "laps": len(laps), "elapsed": result.wall_s, "date": datetime.now().strftime("%d.%m.%Y"),
            "coach": result.coach_started, "best": format_time(best_ms) if best_ms else "", "clean": summary.clean_laps if summary else 0, "delta": delta,
            "cpu": f"{result.cpu_percent:.1f}% jednego rdzenia" if not session.cfg.replay and result.wall_s > 1 else "",
            "good": (result.race.good if result.race else summary.good if summary else ""), "toWork": (result.race.to_work if result.race else summary.to_work if summary else ""),
            "lapRows": lap_rows, "cornerRows": corner_rows, "report": report,
            "race": ({"lines": result.race.lines, "rating": result.race.safety_rating} if result.race else None),
            "lesson": ({"title": session.lesson.title, "passed": result.lesson_result[0], "best": result.lesson_result[1], "needed": result.lesson_result[2]} if session.lesson and result.lesson_result else None),
        }
        # zapamiętaj do ekranu Start i stan lekcji
        if laps:
            self.settings.last_session = {"date": datetime.now().strftime("%d.%m.%Y"), "track": track_name, "track_id": result.state.session.track_id if result.state.session else None,
                                          "best": format_time(best_ms) if best_ms else "", "delta": delta, "laps": len(laps), "toWork": summary.to_work if summary else "", "good": summary.good if summary else ""}
        if session.lesson and result.lesson_result:
            st = self.settings.lesson_state.get(session.lesson.id, {})
            st["best"] = max(st.get("best", 0), result.lesson_result[1])
            st["passed"] = bool(st.get("passed")) or result.lesson_result[0]
            self.settings.lesson_state[session.lesson.id] = st
        self.save_settings()
        self.data.live = None
        self.data.progress_track = None
        self.start_probe()
        self.push_all()
        self.bridge.navigateTo.emit("summary")

    # --- akcje pomocnicze ---
    def select_track(self, name: str) -> None:
        db = Database(self.db_path)
        try:
            for t in db.overview()["tracks"]:
                try:
                    if load_track_by_id(t["track_id"]).name == name:
                        self.data.progress_track = t["track_id"]
                except FileNotFoundError:
                    if f"tor {t['track_id']}" == name:
                        self.data.progress_track = t["track_id"]
        finally:
            db.close()
        self.push_all()

    def check_telemetry(self) -> None:
        if self.data.wizard.get("checking"):
            return
        self.data.wizard["checking"] = True
        self.data.wizard["checkResult"] = "Nasłuchuję 5 s..."
        self.push_all()
        if self.probe is not None:
            self.probe.paused.set()
        port = self.settings.port
        holder: dict = {}

        def work() -> None:
            holder["r"] = probe(port, 5.0)

        t = threading.Thread(target=work, daemon=True)
        t.start()

        def poll() -> None:
            if t.is_alive():
                QTimer.singleShot(200, poll)
                return
            r = holder.get("r")
            self.data.wizard["checking"] = False
            self.start_probe()
            if r is None or r.busy:
                self.data.wizard["checkResult"] = texts.WIZARD["check_busy"]
            elif r.packets == 0:
                self.data.wizard["checkResult"] = texts.WIZARD["check_none"]
            elif not r.supported:
                self.data.wizard["checkResult"] = texts.WIZARD["check_format"].format(fmt=r.fmt)
            else:
                self.data.wizard["checkResult"] = texts.WIZARD["check_ok"].format(track=r.track or "tor nieznany", fmt=r.fmt, rate=int(r.rate))
            self.push_all()

        QTimer.singleShot(200, poll)

    def play_sample(self) -> None:
        library = ClipLibrary(Path(self.settings.voice_dir))
        if len(library) == 0:
            self.bridge.toast.emit(texts.WIZARD["no_clips"].format(path=self.settings.voice_dir))
            return
        if self.player is None:
            self.player = VoicePlayer(library, volume=self.settings.volume).start()
        self.player.volume = self.settings.volume
        self.player.say(["misc_hello"], "test")

    def preview_overlay(self) -> None:
        """Pokazuje nakładkę z przykładową treścią na 5 s (bez sesji)."""
        if self.overlay is not None:
            return
        ov = HudWindow(self.settings.hud_layout, self.settings.overlay_opacity, self.settings.overlay_scale)
        ov.apply(demo_frame())
        ov.show()
        self._preview = ov
        QTimer.singleShot(5000, ov.close)

    def set_photo(self, path: str) -> None:
        src = Path(path)
        if not src.is_file() or src.suffix.lower() not in IMAGE_SUFFIXES:
            self.bridge.notice.emit("error", "To nie jest obraz (png, jpg, webp).")
            return
        dst = self.data_dir / f"profil{src.suffix.lower()}"
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(src.read_bytes())
        self.settings.photo = str(dst)
        self.save_settings()
        self.push_all()
        self.bridge.notice.emit("success", "Zdjęcie zapisane")

    def export_csv(self) -> None:
        sel = self.data.analysis_sel
        db = Database(self.db_path)
        try:
            sessions = db.session_list()
            if not sessions:
                self.bridge.toast.emit("Brak sesji do eksportu")
                return
            session = next((s for s in sessions if s["id"] == sel["session"]), sessions[0])
            laps = db.laps_for_session(session["id"])
            lap = next((l for l in laps if l.id == sel["lap"]), laps[-1] if laps else None)
            if lap is None:
                self.bridge.toast.emit("Brak okrążenia do eksportu")
                return
            own = db.samples(lap.id)
            best = db.best_lap(session["track_id"], allow_invalid=True) if session["track_id"] is not None else None
            ref = db.samples(best.id) if best and best.id != lap.id else None
        finally:
            db.close()
        out = self.export_dir() / f"okrazenie-{lap.id}-{datetime.now():%Y-%m-%d_%H%M%S}.csv"
        out.write_text(lap_csv(own, ref), encoding="utf-8-sig")
        self.bridge.notice.emit("success", f"Zapisano CSV: {out}")

    def save_session_report(self) -> None:
        """Raport sesji (radar umiejętności, sześć wskazówek, okrążenia) do PDF przez Qt, bez okna drukowania."""
        summary = self.data.summary
        if not summary:
            self.bridge.notice.emit("info", "Raport powstaje po zakończonej sesji")
            return
        try:
            from PySide6.QtWebEngineCore import QWebEnginePage
        except ImportError:
            self.bridge.notice.emit("error", "Zapis PDF niedostępny w tej instalacji")
            return
        skills = self.data.build()["skills"]
        profile = next((t for t in skills["tracks"] if t.get("trackId") == summary.get("trackId")), None) or skills.get("all")
        html = session_report_html(summary, profile, self.settings.nick, adapter(self.settings.game).name)
        out_dir = self.data_dir / "raporty"
        out_dir.mkdir(parents=True, exist_ok=True)
        track = (summary.get("track") or "sesja").lower().replace(" ", "-")
        out = out_dir / f"raport-{track}-{datetime.now():%Y-%m-%d_%H%M%S}.pdf"
        page = QWebEnginePage(self)
        self._report_page = page  # żyje do końca zapisu

        def on_loaded(ok: bool) -> None:
            if not ok:
                self.bridge.notice.emit("error", "Raport nie powstał: strona nie wczytała się")
                return
            page.printToPdf(str(out))

        def on_done(path: str, ok: bool) -> None:
            self.bridge.notice.emit("success" if ok else "error", f"Zapisano raport: {path}" if ok else "Raport nie powstał")
            self.report_path = Path(path) if ok else None
            self._report_page = None

        page.loadFinished.connect(on_loaded)
        page.pdfPrintingFinished.connect(on_done)
        page.setHtml(html, QUrl("file:///raport.html"))

    def print_pdf(self) -> None:
        """Systemowe okno drukowania Windows (jedyny wyjątek od zasady „bez osobnych okien”)."""
        try:
            from PySide6.QtPrintSupport import QPrintDialog, QPrinter
        except ImportError:
            self.bridge.notice.emit("error", "Drukowanie niedostępne w tej instalacji")
            return
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        dialog = QPrintDialog(printer, self)
        if dialog.exec():
            self.view.page().print(printer, lambda ok: self.bridge.notice.emit("success" if ok else "error", "Wydruk wysłany" if ok else "Drukowanie nie powiodło się"))

    def closeEvent(self, event) -> None:  # noqa: N802
        if self.session is not None:
            self.session.stop()
            self.finish_session()
        if self.probe is not None:
            self.probe.stop.set()
        if self.player is not None:
            self.player.close()
        super().closeEvent(event)


def run(argv: list[str] | None = None) -> int:
    app = QApplication.instance() or QApplication(argv or sys.argv)
    app.setApplicationName(texts.APP_NAME)
    icon = ROOT / "assets" / "icon.png"
    if icon.exists():
        app.setWindowIcon(QIcon(str(icon)))
    window = WebWindow()
    window.show()
    return app.exec()
