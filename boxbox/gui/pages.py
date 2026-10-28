"""Strony okna głównego. Każda strona dostaje `ctx` (ustawienia, baza, sonda) i nie otwiera osobnych okien."""
import shutil
import threading
import time
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDoubleSpinBox, QFileSystemModel, QFrame, QGridLayout, QHBoxLayout, QLabel, QLineEdit,
    QPlainTextEdit, QProgressBar, QPushButton, QSlider, QSpinBox, QStackedWidget, QTableWidget, QTableWidgetItem,
    QTreeView, QVBoxLayout, QWidget,
)

from boxbox.coach.analyze import format_time, report_laps
from boxbox.coach.progress import CLEAN_LAPS_TO_ADVANCE, STEPS
from boxbox.gui import texts
from boxbox.gui.overlay import QtOverlay
from boxbox.gui.probe import ProbeResult, ProbeWorker, probe
from boxbox.gui.settings import Settings
from boxbox.gui.widgets import Banner, StatCard, label, panel
from boxbox.session import CoachSession, SessionConfig
from boxbox.storage.db import Database
from boxbox.tracks.model import load_track_by_id
from boxbox.ui.overlay_model import GUIDE_DIR, build_coach_view, guide_from_track, load_guide_for
from boxbox.voice.player import ClipLibrary, VoicePlayer


class Context:
    """Wspólne zasoby stron: ustawienia, ścieżka bazy, sonda portu (zatrzymywana na czas sesji)."""

    def __init__(self, settings: Settings, settings_path: Path, db_path: Path, data_dir: Path) -> None:
        self.settings = settings
        self.settings_path = settings_path
        self.db_path = db_path
        self.data_dir = data_dir
        self.probe: ProbeWorker | None = None

    def save(self) -> None:
        self.settings.save(self.settings_path)

    def start_probe(self) -> None:
        if self.probe is None or not self.probe.is_alive():
            self.probe = ProbeWorker(self.settings.port)
            self.probe.start()
        self.probe.paused.clear()

    def pause_probe(self) -> None:
        if self.probe is not None:
            self.probe.paused.set()

    def probe_result(self) -> ProbeResult:
        return self.probe.result if self.probe is not None else ProbeResult()

    def stop_probe(self) -> None:
        if self.probe is not None:
            self.probe.stop.set()


