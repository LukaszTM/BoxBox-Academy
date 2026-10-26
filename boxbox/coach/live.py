"""Trener na żywo: komunikat po zakręcie i podsumowanie po okrążeniu, jako listy klipów + tekst.

Silnik nie odtwarza dźwięku; woła `speak(ids, text)`, które aplikacja podpina
pod odtwarzacz i konsolę. Referencja: najlepsze ważne okrążenie (z bazy albo
z bieżącej sesji); bez referencji trener tylko zapisuje pierwsze okrążenie.
"""
from collections.abc import Callable
from dataclasses import dataclass, field

from boxbox.coach.corners import LapAnalysis, analyze_corner, analyze_lap
from boxbox.coach.laps import Lap, LapRecorder
from boxbox.coach.rules import MIN_TIME_LOSS_S, Message, biggest_loss, evaluate_corner, evaluate_lap, pick_top
from boxbox.tracks.model import Track
from boxbox.voice.phrases import MISC_TEXTS, utterance

CORNER_EXIT_MARGIN_M = 25.0  # tyle metrów za wyjściem z zakrętu najwcześniej mówimy o nim
CORNER_EXIT_DEADLINE_M = 150.0  # najpóźniej tu: gdy pełny gaz jeszcze nie przyszedł, czekamy do tego miejsca (~2 s)
Speak = Callable[[list[str], str], None]


@dataclass
class LiveCoach:
    track: Track
    speak: Speak
    reference: LapAnalysis | None = None
    corner_messages: bool = True
    min_corner_weight: float = MIN_TIME_LOSS_S
    announced: set[tuple[int, int]] = field(default_factory=set)  # (okrążenie, zakręt) już skomentowane
    best_time_ms: int | None = None
    said_hello: bool = False
    said_out_lap: bool = False
    available: Callable[[str], bool] | None = None  # czy klip o id jest w bibliotece (wybór v2/v1)

    def _say_misc(self, key: str) -> None:
        self.speak([f"misc_{key}"], MISC_TEXTS[key])

    def update(self, recorder: LapRecorder, finished: Lap | None) -> list[Message]:
        """Wołane po każdym pakiecie. Zwraca komunikaty wypowiedziane w tym kroku."""
        out: list[Message] = []
        if not self.said_hello and recorder.state.lap is not None:
            self.said_hello = True
            self._say_misc("hello")
            if self.reference is not None:
                self._say_misc("reference_loaded")
        if not self.said_out_lap and recorder.current is not None and recorder.current.pitted:
            self.said_out_lap = True
            self._say_misc("out_lap")
        if finished is not None:
            out += self._on_lap_finished(finished)
        if self.corner_messages and self.reference is not None and recorder.current is not None:
            out += self._on_progress(recorder.current)
        return out

    def _on_progress(self, lap: Lap) -> list[Message]:
        if not lap.samples or lap.pitted:
            return []
        distance = lap.samples[-1].distance_m
        ref = {c.corner: c for c in self.reference.corners} if self.reference else {}
        out: list[Message] = []
        for corner in self.track.corners:
            key = (lap.number, corner.number)
            if key in self.announced or corner.number not in ref or corner.exit_m < corner.entry_m:
                continue  # zakręt przez linię mety dostaje tylko podsumowanie
            if distance < corner.exit_m + CORNER_EXIT_MARGIN_M:
                continue
            metrics = analyze_corner(lap, corner, self.track)
            if metrics is None:
                self.announced.add(key)
                continue
            # pełny gaz po apeksie jeszcze nie przyszedł: poczekaj, ale nie dłużej niż do deadline'u
            if metrics.full_throttle_m is None and distance < corner.exit_m + CORNER_EXIT_DEADLINE_M:
                continue
            self.announced.add(key)
            msgs = evaluate_corner(lap.number, metrics, ref[corner.number], self.track, lap.traction_control)
            best = max(msgs, key=lambda m: m.weight, default=None)
            if best is not None and best.weight >= self.min_corner_weight:
                self.speak(*utterance(best, self.available, short=True))
                out.append(best)
        return out

    def _on_lap_finished(self, lap: Lap) -> list[Message]:
        if lap.pitted or not lap.is_complete(self.track.length_m):
            return []
        analysis = analyze_lap(lap, self.track)
        out: list[Message] = []
        usable = not lap.invalid and lap.lap_time_ms is not None
        if self.reference is None:
            if usable:
                self.reference = analysis
                self.best_time_ms = lap.lap_time_ms
                self._say_misc("no_reference")
            return []
        if lap.invalid:
            self._say_misc("lap_invalid")
        messages = evaluate_lap(lap, analysis, self.reference, self.track)
        top = pick_top(messages)
        if top:
            self._say_misc("lap_summary")
            for m in top:
                self.speak(*utterance(m, self.available))
            out += top
        elif not lap.invalid:
            soft = biggest_loss(messages)
            if soft is not None:
                ids, text = utterance(soft, self.available)
                self.speak(["misc_biggest_loss", *ids], f"{MISC_TEXTS['biggest_loss']} {text}")
                out.append(soft)
            else:
                self._say_misc("lap_clean")
        if usable and (self.best_time_ms is None or lap.lap_time_ms < self.best_time_ms):  # type: ignore[operator]
            self.best_time_ms = lap.lap_time_ms
            self.reference = analysis
            self._say_misc("lap_best")
        return out

    def finish(self) -> None:
        self._say_misc("session_end")
