"""Prowadzenie w zakręcie na żywo: w nieopanowanych zakrętach trener mówi przed punktem, co zrobić.

Komendy biorą się z okrążenia referencyjnego (`CornerMetrics`): gdzie referencja puściła gaz,
gdzie i jak mocno zaczęła hamować, gdzie była w apeksie (pół gazu) i gdzie dała pełny gaz.
Każda komenda pada z wyprzedzeniem zależnym od prędkości (`LEAD_S`), żeby kierowca zdążył
usłyszeć i zareagować dokładnie w punkcie. Przed pierwszą komendą zakrętu krótkie
"Zakręt czwarty. Prowadzę.", żeby wiedział, że to komendy, nie uwagi.

Zakręty do prowadzenia wybiera `LiveCoach`: te z uwagami z podsumowania ostatniego okrążenia
(najwyżej `MAX_GUIDED`), a na starcie sesji te z uwagami z poprzednich sesji. Zakręt bez uwagi
wypada z listy, więc dobrze przejechany zakręt milknie sam. Silnik nie dotyka dźwięku:
zwraca komendy, a aplikacja je mówi (jako pilne: przerywają podsumowanie).
"""
from collections.abc import Sequence
from dataclasses import dataclass, field

from boxbox.coach.corners import CornerMetrics, LapAnalysis
from boxbox.coach.laps import Lap
from boxbox.tracks.model import Corner, Track
from boxbox.voice.phrases import GUIDE_TEXTS, corner_key, corner_text

LEAD_S = 1.0  # wyprzedzenie komendy: czas na wypowiedzenie słowa i reakcję kierowcy
MIN_LEAD_M = 15.0  # nawet przy małej prędkości komenda pada kilkanaście metrów wcześniej
INTRO_M = 220.0  # "Zakręt czwarty. Prowadzę." tyle metrów przed pierwszą komendą (ok. 3 s przy 250 km/h)
LATE_M = 40.0  # komenda, którą auto już minęło o tyle metrów (np. skok próbek), przepada zamiast mylić
HARD_BRAKE = 0.8  # maks. hamulec referencji od tego progu = "mocno"; poniżej MEDIUM_BRAKE = "lekko"
MEDIUM_BRAKE = 0.45
LIFT_MIN_GAP_M = 60.0  # "puść gaz" tylko gdy referencja puszcza gaz wyraźnie przed hamowaniem (inaczej "hamuj" by je uciął)
HALF_MIN_GAP_M = 40.0  # "pół gazu" w apeksie tylko gdy pełny gaz referencji jest wyraźnie później
MAX_GUIDED = 3  # tyle zakrętów naraz najwyżej; więcej to gadanie, nie nauka
KINDS = ("intro", "lift", "brake", "half", "full")
BRAKE_KINDS = frozenset({"lift", "brake"})
THROTTLE_KINDS = frozenset({"half", "full"})


def kinds_for_rules(rules: Sequence[str]) -> frozenset[str]:
    """Lekcja o hamowaniu dostaje tylko komendy hamowania, lekcja o gazie tylko gazu; mieszana albo inna: wszystkie."""
    brake = any(r.startswith(("brake", "trail")) for r in rules)
    throttle = any(r.startswith(("throttle", "grip")) for r in rules)
    if brake and not throttle:
        return BRAKE_KINDS
    if throttle and not brake:
        return THROTTLE_KINDS
    return frozenset(KINDS)


@dataclass(frozen=True)
class Cue:
    corner: int
    corner_name: str
    kind: str  # intro | lift | brake | half | full
    at_m: float  # dystans okrążenia, w którym kierowca ma to zrobić
    ids: tuple[str, ...]
    text: str  # dokładnie to, co mówi głos


def is_urgent_cue(ids: Sequence[str]) -> bool:
    """Komenda w zakręcie (nie wstęp) ma wybrzmieć w porę: aplikacja przerywa nią to, co właśnie leci."""
    return bool(ids) and ids[0].startswith("guide_") and ids[0] != "guide_intro"


def brake_strength(max_brake: float) -> str:
    if max_brake >= HARD_BRAKE:
        return "brake_hard"
    return "brake_medium" if max_brake >= MEDIUM_BRAKE else "brake_light"