# ---------------------------------------------------------------- Start
class HomePage(QWidget):
    session_finished = Signal()

    def __init__(self, ctx: Context) -> None:
        super().__init__()
        self.ctx = ctx
        self.session: CoachSession | None = None
        self.overlay: QtOverlay | None = None
        self.guide = None
        self.guide_track_id: int | None = None
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(12)
        root.addWidget(label(texts.HOME["title"], "h1"))
        root.addWidget(label(texts.HOME["subtitle"], "muted"))
        self.banner = Banner(self)
        root.addWidget(self.banner)

        status_frame, status_lay = panel(self)
        self.status = label("", "muted")
        self.status.setObjectName("status")
        status_lay.addWidget(self.status)
        root.addWidget(status_frame)

        opts_frame, opts_lay = panel(self)
        self.mode = QComboBox()
        self.mode.addItems([texts.HOME["mode_coach"], texts.HOME["mode_race"]])
        self.mode.model().item(1).setEnabled(False)
        self.name = QLineEdit("sesja")
        self.record = QCheckBox(texts.HOME["record"])
        self.record.setChecked(ctx.settings.record)
        self.use_overlay = QCheckBox(texts.HOME["overlay"])
        self.use_overlay.setChecked(ctx.settings.overlay)
        self.auto_start = QCheckBox(texts.HOME["auto_start"])
        self.auto_start.setChecked(ctx.settings.auto_start)
        self.auto_start.toggled.connect(self._save_auto_start)
        grid = QGridLayout()
        grid.addWidget(label("Tryb"), 0, 0)
        grid.addWidget(self.mode, 0, 1)
        grid.addWidget(label(texts.HOME["name"]), 1, 0)
        grid.addWidget(self.name, 1, 1)
        grid.addWidget(self.record, 2, 0, 1, 2)
        grid.addWidget(self.use_overlay, 3, 0, 1, 2)
        grid.addWidget(self.auto_start, 4, 0, 1, 2)
        opts_lay.addLayout(grid)
        self.go = QPushButton(texts.HOME["go"])
        self.go.setObjectName("go")
        self.go.clicked.connect(self.toggle_session)
        opts_lay.addWidget(self.go, 0, Qt.AlignmentFlag.AlignLeft)
        root.addWidget(opts_frame)

        live_frame, live_lay = panel(self)
        live_frame.setObjectName("panel")
        self.live_frame = live_frame
        self.l_lap = label("", "big")
        self.l_corner = label("", "cyan")
        self.l_focus = label("", "yellow")
        self.l_messages = QPlainTextEdit()
        self.l_messages.setReadOnly(True)
        self.l_messages.setMaximumBlockCount(200)
        self.l_messages.setMinimumHeight(140)
        self.l_progress = label("", "green")
        self.l_live_status = label("", "muted")
        live_lay.addWidget(self.l_lap)
        live_lay.addWidget(self.l_corner)
        live_lay.addWidget(self.l_focus)
        live_lay.addWidget(label(texts.HOME["messages"], "h2"))
        live_lay.addWidget(self.l_messages)
        live_lay.addWidget(self.l_progress)
        live_lay.addWidget(self.l_live_status)
        root.addWidget(live_frame, 1)

        self.summary = QPlainTextEdit()
        self.summary.setObjectName("mono")
        self.summary.setReadOnly(True)
        self.summary.setMinimumHeight(160)
        self.summary.hide()
        root.addWidget(self.summary, 1)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(150)
        self._shown_messages = 0
        self._last_packets = 0
        self._last_packet_at = 0.0
        self.auto_stop_enabled = True

    def _save_auto_start(self, on: bool) -> None:
        self.ctx.settings.auto_start = on
        self.ctx.save()

    # stan połączenia (sonda) i sesji
    def refresh(self) -> None:
        port = self.ctx.settings.port
        if self.session is None:
            r = self.ctx.probe_result()
            if r.busy:
                self.status.setText(texts.HOME["status_busy"].format(port=port))
            elif r.connected:
                self.status.setText(texts.HOME["status_ok"].format(track=r.track or "tor nieznany", fmt=r.fmt, rate=int(r.rate)))
            else:
                self.status.setText(texts.HOME["status_waiting"].format(port=port))
            if r.connected and self.auto_start.isChecked():
                self.start_session()
                self.l_messages.appendPlainText(texts.HOME["auto_started"])
            return
        sh = self.session.shared
        with sh.lock:
            state = sh.state
            if state.session is not None and state.session.track_id != self.guide_track_id:
                self.guide_track_id = state.session.track_id
                self.guide = load_guide_for(state.session.track_id, GUIDE_DIR)
            if self.guide is None and self.session.coach is not None:
                self.guide = guide_from_track(self.session.coach.track)  # tor bez przewodnika: zakręty z pliku toru
            view = build_coach_view(state, self.guide, sh.messages, sh.packets, sh.progress_line, sh.recording_name, sh.focus_line)
            error = sh.error
            new_messages = self.session.messages[self._shown_messages:]
            self._shown_messages = len(self.session.messages)
            stopped = sh.stop.is_set()
        self.l_lap.setText(view.lap_line or texts.HOME["live_waiting"])
        self.l_corner.setText(view.corner_line)
        self.l_focus.setText(view.focus_line)
        for t, text in new_messages:
            self.l_messages.appendPlainText(f"[{t:6.1f} s] {text}")
        self.l_progress.setText(view.progress_line)
        self.l_live_status.setText(error or view.status_line)
        self.status.setText(error or view.status_line)
        if self.overlay is not None:
            self.overlay.apply(view, error)
        if error:
            self.banner.show_text(error)
        now = time.monotonic()
        if sh.packets != self._last_packets:
            self._last_packets = sh.packets
            self._last_packet_at = now
        elif (self.auto_stop_enabled and self._last_packets > 0 and not self.session.cfg.replay
              and now - self._last_packet_at > self.ctx.settings.auto_stop_s):
            self.l_messages.appendPlainText(texts.HOME["auto_stopped"].format(s=self.ctx.settings.auto_stop_s))
            self.session.stop()
        if stopped and not self.session.running:
            self.finish_session()

    def toggle_session(self) -> None:
        if self.session is None:
            self.start_session()
        else:
            self.session.stop()

    def start_session(self, cfg: SessionConfig | None = None) -> None:
        s = self.ctx.settings
        if cfg is None:
            cfg = SessionConfig(
                mode="coach", port=s.port, db=self.ctx.db_path, record=self.name.text().strip() or "sesja" if self.record.isChecked() else None,
                voice=Path(s.voice_dir), volume=s.volume,
            )
        self.ctx.pause_probe()
        self.banner.hide()
        self.summary.hide()
        self.l_messages.clear()
        self._shown_messages = 0
        self.guide = None
        self.guide_track_id = None
        self.session = CoachSession(cfg, on_note=lambda text: None)
        self._last_packets = 0
        self._last_packet_at = time.monotonic()
        self.session.start_background()
        self.go.setText(texts.HOME["stop"])
        if self.use_overlay.isChecked() and not cfg.replay:
            self.overlay = QtOverlay(scale=s.overlay_scale)
            self.overlay.show()

    def finish_session(self) -> None:
        if self.session is None:
            return
        session, self.session = self.session, None
        result = session.finish()
        if self.overlay is not None:
            self.overlay.close()
            self.overlay = None
        self.go.setText(texts.HOME["go"])
        lines = [texts.HOME["summary_title"]]
        if result.wall_s > 1 and not session.cfg.replay:
            lines.append(texts.HOME["cpu"].format(cpu=result.cpu_percent, wall=result.wall_s))
        if result.player_errors:
            lines.append(f"Głos: {len(result.player_errors)} błędów, pierwszy: {result.player_errors[0]}")
        if result.summary is not None:
            lines += [f"Dobrze:   {result.summary.good}", f"Do pracy: {result.summary.to_work}", ""]
        if not result.state.empty:
            source = str(session.cfg.replay) if session.cfg.replay else "okno"
            try:
                lines.append(report_laps(result.recorder, session.cfg.track, session.cfg.db, source, "best", session.cfg.replay))
            except Exception as exc:  # raport nie może zabić okna
                lines.append(f"Raport po sesji nie powstał: {exc}")
        self.summary.setPlainText("\n".join(lines))
        self.summary.show()
        self.ctx.start_probe()
        self.session_finished.emit()

    def shutdown(self) -> None:
        if self.session is not None:
            self.session.stop()
            self.finish_session()


