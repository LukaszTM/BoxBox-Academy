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

from boxbox.coach.guide_live import is_urgent_cue
from boxbox.coach.laps import Lap, LapRecorder
from boxbox.coach.lessons import Lesson
from boxbox.coach.lessons import evaluate as evaluate_lesson
from boxbox.coach.lessons import lesson as lesson_by_id
from boxbox.coach.live import LiveCoach
from boxbox.coach.progress import CLEAN_LAPS_TO_ADVANCE, STEPS
from boxbox.coach.rules import Message
from boxbox.coach.summary import SessionSummary, summarize
from boxbox.engineer.rules import Engineer
from boxbox.engineer.summary import RaceSummary, summarize_race
from boxbox.storage.db import Database
from boxbox.telemetry.record import recording_path
from boxbox.telemetry.recording import RecordingWriter, is_needed
from boxbox.telemetry.replay import replay
from boxbox.telemetry.state import TelemetryState
from boxbox.telemetry.udp import DEFAULT_PORT, listen
from boxbox.tracks.atlas import ShapeSampler, fit_path, load_atlas
from boxbox.tracks.atlas import fit as fit_atlas
from boxbox.tracks.auto import save_auto_track, track_from_lap
from boxbox.tracks.model import USER_TRACK_DIR, Track, find_track_path, load_track, track_path, user_track_path
from boxbox.tracks.shape import build_shape, save_shape, shape_path
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
    corner_guidance: bool = True  # prowadzenie w nieopanowanych zakrętach: puść gaz, hamuj, pół gazu, pełny gaz
    lesson: str | None = None  # id lekcji (boxbox/coach/lessons.py); trener mówi tylko o jej regułach
    lesson_corner: int | None = None
    explain_mode: bool = False  # dłuższe wyjaśnienie przy pierwszej uwadze danego typu
    shape_dir: Path | None = None  # dokąd zapisać realny kształt toru z pełnego okrążenia (None = nie zapisuj)
    fit_dir: Path | None = None  # dokąd zapisać dopasowanie atlasu, gdy okrążenie niepełne (None = nie zapisuj)
    auto_track_dir: Path | None = USER_TRACK_DIR  # tor bez pliku: zakręty z 1. pełnego okrążenia lądują tu (None = tylko w pamięci)


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
    race: RaceSummary | None = None  # tryb wyścigowy


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
        self.track_source = ""  # "pakiet" | "automatyczny" (plik z data/tracks) | "sesja" (wyznaczony teraz) | "własny" (--track)
        self.track_pending = False  # brak pliku toru: czekamy na pierwsze pełne okrążenie
        self._auto_track_tries = 0
        self.engineer: Engineer | None = Engineer() if cfg.mode == "race" else None
        self.writer: RecordingWriter | None = None
        self.recording: Path | None = None
        self._rec_start = time.monotonic()
        self._t0 = time.monotonic()
        self._wall0 = self._cpu0 = 0.0
        self.result: SessionResult | None = None
        self.thread: threading.Thread | None = None
        self.shape_sampler = ShapeSampler()  # pozycja auta do mapy toru (kształt albo dopasowanie atlasu)

    # --- przygotowanie -------------------------------------------------
    def make_player(self) -> VoicePlayer | None:
        cfg = self.cfg
        if cfg.mode not in ("coach", "race") or cfg.no_voice or (cfg.replay and cfg.speed <= 0):
            return None
        library = ClipLibrary(cfg.voice)
        if len(library) == 0:
            self.on_note(f"Brak klipów głosu w {cfg.voice}; komunikaty tylko w konsoli.")
            return None
        player = VoicePlayer(library, volume=max(0.1, cfg.volume)).start()
        if cfg.mode == "coach":
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
            # wskazówka w zakręcie ("Hamuj mocno.") musi wybrzmieć w porę: przerywa to, co właśnie leci
            self.player.say(ids, text, urgent=is_urgent_cue(ids))

    def note(self, text: str) -> None:
        """Informacja bez głosu: konsola przez on_note, okno i nakładka przez listę komunikatów sesji."""
        self.on_note(text)
        self.shared.messages.append(text)
        self.messages.append((time.monotonic() - self._t0, text))

    def _track_file(self) -> Path:
        cfg, st = self.cfg, self.state.session
        assert st is not None
        return cfg.track or find_track_path(st.track_id, user_dir=cfg.auto_track_dir or USER_TRACK_DIR)

    def _auto_track(self, finished: Lap | None) -> Track | None:
        """Tor bez pliku: zakręty z pierwszego pełnego okrążenia (jak boxbox.tracks.detect), zapis do data/tracks."""
        st = self.state.session
        assert st is not None
        if finished is None:
            return None
        track = track_from_lap(finished, st.track_id, st.track_name, float(st.track_length_m),
                               source=f"sesja {datetime.now():%Y-%m-%d}, okrążenie {finished.number}")
        if track is None:
            if finished.is_complete(float(st.track_length_m)) and not finished.pitted:
                self._auto_track_tries += 1
                if self._auto_track_tries >= 3:
                    self.coach_failed = True
                    self.shared.error = f"nie udało się wyznaczyć zakrętów toru {st.track_name}: trener wyłączony"
                    self.note(f"Nie udało się wyznaczyć zakrętów toru {st.track_name} z {self._auto_track_tries} okrążeń: trener na żywo wyłączony.")
                    log.error("tor %s: brak zakrętów po %d pełnych okrążeniach", st.track_id, self._auto_track_tries)
            return None
        path = self.cfg.track or (user_track_path(st.track_id, user_dir=self.cfg.auto_track_dir) if self.cfg.auto_track_dir else None)
        where = ""
        if path is not None:
            try:
                save_auto_track(track, path)
                where = f", plik {path}"
            except OSError as exc:  # brak zapisu nie blokuje trenera w tej sesji
                log.error("zapis pliku toru %s: %s", path, exc)
        self.track_source = "sesja"
        self.track_pending = False
        self.note(f"Zakręty toru {st.track_name} wyznaczone z okrążenia {finished.number}: {len(track.corners)} stref hamowania{where}. Trener aktywny.")
        log.info("tor %s: %d zakrętów wyznaczonych z okrążenia %d%s", st.track_id, len(track.corners), finished.number, where)
        return track

    def ensure_coach(self, finished: Lap | None = None) -> None:
        """Trener startuje, gdy znamy tor (pakiet Session): plik toru + referencja z bazy.

        Bez pliku toru czeka na pierwsze pełne okrążenie i wyznacza zakręty z niego (`finished`).
        """
        if self.coach is not None or self.coach_failed or self.state.session is None:
            return
        cfg = self.cfg
        path = self._track_file()
        try:
            track = load_track(path)
            self.track_source = "własny" if cfg.track else ("pakiet" if path == track_path(self.state.session.track_id) else "automatyczny")
        except FileNotFoundError:
            if not self.track_pending:
                self.track_pending = True
                self.note(f"Brak pliku toru {path}: zakręty wyznaczę po pierwszym pełnym okrążeniu, wtedy startuje trener.")
                log.warning("brak pliku toru %s (tor %s): czekam na pełne okrążenie", path, self.state.session.track_id)
            track = self._auto_track(finished)
            if track is None:
                return
        reference = best_time = progress = None
        guided: set[int] = set()
        if cfg.db is not None:
            db = Database(cfg.db)
            ref = db.reference(track.track_id)
            progress = db.load_progress(track.track_id)
            issues = db.recent_corner_issues(track.track_id)
            db.close()
            if ref is not None:
                reference, best_time = ref.analysis, ref.lap.lap_time_ms
                self.reference_before, self.best_before_ms = ref.corners, ref.lap.lap_time_ms
            # zakręty z uwagami w ostatnich okrążeniach poprzednich sesji dostają prowadzenie od razu
            guided = set(sorted(issues, key=lambda c: -len(issues[c]))[:3])
        if progress is not None:
            self.shared.progress_line = progress_line(progress.step, progress.streak)
        log.info("trener: tor %s (%s), referencja %s, krok %s", track.name, path,
                 f"{best_time} ms" if best_time else "brak", progress.step if progress else "-")
        self.coach = LiveCoach(
            track, self.speak, reference, corner_messages=cfg.corner_messages, best_time_ms=best_time,
            said_hello=self.player is not None,  # powitanie poszło już na starcie
            available=(lambda i: i in self.player.library) if self.player is not None else None,
            progress=progress, lesson=self.lesson, lesson_corner=cfg.lesson_corner, explain_mode=cfg.explain_mode,
            guidance=cfg.corner_guidance, guided_corners=guided,
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
            self.shape_sampler.feed(self.state)
            if self.engineer is not None:
                for radio in self.engineer.update(self.state, time.monotonic() - self._t0):
                    self.speak(list(radio.ids), radio.text)
            if self.cfg.mode == "coach":
                self.ensure_coach(finished)
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
        race = None
        if self.engineer is not None and self.state.lap is not None:
            lap = self.state.lap.player
            race = summarize_race(self.state, self.engineer.start_report, self.engineer.collisions, self.engineer.penalties, lap.total_warnings, lap.num_pit_stops)
            log.info("wyścig: %s", " | ".join(race.lines))
        self.save_track_shape()
        self.result = SessionResult(self.state, self.recorder, wall, cpu_percent, self.coach is not None, errors, self.recording, summary, lesson_result, race)
        return self.result

    def save_track_shape(self) -> Path | None:
        """Po sesji: realny kształt toru z pełnego okrążenia (jak recorder) albo dopasowanie atlasu z przejechanych metrów."""
        cfg, st = self.cfg, self.state
        if st.session is None or (cfg.shape_dir is None and cfg.fit_dir is None):
            return None
        track_id, length = st.session.track_id, float(st.session.track_length_m)
        if length <= 0:
            return None
        try:
            track = self.coach.track if self.coach is not None else None
            if cfg.shape_dir is not None:
                full = self.shape_sampler.complete_lap(length)
                if full is not None:
                    shape = build_shape(full, track_id, st.session.track_name, length, track)
                    path = shape_path(track_id, cfg.shape_dir)
                    save_shape(shape, path)
                    log.info("kształt toru %d zapisany z sesji: %s (%d punktów)", track_id, path, len(shape.points))
                    return path
            if cfg.fit_dir is not None:
                atlas = load_atlas(track_id)
                if atlas is not None and not fit_path(track_id, cfg.fit_dir).exists():
                    fit_ = fit_atlas(atlas, self.shape_sampler.all_samples(), length)
                    if fit_ is not None:
                        path = fit_path(track_id, cfg.fit_dir)
                        fit_.save(path)
                        log.info("obrys toru %d dopasowany do gry: błąd %.1f m, %d próbek", track_id, fit_.error_m, fit_.samples)
                        return path
        except Exception:  # mapa nie może zepsuć zakończenia sesji
            log.error("kształt toru: %s", traceback.format_exc())
        return None
