"""Sesja trenera niezależna od interfejsu: telemetria (UDP albo nagranie) -> okrążenia -> trener -> komunikaty.

Konsola (`boxbox.app`) i okno (`boxbox.gui`) używają tej samej klasy. Interfejs tylko czyta
`shared` pod blokadą i dostaje wywołania zwrotne `on_message` / `on_packet`; nic nie liczy.
"""
import logging
import os
import threading
import time
import traceback
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from boxbox.coach.laps import LapRecorder
from boxbox.coach.lessons import Lesson, evaluate as evaluate_lesson, lesson as lesson_by_id
from boxbox.coach.live import LiveCoach
from boxbox.coach.progress import CLEAN_LAPS_TO_ADVANCE, STEPS
from boxbox.coach.rules import Message
from boxbox.coach.summary import SessionSummary, summarize
from boxbox.storage.db import Database
from boxbox.telemetry.record import recording_path
from boxbox.telemetry.recording import RecordingWriter, is_needed
from boxbox.telemetry.replay import replay
from boxbox.telemetry.state import TelemetryState
from boxbox.telemetry.udp import DEFAULT_PORT, listen
from boxbox.tracks.model import load_track, track_path
from boxbox.ui.overlay_model import SharedCoachState
from boxbox.voice.player import ClipLibrary, VoicePlayer

log = logging.getLogger("boxbox")
DEFAULT_DB = Path("data") / "boxbox.sqlite"
DEFAULT_VOICE = Path("assets") / "voice"


class Stopped(Exception):
    """Sesję zatrzymano z zewnątrz (okno, nakładka) w trakcie odtwarzania."""


def progress_line(step: int, streak: int) -> str:
    nxt = STEPS.get(step + 1)
    goal = f"Cel: {CLEAN_LAPS_TO_ADVANCE} czyste okrążenia z rzędu ({streak}/{CLEAN_LAPS_TO_ADVANCE})"
    return goal + (f", potem: {nxt}" if nxt else ", jedziesz bez asyst: pracujemy nad czasem") + f" | teraz: {STEPS[step]}"


def next_lap_target(m: Message) -> str:
    """Mały, osiągalny krok na następne okrążenie zamiast całej różnicy do referencji: połowa, 5–20 m."""
    if m.value_m is None:
        return ""
    step = int(min(20, max(5, round(m.value_m / 2 / 5) * 5)))
    if m.rule in ("brake_late", "brake_late_big"):
        return f"hamuj {step} m wcześniej"
    if m.rule == "brake_early":
        return f"hamuj {step} m później"
    if m.rule == "throttle_late":
        return f"pełny gaz {step} m wcześniej"
    return ""


def focus_line(messages: list[Message]) -> str:
    """Co poprawić na następnym okrążeniu: największa strata z podsumowania, jako konkretny cel."""
    big = [m for m in messages if m.corner]
    if not big:
        return ""
    m = max(big, key=lambda x: x.weight)
    target = next_lap_target(m)
    what = target or m.problem.rstrip(".").lower()
    return f"Na tym okrążeniu popraw: {m.corner_name}, {what}"


@dataclass
class SessionConfig:
    mode: str = "coach"
    replay: Path | None = None
    speed: float = 1.0
    port: int = DEFAULT_PORT
    duration: float | None = None
    track: Path | None = None
    db: Path | None = DEFAULT_DB
    record: str | None = None
    recordings_dir: Path = Path("recordings")
    voice: Path = DEFAULT_VOICE
    no_voice: bool = False
    volume: float = 1.0
    corner_messages: bool = True
    lesson: str | None = None  # id lekcji (boxbox/coach/lessons.py); trener mówi tylko o jej regułach
    lesson_corner: int | None = None
    explain_mode: bool = False  # dłuższe wyjaśnienie przy pierwszej uwadze danego typu


@dataclass
class SessionResult:
    state: TelemetryState
    recorder: LapRecorder
    wall_s: float
    cpu_percent: float
    coach_started: bool
    player_errors: list[str] = field(default_factory=list)
    recording: Path | None = None
    summary: SessionSummary | None = None  # Dobrze / Do pracy (tylko tryb nauki z trenerem)
    lesson_result: tuple[bool, int, int] | None = None  # (zaliczona, najlepsza seria, wymagana)


