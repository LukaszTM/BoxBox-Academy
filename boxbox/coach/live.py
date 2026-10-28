"""Trener na żywo: komunikat po zakręcie i podsumowanie po okrążeniu, jako listy klipów + tekst.

Silnik nie odtwarza dźwięku; woła `speak(ids, text)`, które aplikacja podpina
pod odtwarzacz i konsolę. Referencja: najlepsze ważne okrążenie (z bazy albo
z bieżącej sesji); bez referencji trener tylko zapisuje pierwsze okrążenie.
"""
from collections.abc import Callable
from dataclasses import dataclass, field

from boxbox.coach.corners import LapAnalysis, analyze_corner, analyze_lap
from boxbox.coach.ers import advise_ers, analyze_ers
from boxbox.coach.glossary import explain
from boxbox.coach.guide_live import KINDS, CornerGuide, kinds_for_rules
from boxbox.coach.lessons import Lesson, filter_messages
from boxbox.coach.progress import TrackProgress
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
    progress: TrackProgress | None = None  # ścieżka zdejmowania asyst (z bazy); None = bez śledzenia
    ers_advice: bool = True
    lesson: Lesson | None = None  # lekcja: trener mówi tylko o jej regułach (i zakręcie)
    lesson_corner: int | None = None
    explain_mode: bool = False  # "wytłumacz mi": przy pierwszej uwadze danego typu dłuższe wyjaśnienie
    explained: set[str] = field(default_factory=set)
    guidance: bool = True  # prowadzenie w nieopanowanych zakrętach (komendy przed punktem z referencji)
    guided_corners: set[int] = field(default_factory=set)  # zakręty do prowadzenia na start (np. z poprzednich sesji)
    guide: CornerGuide = field(init=False)

    def __post_init__(self) -> None:
        kinds = kinds_for_rules(self.lesson.rules) if self.lesson is not None else frozenset(KINDS)
        self.guide = CornerGuide(self.track, self.reference, kinds=kinds)
        self.guide.set_guided(sorted(self.guided_corners) if self.lesson_corner is None else [self.lesson_corner])

    def _say_misc(self, key: str) -> None:
        self.speak([f"misc_{key}"], MISC_TEXTS[key])

    def _say_message(self, m: Message, short: bool = False) -> None:
        ids, text = utterance(m, self.available, short=short)
        if self.explain_mode and m.rule not in self.explained:
            self.explained.add(m.rule)
            long = explain(m.rule)
            if long:
                clip = f"explain_{m.rule.replace('_big', '').replace('_throttle', '').replace('_entry', '')}"
                if self.available is not None and self.available(clip):
                    ids = ids + [clip]
                text = f"{text} {long}"
        self.speak(ids, text)

    def _lesson_filter(self, messages: list[Message]) -> list[Message]:
        if self.lesson is None:
            return messages
        return filter_messages(self.lesson, messages, self.lesson_corner)

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
        if self.guidance and self.reference is not None and recorder.current is not None:
            self.guide.set_reference(self.reference)
            for cue in self.guide.update(recorder.current):
                self.speak(list(cue.ids), cue.text)
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
            msgs = self._lesson_filter(evaluate_corner(lap.number, metrics, ref[corner.number], self.track, lap.traction_control))
            best = max(msgs, key=lambda m: m.weight, default=None)
            if best is not None and best.weight >= self.min_corner_weight:
                self._say_message(best, short=True)
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
        spoken = self._lesson_filter(messages)
        top = pick_top(spoken)
        if top:
            self._say_misc("lap_summary")
            for m in top:
                self._say_message(m)
            out += top
        elif not lap.invalid:
            soft = biggest_loss(spoken)
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
        # prowadzenie na następnym okrążeniu: zakręty z uwag tego okrążenia (lekcja z zakrętem: tylko on)
        if self.lesson_corner is None:
            self.guide.set_guided([m.corner for m in pick_top(spoken)])
        if self.progress is not None:
            clip, text = self.progress.record(lap, messages)
            if clip is not None and text is not None:
                self.speak([f"misc_{clip}"], text)
        if self.ers_advice and lap.ers_assist is False and lap.ers:
            advice = advise_ers(analyze_ers(lap, lap.ers, self.track), lap.ers_assist)
            if advice.kind in ("wasted_in_corners", "unused_battery"):
                key = "ers_wasted" if advice.kind == "wasted_in_corners" else "ers_unused"
                self.speak([f"misc_{key}"], MISC_TEXTS[key])
        return out

    def finish(self) -> None:
        self._say_misc("session_end")
