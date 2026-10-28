"""Okno BoxBox Academy: interfejs z makiety (index.html) w Qt WebEngine + mostek do silnika.

Interfejs tylko rysuje; wszystko liczy Python: sesja (CoachSession), sonda portu, baza, eksporty.
Zasada „bez wyskakujących okien”: jedyne systemowe okno to drukowanie (Windows).
"""
import base64
import json
import os
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QObject, QTimer, QUrl, Signal, Slot
from PySide6.QtGui import QIcon
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QApplication, QMainWindow

from boxbox.coach.analyze import format_time, report_laps
from boxbox.coach.delta import lap_csv
from boxbox.coach.lessons import lesson as lesson_by_id
from boxbox.coach.progress import CLEAN_LAPS_TO_ADVANCE
from boxbox.gui import texts
from boxbox.gui.data import DataBuilder, _resample, _norm, to_json
from boxbox.gui.overlay import QtOverlay
from boxbox.gui.probe import ProbeResult, ProbeWorker, probe
from boxbox.gui.settings import Settings
from boxbox.session import CoachSession, SessionConfig
from boxbox.storage.db import Database
from boxbox.tools.bugreport import build_bug_report
from boxbox.tracks.model import load_track_by_id
from boxbox.ui.overlay_model import GUIDE_DIR, build_coach_view, load_guide_for
from boxbox.voice.player import ClipLibrary, VoicePlayer

WEB_DIR = Path(__file__).resolve().parent / "web"
ROOT = Path(__file__).resolve().parent.parent.parent
IMAGE_SUFFIXES = (".png", ".jpg", ".jpeg", ".webp", ".bmp")


class Bridge(QObject):
    """Obiekt widoczny w JS jako `bridge`. Sloty = akcje z okna, sygnały = dane do okna."""

    dataChanged = Signal(str)
    liveChanged = Signal(str)
    toast = Signal(str)
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
        self.toast.emit(f"Raport błędu: {files[0]}")
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
        self.toast.emit(f"Zapisano plakietkę: {out}")

    @Slot()
    def listPhotos(self) -> None:
        found = []
        for folder in (Path.home() / "Pictures", Path.home() / "Obrazy", Path.home() / "Desktop", Path.home() / "Pulpit"):
            if folder.is_dir():
                for p in sorted(folder.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
                    if p.suffix.lower() in IMAGE_SUFFIXES and p.stat().st_size < 12_000_000:
                        found.append(p)
                    if len(found) >= 40:
                        break
        out = [{"path": str(p), "name": p.name, "thumb": QUrl.fromLocalFile(str(p)).toString()} for p in found[:40]]
        self.photos.emit(json.dumps(out, ensure_ascii=False))

    @Slot(str)
    def setPhoto(self, path: str) -> None:
        self.w.set_photo(path)

    @Slot()
    def openDataDir(self) -> None:
        path = str(self.w.data_dir.resolve())
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
        self.overlay: QtOverlay | None = None
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
        self.start_probe()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(200)

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
            elif key == "opacity":
                s.overlay_opacity = int(value)
            elif key == "port":
                s.port = int(value)
                self.data.status["port"] = s.port
                self.start_probe(restart=True)
            elif key == "overlayDefault":
                s.overlay = bool(value)
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
            self.data.status = {"connected": r.connected, "busy": r.busy, "track": r.track, "fmt": r.fmt, "rate": int(r.rate), "port": self.settings.port}
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
            lesson=lesson_id, lesson_corner=int(ui.get("corner") or 0) or None, explain_mode=s.explain,
            shape_dir=self.data.shape_dir, fit_dir=self.data.fit_dir,
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
        self.session = CoachSession(cfg, on_note=lambda text: None)
        self._last_packets = 0
        self._last_packet_at = time.monotonic()
        self.session_started_at = time.monotonic()
        self.session_ui = {"name": name or cfg.record or "sesja", "overlay": self.settings.overlay if overlay is None else overlay, "auto": auto}
        self.session.start_background()
        if self.session_ui["overlay"] and not cfg.replay:
            self.overlay = QtOverlay(scale=self.settings.overlay_scale)
            self.overlay.setWindowOpacity(self.settings.overlay_opacity / 100)
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
            self.overlay.apply(view, error)
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

    def finish_session(self) -> None:
        session, self.session = self.session, None
        if session is None:
            return
        result = session.finish()
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
            "name": self.session_ui.get("name", ""), "track": track_name, "laps": len(laps), "elapsed": result.wall_s, "date": datetime.now().strftime("%d.%m.%Y"),
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
        if self.overlay is not None:
            return
        ov = QtOverlay(scale=self.settings.overlay_scale)
        ov.setWindowOpacity(self.settings.overlay_opacity / 100)
        from boxbox.ui.overlay_model import CoachView

        ov.apply(CoachView("OKRĄŻENIE 4", "T8-T10  za 120 m", ("T1-T2: hamowanie za późno, o jakieś dwadzieścia metrów.", "Pierwsze okrążenie zapisane jako odniesienie.", "Mechanik na radiu, słyszę cię."), "Cel: 3 czyste okrążenia z rzędu (2/3)", "245 km/h, bieg 6 | 3481 m | podgląd", "Na tym okrążeniu popraw: T1-T2, hamuj 20 m wcześniej"))
        ov.show()
        self._preview = ov
        QTimer.singleShot(5000, ov.close)

    def set_photo(self, path: str) -> None:
        src = Path(path)
        if not src.is_file() or src.suffix.lower() not in IMAGE_SUFFIXES:
            self.bridge.toast.emit("To nie jest obraz (png, jpg, webp).")
            return
        dst = self.data_dir / f"profil{src.suffix.lower()}"
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(src.read_bytes())
        self.settings.photo = str(dst)
        self.save_settings()
        self.push_all()
        self.bridge.toast.emit("Zdjęcie zapisane")

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
        self.bridge.toast.emit(f"Zapisano CSV: {out}")

    def print_pdf(self) -> None:
        """Systemowe okno drukowania Windows (jedyny wyjątek od zasady „bez osobnych okien”)."""
        try:
            from PySide6.QtPrintSupport import QPrintDialog, QPrinter
        except ImportError:
            self.bridge.toast.emit("Drukowanie niedostępne w tej instalacji")
            return
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        dialog = QPrintDialog(printer, self)
        if dialog.exec():
            self.view.page().print(printer, lambda ok: self.bridge.toast.emit("Wydruk wysłany" if ok else "Drukowanie nie powiodło się"))

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