class CoachSession:
    def __init__(
        self, cfg: SessionConfig,
        on_message: Callable[[list[str], str], None] | None = None,
        on_note: Callable[[str], None] | None = None,
        on_packet: Callable[[TelemetryState], None] | None = None,
    ) -> None:
        self.cfg = cfg
        self.on_message = on_message
        self.on_note = on_note or (lambda text: None)
        self.on_packet = on_packet
        self.recorder = LapRecorder()
        self.state = self.recorder.state
        self.shared = SharedCoachState(self.state, recording_name=cfg.record if not cfg.replay else None)
        self.messages: list[tuple[float, str]] = []  # (sekundy od startu, tekst), pod shared.lock
        self.lap_messages: list[Message] = []  # wszystkie uwagi z okrążeń (do podsumowania sesji)
        self.reference_before: tuple | None = None  # metryki referencji z bazy sprzed sesji
        self.best_before_ms: int | None = None
        self.lesson: Lesson | None = lesson_by_id(cfg.lesson) if cfg.lesson else None
        self.messages_by_lap: dict[int, list[Message]] = {}
        self.player: VoicePlayer | None = None
        self.coach: LiveCoach | None = None
        self.coach_failed = False
        self.writer: RecordingWriter | None = None
        self.recording: Path | None = None
        self._rec_start = time.monotonic()
        self._t0 = time.monotonic()
        self._wall0 = self._cpu0 = 0.0
        self.result: SessionResult | None = None
        self.thread: threading.Thread | None = None

    # --- przygotowanie -------------------------------------------------
    def make_player(self) -> VoicePlayer | None:
        cfg = self.cfg
        if cfg.mode != "coach" or cfg.no_voice or (cfg.replay and cfg.speed <= 0):
            return None
        library = ClipLibrary(cfg.voice)
        if len(library) == 0:
            self.on_note(f"Brak klipów głosu w {cfg.voice}; komunikaty tylko w konsoli.")
            return None
        player = VoicePlayer(library, volume=max(0.1, cfg.volume)).start()
        player.say(["misc_hello"], "test dźwięku")  # od razu po starcie: słychać, zanim wyjedziesz na tor
        self.on_note(f"Głos: {len(library)} klipów, backend {player.backend.name}. Powinieneś teraz słyszeć powitanie.")
        log.info("głos: %d klipów, backend %s, głośność %.1f", len(library), player.backend.name, cfg.volume)
        return player

    def speak(self, ids: list[str], text: str) -> None:
        log.info("mechanik: %s  [%s]", text, " ".join(ids))
        self.shared.messages.append(text)  # pod blokadą: wywoływane z handle()
        self.messages.append((time.monotonic() - self._t0, text))
        if self.on_message is not None:
            self.on_message(ids, text)
        if self.player is not None:
            self.player.say(ids, text)

    def ensure_coach(self) -> None:
        """Trener startuje, gdy znamy tor (pakiet Session): plik toru + referencja z bazy."""
        if self.coach is not None or self.coach_failed or self.state.session is None:
            return
        cfg = self.cfg
        path = cfg.track or track_path(self.state.session.track_id)
        try:
            track = load_track(path)
        except FileNotFoundError:
            self.coach_failed = True
            self.on_note(f"Brak pliku toru {path}: trener na żywo wyłączony (tabela po sesji nadal będzie).")
            log.error("brak pliku toru %s (tor %s)", path, self.state.session.track_id)
            self.shared.error = f"brak pliku toru dla {self.state.session.track_name}: trener wyłączony"
            return
        reference = best_time = progress = None
        if cfg.db is not None:
            db = Database(cfg.db)
            ref = db.reference(track.track_id)
            progress = db.load_progress(track.track_id)
            db.close()
            if ref is not None:
                reference, best_time = ref.analysis, ref.lap.lap_time_ms
                self.reference_before, self.best_before_ms = ref.corners, ref.lap.lap_time_ms
        if progress is not None:
            self.shared.progress_line = progress_line(progress.step, progress.streak)
        log.info("trener: tor %s (%s), referencja %s, krok %s", track.name, path,
                 f"{best_time} ms" if best_time else "brak", progress.step if progress else "-")
        self.coach = LiveCoach(
            track, self.speak, reference, corner_messages=cfg.corner_messages, best_time_ms=best_time,
            said_hello=self.player is not None,  # powitanie poszło już na starcie
            available=(lambda i: i in self.player.library) if self.player is not None else None,
            progress=progress, lesson=self.lesson, lesson_corner=cfg.lesson_corner, explain_mode=cfg.explain_mode,
        )

    # --- przetwarzanie --------------------------------------------------
    def handle(self, data: bytes) -> None:
        if self.shared.stop.is_set():
            raise Stopped
        if self.writer is not None and is_needed(data):
            if self.writer.count == 0:
                self._rec_start = time.monotonic()
            self.writer.write(time.monotonic() - self._rec_start, data)
        with self.shared.lock:
            finished = self.recorder.feed(data)
            self.shared.packets += 1
            if self.cfg.mode == "coach":
                self.ensure_coach()
                if self.coach is not None:
                    said = self.coach.update(self.recorder, finished)
                    if finished is not None:
                        log.info("okrążenie %d: %s, %d komunikatów", finished.number,
                                 f"{finished.lap_time_ms} ms" if finished.lap_time_ms else "bez czasu", len(said))
                        self.lap_messages += [m for m in said if m.corner]
                        self.messages_by_lap[finished.number] = [m for m in said if m.corner]
                        self.shared.focus_line = focus_line(said)
                        if self.coach.progress is not None:
                            self.shared.progress_line = progress_line(self.coach.progress.step, self.coach.progress.streak)
        if self.on_packet is not None:
            self.on_packet(self.state)

    def _open_writer(self) -> None:
        cfg = self.cfg
        if cfg.record and not cfg.replay:
            path = recording_path(cfg.recordings_dir, cfg.record.replace(" ", "-"), datetime.now())
            path.parent.mkdir(parents=True, exist_ok=True)
            self.writer = RecordingWriter(path)
            self.recording = path
            self.on_note(f"Nagrywam sesję do {path}")

    def loop(self) -> None:
        """Pętla telemetrii; wołana w wątku (okno, nakładka) albo wprost (konsola)."""
        cfg = self.cfg
        try:
            if cfg.replay:
                replay(cfg.replay, self.handle, speed=cfg.speed)
            else:
                for data in listen(cfg.port, duration=cfg.duration, stop=self.shared.stop):
                    self.handle(data)
        except Stopped:
            pass
        except OSError as exc:
            self.shared.error = f"port {cfg.port}: {exc}"
            self.on_note(self.shared.error)
            log.error("telemetria: %s", self.shared.error)
        except Exception:
            self.shared.error = "błąd w trenerze (szczegóły w dzienniku data/boxbox.log)"
            self.on_note(self.shared.error)
            log.error("wątek telemetrii: %s", traceback.format_exc())
        finally:
            self.shared.stop.set()
            if self.writer is not None:
                self.writer.close()

    # --- cykl życia -------------------------------------------------------
    def start(self) -> None:
        """Przygotowanie (głos, nagrywanie) bez pętli; potem `loop()` albo `start_background()`."""
        self._t0 = time.monotonic()
        self.player = self.make_player()
        self._open_writer()
        self._wall0, self._cpu0 = time.monotonic(), sum(os.times()[:2])

    def start_background(self) -> threading.Thread:
        self.start()
        self.thread = threading.Thread(target=self.loop, daemon=True, name="boxbox-telemetria")
        self.thread.start()
        return self.thread

    def stop(self) -> None:
        self.shared.stop.set()

    @property
    def running(self) -> bool:
        return self.thread is not None and self.thread.is_alive()

    def finish(self) -> SessionResult:
        """Po zakończeniu pętli: zamyka trenera i głos, liczy obciążenie. Idempotentne."""
        if self.result is not None:
            return self.result
        if self.thread is not None:
            self.shared.stop.set()
            self.thread.join(timeout=5)
        wall = time.monotonic() - self._wall0
        cpu = sum(os.times()[:2]) - self._cpu0
        cpu_percent = 100 * cpu / wall if wall > 0 else 0.0
        if not self.cfg.replay and wall > 1:
            log.info("obciążenie %.1f%% przez %.0f s, pakietów %d, trener %s", cpu_percent, wall,
                     sum(self.state.packets.values()), "aktywny" if self.coach is not None else "nie wystartował")
        if self.coach is not None:
            self.coach.finish()
        errors: list[str] = []
        if self.player is not None:
            self.player.close()
            errors = list(self.player.errors)
        summary = None
        if self.coach is not None:
            laps = self.recorder.laps
            best_now = None
            if self.coach.reference is not None and self.coach.best_time_ms is not None:
                best_now = self.coach.reference  # po sesji referencja = najlepsze okrążenie sesji albo z bazy
            try:
                summary = summarize(laps, self.lap_messages, self.coach.track, best_now, self.reference_before, self.best_before_ms)
            except Exception:  # podsumowanie nie może zepsuć zakończenia sesji
                log.error("podsumowanie: %s", traceback.format_exc())
            if summary is not None:
                log.info("podsumowanie: dobrze: %s | do pracy: %s", summary.good, summary.to_work)
        lesson_result = None
        if self.lesson is not None and self.coach is not None:
            lesson_result = evaluate_lesson(self.lesson, self.recorder.laps, self.messages_by_lap, self.cfg.lesson_corner)
            log.info("lekcja %s: %s, seria %d/%d", self.lesson.id, "zaliczona" if lesson_result[0] else "nie", lesson_result[1], lesson_result[2])
        self.result = SessionResult(self.state, self.recorder, wall, cpu_percent, self.coach is not None, errors, self.recording, summary, lesson_result)
        return self.result