# ---------------------------------------------------------------- Kreator
class WizardPage(QWidget):
    finished = Signal()

    def __init__(self, ctx: Context) -> None:
        super().__init__()
        self.ctx = ctx
        self.player: VoicePlayer | None = None
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.addWidget(label(texts.WIZARD["title"], "h1"))
        self.steps_label = label("", "muted")
        root.addWidget(self.steps_label)
        self.progress = QProgressBar()
        self.progress.setRange(0, len(texts.WIZARD["steps"]))
        root.addWidget(self.progress)
        self.stack = QStackedWidget()
        root.addWidget(self.stack, 1)
        nav = QHBoxLayout()
        self.back = QPushButton(texts.WIZARD["back"])
        self.next = QPushButton(texts.WIZARD["next"])
        self.back.clicked.connect(lambda: self.goto(self.stack.currentIndex() - 1))
        self.next.clicked.connect(self.on_next)
        nav.addWidget(self.back)
        nav.addStretch(1)
        nav.addWidget(self.next)
        root.addLayout(nav)
        self.stack.addWidget(self._telemetry_step())
        self.stack.addWidget(self._speakers_step())
        self.stack.addWidget(self._assists_step())
        self.stack.addWidget(self._driver_step())
        self.goto(0)

    def _table(self, rows: list[tuple[str, str]]) -> QWidget:
        grid = QGridLayout()
        for i, (k, v) in enumerate(rows):
            grid.addWidget(label(k, "muted"), i, 0)
            grid.addWidget(label(v), i, 1)
        w = QWidget()
        w.setLayout(grid)
        return w

    def _telemetry_step(self) -> QWidget:
        frame, lay = panel()
        lay.addWidget(label(texts.WIZARD["telemetry_intro"]))
        lay.addWidget(self._table(texts.WIZARD["telemetry_rows"]))
        self.check_btn = QPushButton(texts.WIZARD["check"])
        self.check_btn.clicked.connect(self.run_check)
        self.check_result = label("", "muted")
        lay.addWidget(self.check_btn, 0, Qt.AlignmentFlag.AlignLeft)
        lay.addWidget(self.check_result)
        lay.addStretch(1)
        return frame

    def run_check(self) -> None:
        self.check_btn.setEnabled(False)
        self.check_result.setText(texts.WIZARD["checking"])
        self.ctx.pause_probe()
        port = self.ctx.settings.port

        def work() -> None:
            self._probe_result = probe(port, 5.0)

        self._probe_result = None
        t = threading.Thread(target=work, daemon=True)
        t.start()
        timer = QTimer(self)
        timer.setInterval(200)

        def poll() -> None:
            if t.is_alive():
                return
            timer.stop()
            r = self._probe_result
            self.check_btn.setEnabled(True)
            self.ctx.start_probe()
            if r is None or r.busy:
                self.check_result.setText(texts.WIZARD["check_busy"])
            elif r.packets == 0:
                self.check_result.setText(texts.WIZARD["check_none"])
            elif not r.supported:
                self.check_result.setText(texts.WIZARD["check_format"].format(fmt=r.fmt))
            else:
                self.check_result.setText(texts.WIZARD["check_ok"].format(track=r.track or "tor nieznany", fmt=r.fmt, rate=int(r.rate)))

        timer.timeout.connect(poll)
        timer.start()

    def _speakers_step(self) -> QWidget:
        frame, lay = panel()
        lay.addWidget(label(texts.WIZARD["speakers_intro"]))
        play = QPushButton(texts.WIZARD["play"])
        play.clicked.connect(self.play_hello)
        self.speakers_result = label("", "muted")
        buttons = QHBoxLayout()
        heard = QPushButton(texts.WIZARD["heard"])
        not_heard = QPushButton(texts.WIZARD["not_heard"])
        heard.clicked.connect(lambda: self.speakers_result.setText("Dobrze. Głośność zmienisz w ustawieniach."))
        not_heard.clicked.connect(lambda: self.speakers_result.setText(
            "Sprawdź w Windows: Ustawienia → Dźwięk → urządzenie wyjściowe (słuchawki/głośniki), potem Odtwórz ponownie."))
        buttons.addWidget(play)
        buttons.addWidget(heard)
        buttons.addWidget(not_heard)
        buttons.addStretch(1)
        lay.addLayout(buttons)
        lay.addWidget(self.speakers_result)
        lay.addStretch(1)
        return frame

    def play_hello(self) -> None:
        library = ClipLibrary(Path(self.ctx.settings.voice_dir))
        if len(library) == 0:
            self.speakers_result.setText(texts.WIZARD["no_clips"].format(path=self.ctx.settings.voice_dir))
            return
        if self.player is None:
            self.player = VoicePlayer(library, volume=self.ctx.settings.volume).start()
        self.player.say(["misc_hello"], "test")
        self.speakers_result.setText("Odtwarzam...")

    def _assists_step(self) -> QWidget:
        frame, lay = panel()
        lay.addWidget(label(texts.WIZARD["assists_intro"]))
        lay.addWidget(self._table(texts.WIZARD["assists_rows"]))
        lay.addStretch(1)
        return frame

    def _driver_step(self) -> QWidget:
        frame, lay = panel()
        lay.addWidget(label(texts.WIZARD["driver_intro"]))
        self.nick = QLineEdit(self.ctx.settings.nick)
        self.nick.setPlaceholderText(texts.WIZARD["nick"])
        lay.addWidget(self.nick)
        lay.addStretch(1)
        return frame

    def goto(self, index: int) -> None:
        index = max(0, min(index, self.stack.count() - 1))
        self.stack.setCurrentIndex(index)
        self.progress.setValue(index + 1)
        names = texts.WIZARD["steps"]
        self.steps_label.setText(f"Krok {index + 1}/{len(names)}: {names[index]}")
        self.back.setEnabled(index > 0)
        self.next.setText(texts.WIZARD["finish"] if index == self.stack.count() - 1 else texts.WIZARD["next"])

    def on_next(self) -> None:
        if self.stack.currentIndex() == self.stack.count() - 1:
            self.ctx.settings.nick = self.nick.text().strip()
            self.ctx.settings.wizard_done = True
            self.ctx.save()
            if self.player is not None:
                self.player.close()
                self.player = None
            self.finished.emit()
        else:
            self.goto(self.stack.currentIndex() + 1)