def _signed(from_m: float, to_m: float, length_m: float) -> float:
    """Metry od `from_m` do `to_m` wzdłuż okrążenia, w zakresie (-L/2, L/2]; dodatnie = przed autem."""
    return ((to_m - from_m + length_m / 2) % length_m) - length_m / 2


def corner_cues(corner: Corner, ref: CornerMetrics, length_m: float) -> tuple[Cue, ...]:
    """Komendy dla zakrętu z metryk referencji, w kolejności jazdy."""
    name = corner.name or f"zakręt {corner.number}"
    cues: list[Cue] = []

    def add(kind: str, at_m: float, key: str) -> None:
        cues.append(Cue(corner.number, name, kind, at_m % length_m, (f"guide_{key}",), GUIDE_TEXTS[key]))

    if ref.brake_point_m is not None:
        add("brake", ref.brake_point_m, brake_strength(ref.max_brake))
    if ref.lift_m is not None and (ref.brake_point_m is None or _signed(ref.lift_m, ref.brake_point_m, length_m) >= LIFT_MIN_GAP_M):
        add("lift", ref.lift_m, "lift")
    if ref.full_throttle_m is not None:
        if _signed(ref.apex_m, ref.full_throttle_m, length_m) >= HALF_MIN_GAP_M:
            add("half", ref.apex_m, "half")
        add("full", ref.full_throttle_m, "full")
    if not cues:
        return ()
    cues.sort(key=lambda c: _signed(corner.entry_m, c.at_m, length_m))
    first = cues[0]
    intro = Cue(corner.number, name, "intro", (first.at_m - INTRO_M) % length_m,
                (f"corner_{corner_key(name)}", "guide_intro"), f"{corner_text(name)} {GUIDE_TEXTS['intro']}")
    return (intro, *cues)


@dataclass
class CornerGuide:
    track: Track
    reference: LapAnalysis | None = None
    guided: set[int] = field(default_factory=set)  # numery zakrętów do prowadzenia
    kinds: frozenset[str] = frozenset(KINDS)  # rodzaje komend (lekcja zawęża do hamowania albo gazu); wstęp zawsze
    said: set[tuple[int, int, str]] = field(default_factory=set)  # (okrążenie, zakręt, rodzaj) już powiedziane
    _cues: dict[int, tuple[Cue, ...]] = field(default_factory=dict)
    _ref_id: int = 0

    def set_reference(self, reference: LapAnalysis | None) -> None:
        if id(reference) != self._ref_id:
            self.reference, self._ref_id, self._cues = reference, id(reference), {}

    def set_guided(self, corners: Sequence[int]) -> None:
        self.guided = set(list(corners)[:MAX_GUIDED])

    def cues_for(self, corner: Corner) -> tuple[Cue, ...]:
        if corner.number not in self._cues:
            ref = next((m for m in self.reference.corners if m.corner == corner.number), None) if self.reference else None
            cues = corner_cues(corner, ref, self.track.length_m) if ref is not None else ()
            kept = tuple(c for c in cues if c.kind in self.kinds)
            self._cues[corner.number] = (cues[0], *kept) if kept and cues[0].kind == "intro" else kept
        return self._cues[corner.number]

    def update(self, lap: Lap) -> list[Cue]:
        """Komendy, których pora właśnie nadeszła (zwykle 0 albo 1), dla ostatniej próbki okrążenia."""
        if self.reference is None or not self.guided or lap.pitted or not lap.samples:
            return []
        s = lap.samples[-1]
        lead = max(MIN_LEAD_M, s.speed_kmh / 3.6 * LEAD_S)
        length = self.track.length_m
        out: list[Cue] = []
        for corner in self.track.corners:
            if corner.number not in self.guided:
                continue
            for cue in self.cues_for(corner):
                key = (lap.number, corner.number, cue.kind)
                if key in self.said:
                    continue
                ahead = (cue.at_m - s.distance_m) % length  # 0..L: ile metrów do punktu jadąc do przodu
                if lead < ahead < length - LATE_M:
                    continue  # jeszcze daleko
                self.said.add(key)
                if ahead <= lead:
                    out.append(cue)  # punkt tuż przed autem: pora mówić; minięty o >LATE_M (skok próbek) przepada
        return out