# ---------------------------------------------------------------- Karta kierowcy
class PhotoLabel(QLabel):
    dropped = Signal(str)

    def __init__(self) -> None:
        super().__init__(texts.PROFILE["photo_hint"])
        self.setObjectName("panel2")
        self.setAcceptDrops(True)
        self.setFixedSize(200, 200)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setWordWrap(True)

    def dragEnterEvent(self, event) -> None:  # noqa: N802
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:  # noqa: N802
        for url in event.mimeData().urls():
            self.dropped.emit(url.toLocalFile())
            break

    def set_photo(self, path: str) -> None:
        pix = QPixmap(path)
        if pix.isNull():
            self.setText(texts.PROFILE["photo_hint"])
            return
        self.setPixmap(pix.scaled(self.size(), Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation))


IMAGE_SUFFIXES = (".png", ".jpg", ".jpeg", ".bmp", ".webp")


class ProfilePage(QWidget):
    def __init__(self, ctx: Context) -> None:
        super().__init__()
        self.ctx = ctx
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.addWidget(label(texts.PROFILE["title"], "h1"))
        card, card_lay = panel(self)
        top = QHBoxLayout()
        self.photo = PhotoLabel()
        self.photo.dropped.connect(self.use_photo)
        top.addWidget(self.photo)
        form = QGridLayout()
        self.nick = QLineEdit(ctx.settings.nick)
        self.id_label = label(ctx.settings.player_id, "cyan")
        form.addWidget(label(texts.PROFILE["nick"], "muted"), 0, 0)
        form.addWidget(self.nick, 0, 1)
        form.addWidget(label(texts.PROFILE["id"], "muted"), 1, 0)
        form.addWidget(self.id_label, 1, 1)
        self.choose = QPushButton(texts.PROFILE["choose_photo"])
        self.choose.setCheckable(True)
        self.choose.toggled.connect(self.toggle_browser)
        form.addWidget(self.choose, 2, 0, 1, 2)
        save = QPushButton(texts.PROFILE["save"])
        save.clicked.connect(self.save)
        self.saved = label("", "green")
        form.addWidget(save, 3, 0)
        form.addWidget(self.saved, 3, 1)
        top.addLayout(form, 1)
        card_lay.addLayout(top)
        # przeglądarka plików w oknie (bez osobnego okna dialogowego)
        self.model = QFileSystemModel(self)
        self.model.setNameFilters([f"*{s}" for s in IMAGE_SUFFIXES])
        self.model.setNameFilterDisables(False)
        self.tree = QTreeView()
        self.tree.setModel(self.model)
        self.tree.setMinimumHeight(220)
        for col in (1, 2, 3):
            self.tree.hideColumn(col)
        self.tree.doubleClicked.connect(self.pick_from_tree)
        self.tree.hide()
        card_lay.addWidget(self.tree)
        root.addWidget(card)
        stats_frame, stats_lay = panel(self)
        self.c_sessions = StatCard(texts.PROFILE["sessions"])
        self.c_laps = StatCard(texts.PROFILE["laps"])
        self.c_tracks = StatCard(texts.PROFILE["tracks"])
        cards = QHBoxLayout()
        for c in (self.c_sessions, self.c_laps, self.c_tracks):
            cards.addWidget(c)
        stats_lay.addLayout(cards)
        self.tracks_grid = QGridLayout()
        stats_lay.addLayout(self.tracks_grid)
        root.addWidget(stats_frame)
        root.addStretch(1)
        if ctx.settings.photo:
            self.photo.set_photo(ctx.settings.photo)
        self.reload()

    def toggle_browser(self, on: bool) -> None:
        if on:
            home = str(Path.home())
            self.model.setRootPath(home)
            self.tree.setRootIndex(self.model.index(home))
        self.tree.setVisible(on)

    def pick_from_tree(self, index) -> None:
        path = self.model.filePath(index)
        if Path(path).suffix.lower() in IMAGE_SUFFIXES:
            self.use_photo(path)
            self.choose.setChecked(False)

    def use_photo(self, path: str) -> None:
        src = Path(path)
        if not src.is_file() or src.suffix.lower() not in IMAGE_SUFFIXES:
            return
        dst = self.ctx.data_dir / f"profil{src.suffix.lower()}"
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)
        self.ctx.settings.photo = str(dst)
        self.ctx.save()
        self.photo.set_photo(str(dst))

    def save(self) -> None:
        self.ctx.settings.nick = self.nick.text().strip()
        self.ctx.save()
        self.saved.setText(texts.PROFILE["saved"])

    def reload(self) -> None:
        self.nick.setText(self.ctx.settings.nick)
        try:
            db = Database(self.ctx.db_path)
            ov = db.overview()
            steps = {}
            for t in ov["tracks"]:
                steps[t["track_id"]] = db.load_progress(t["track_id"]).step
            db.close()
        except Exception:
            ov, steps = {"sessions": 0, "laps": 0, "tracks": []}, {}
        self.c_sessions.set(str(ov["sessions"]))
        self.c_laps.set(str(ov["laps"]))
        self.c_tracks.set(str(len(ov["tracks"])))
        while self.tracks_grid.count():
            item = self.tracks_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        for i, t in enumerate(ov["tracks"]):
            try:
                name = load_track_by_id(t["track_id"]).name
            except FileNotFoundError:
                name = f"tor {t['track_id']}"
            self.tracks_grid.addWidget(label(name, "h2"), i, 0)
            self.tracks_grid.addWidget(label(f"{texts.PROFILE['best']}: {format_time(t['best_ms'])}"), i, 1)
            self.tracks_grid.addWidget(label(f"{t['laps']} okr., {t['sessions']} sesji", "muted"), i, 2)
            step = steps.get(t["track_id"], 1)
            self.tracks_grid.addWidget(label(f"{texts.PROFILE['step']}: {step} ({STEPS[step]})", "muted"), i, 3)


# ---------------------------------------------------------------- Postęp
class ProgressPage(QWidget):
    def __init__(self, ctx: Context) -> None:
        super().__init__()
        self.ctx = ctx
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.addWidget(label(texts.PROGRESS["title"], "h1"))
        self.track_box = QComboBox()
        self.track_box.currentIndexChanged.connect(self.show_track)
        root.addWidget(self.track_box, 0, Qt.AlignmentFlag.AlignLeft)
        self.empty = label(texts.PROGRESS["no_data"], "muted")
        root.addWidget(self.empty)
        frame, lay = panel(self)
        self.step_label = label("", "h2")
        self.streak_bar = QProgressBar()
        self.streak_bar.setRange(0, CLEAN_LAPS_TO_ADVANCE)
        self.streak_bar.setFormat("czyste okrążenia z rzędu: %v/%m")
        self.best_label = label("", "")
        self.mastered = label("", "green")
        self.todo = label("", "yellow")
        for w in (self.step_label, self.streak_bar, self.best_label, self.mastered, self.todo):
            lay.addWidget(w)
        root.addWidget(frame)
        self.table = QTableWidget(0, len(texts.PROGRESS["laps_table"]))
        self.table.setHorizontalHeaderLabels(texts.PROGRESS["laps_table"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setVisible(False)
        root.addWidget(self.table, 1)
        self.track_ids: list[int] = []
        self.reload()

    def reload(self) -> None:
        try:
            db = Database(self.ctx.db_path)
            tracks = db.overview()["tracks"]
            db.close()
        except Exception:
            tracks = []
        self.track_ids = [t["track_id"] for t in tracks]
        self.track_box.blockSignals(True)
        self.track_box.clear()
        for tid in self.track_ids:
            try:
                self.track_box.addItem(load_track_by_id(tid).name)
            except FileNotFoundError:
                self.track_box.addItem(f"tor {tid}")
        self.track_box.blockSignals(False)
        self.empty.setVisible(not tracks)
        if tracks:
            self.show_track(0)

    def show_track(self, index: int) -> None:
        if index < 0 or index >= len(self.track_ids):
            return
        tid = self.track_ids[index]
        db = Database(self.ctx.db_path)
        p = db.load_progress(tid)
        best = db.best_time_per_step(tid)
        issues = db.recent_corner_issues(tid)
        rows = db.lap_table(tid)
        db.close()
        self.step_label.setText(f"Krok {p.step}: {STEPS[p.step]}")
        self.streak_bar.setValue(min(p.streak, CLEAN_LAPS_TO_ADVANCE))
        self.best_label.setText("  |  ".join(f"krok {s} ({STEPS[s]}): {format_time(ms)}" for s, ms in sorted(best.items())) or "")
        try:
            track = load_track_by_id(tid)
            mastered = [c.name for c in track.corners if c.number not in issues]
            todo = [f"{c.name} ({', '.join(sorted(set(issues[c.number])))})" for c in track.corners if c.number in issues]
        except FileNotFoundError:
            mastered, todo = [], []
        self.mastered.setText(f"{texts.PROGRESS['mastered']}: {', '.join(mastered) or texts.PROGRESS['none_yet']}")
        self.todo.setText(f"{texts.PROGRESS['todo']}: {'; '.join(todo)}" if todo else "")
        self.table.setRowCount(len(rows))
        tc_names = {0: "wył.", 1: "średnia", 2: "pełna"}
        gb_names = {1: "ręczna", 2: "ręczna+sug.", 3: "automat"}
        for r, row in enumerate(rows):
            cells = [
                row["created_at"][:16].replace("T", " "), str(row["number"]), format_time(row["lap_time_ms"]),
                "tak" if row["valid"] else "nie", tc_names.get(row["traction_control"], "-"),
                "wł." if row["abs_on"] else "wył.", gb_names.get(row["gearbox"], "-"),
            ]
            for c, text in enumerate(cells):
                item = QTableWidgetItem(text)
                item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                self.table.setItem(r, c, item)
        self.table.resizeColumnsToContents()


# ---------------------------------------------------------------- Ustawienia
class SettingsPage(QWidget):
    tutorial_requested = Signal()
    wizard_requested = Signal()

    def __init__(self, ctx: Context) -> None:
        super().__init__()
        self.ctx = ctx
        s = ctx.settings
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.addWidget(label(texts.SETTINGS["title"], "h1"))
        frame, lay = panel(self)
        grid = QGridLayout()
        self.volume = QSlider(Qt.Orientation.Horizontal)
        self.volume.setRange(5, 30)
        self.volume.setValue(int(s.volume * 10))
        self.volume_label = label(f"{s.volume:.1f}")
        self.volume.valueChanged.connect(lambda v: self.volume_label.setText(f"{v / 10:.1f}"))
        self.scale = QDoubleSpinBox()
        self.scale.setRange(0.6, 2.0)
        self.scale.setSingleStep(0.1)
        self.scale.setValue(s.overlay_scale)
        self.port = QSpinBox()
        self.port.setRange(1024, 65535)
        self.port.setValue(s.port)
        self.voice_dir = QLineEdit(s.voice_dir)
        grid.addWidget(label(texts.SETTINGS["volume"]), 0, 0)
        grid.addWidget(self.volume, 0, 1)
        grid.addWidget(self.volume_label, 0, 2)
        grid.addWidget(label(texts.SETTINGS["overlay_scale"]), 1, 0)
        grid.addWidget(self.scale, 1, 1)
        grid.addWidget(label(texts.SETTINGS["port"]), 2, 0)
        grid.addWidget(self.port, 2, 1)
        grid.addWidget(label(texts.SETTINGS["voice_dir"]), 3, 0)
        grid.addWidget(self.voice_dir, 3, 1, 1, 2)
        lay.addLayout(grid)
        buttons = QHBoxLayout()
        save = QPushButton(texts.SETTINGS["save"])
        save.clicked.connect(self.save)
        tut = QPushButton(texts.SETTINGS["tutorial"])
        tut.clicked.connect(self.tutorial_requested.emit)
        wiz = QPushButton(texts.SETTINGS["wizard"])
        wiz.clicked.connect(self.wizard_requested.emit)
        self.saved = label("", "green")
        for b in (save, tut, wiz):
            buttons.addWidget(b)
        buttons.addWidget(self.saved)
        buttons.addStretch(1)
        lay.addLayout(buttons)
        root.addWidget(frame)
        root.addStretch(1)

    def save(self) -> None:
        s = self.ctx.settings
        s.volume = self.volume.value() / 10
        s.overlay_scale = self.scale.value()
        s.port = self.port.value()
        s.voice_dir = self.voice_dir.text().strip() or "assets/voice"
        self.ctx.save()
        self.saved.setText("Zapisano")
