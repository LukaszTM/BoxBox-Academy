"""Plan baterii na okrążenie: na których prostych deploy daje najwięcej, ostrzeżenie przed pustą baterią.

Zasada z gry: na okrążenie można wydać ok. 4 MJ (ERS_MAX_J), a pełna moc MGU-K (120 kW) wyczerpuje to
w ok. 33 s. Zysk z deployu jest tym większy, im dłużej auto jedzie z pełnym gazem, więc plan to proste
(odcinki między wyjściem z zakrętu a wejściem w następny) uszeregowane według czasu przejazdu z okrążenia
referencyjnego, aż do wyczerpania budżetu. Ocena po okrążeniu: jaka część deployu poszła na zaplanowane
proste. Ostrzeżenie na żywo: bateria prawie pusta tuż przed najdłuższą prostą.
"""
from dataclasses import dataclass

from boxbox.coach.ers import ERS_MAX_J
from boxbox.coach.ers_sample import ErsSample
from boxbox.coach.laps import Lap
from boxbox.tracks.model import Track

DEPLOY_POWER_W = 120_000.0
BUDGET_S = ERS_MAX_J / DEPLOY_POWER_W  # ~33 s pełnej mocy na okrążenie
MIN_STRAIGHT_M = 120.0  # krótsze odcinki między zakrętami to nie proste
EMPTY_RATIO = 0.15  # bateria „prawie pusta”
WARN_AHEAD_M = 250.0  # ostrzeżenie tyle metrów przed początkiem najdłuższej prostej
ON_PLAN_OK = 0.7  # tyle deployu na zaplanowanych prostych = dobrze


@dataclass(frozen=True)
class Straight:
    number: int
    start_m: float  # wyjście z zakrętu
    end_m: float  # wejście w następny (może być < start_m: przez linię mety)
    length_m: float
    seconds: float  # czas przejazdu z okrążenia referencyjnego
    from_corner: str
    to_corner: str
    deploy: bool = False  # w planie
    share: float = 0.0  # jaka część budżetu (0..1) przypada na tę prostą

    def contains(self, distance_m: float, length_m: float) -> bool:
        if self.end_m >= self.start_m:
            return self.start_m <= distance_m <= self.end_m
        return distance_m >= self.start_m or distance_m <= self.end_m


@dataclass(frozen=True)
class ErsPlan:
    straights: tuple[Straight, ...]  # w kolejności toru

    @property
    def planned(self) -> tuple[Straight, ...]:
        return tuple(s for s in self.straights if s.deploy)

    @property
    def longest(self) -> Straight | None:
        return max(self.straights, key=lambda s: s.seconds, default=None)

    def straight_at(self, distance_m: float, length_m: float) -> Straight | None:
        return next((s for s in self.straights if s.contains(distance_m, length_m)), None)


@dataclass(frozen=True)
class ErsPlanReview:
    deployed_j: float
    on_plan_j: float

    @property
    def on_plan_ratio(self) -> float:
        return self.on_plan_j / self.deployed_j if self.deployed_j > 0 else 0.0

    @property
    def ok(self) -> bool:
        return self.deployed_j <= 0 or self.on_plan_ratio >= ON_PLAN_OK


def _time_at(lap: Lap, distance_m: float) -> float | None:
    """Czas okrążenia (s) w najbliższej próbce; None bez próbek w pobliżu (50 m)."""
    best = min(lap.samples, key=lambda s: abs(s.distance_m - distance_m), default=None)
    return best.lap_time_ms / 1000 if best is not None and abs(best.distance_m - distance_m) <= 50 else None


def straights(track: Track, reference: Lap) -> tuple[Straight, ...]:
    """Proste między zakrętami z czasem przejazdu z okrążenia referencyjnego (próbki), w kolejności toru."""
    corners = track.corners
    if len(corners) < 2 or not reference.samples:
        return ()
    length = track.length_m
    total = reference.lap_time_ms / 1000 if reference.lap_time_ms else (reference.samples[-1].lap_time_ms / 1000)
    out: list[Straight] = []
    for i, c in enumerate(corners):
        nxt = corners[(i + 1) % len(corners)]
        start, end = c.exit_m, nxt.entry_m
        wraps = end < start
        seg_len = (end - start) if not wraps else (length - start + end)
        if seg_len < MIN_STRAIGHT_M:
            continue
        t0, t1 = _time_at(reference, start), _time_at(reference, end)
        if t0 is None or t1 is None:
            seconds = seg_len / max(1.0, length / total) if total else 0.0  # średnia prędkość okrążenia
        elif wraps:
            seconds = (total - t0) + t1
        else:
            seconds = max(0.0, t1 - t0)
        name = lambda cc: cc.name or f"zakręt {cc.number}"  # noqa: E731
        out.append(Straight(len(out) + 1, start, end, seg_len, seconds, name(c), name(nxt)))
    return tuple(out)


def plan(track: Track, reference: Lap, budget_s: float = BUDGET_S) -> ErsPlan:
    """Najdłuższe (czasowo) proste dostają deploy, aż budżet się skończy; ostatnia może dostać część."""
    segs = list(straights(track, reference))
    left = budget_s
    marked: dict[int, tuple[bool, float]] = {}
    for s in sorted(segs, key=lambda x: x.seconds, reverse=True):
        if left <= 0 or s.seconds <= 0:
            break
        used = min(s.seconds, left)
        marked[s.number] = (True, used / budget_s)
        left -= used
    out = tuple(Straight(s.number, s.start_m, s.end_m, s.length_m, s.seconds, s.from_corner, s.to_corner,
                         *marked.get(s.number, (False, 0.0))) for s in segs)
    return ErsPlan(out)


def review(plan_: ErsPlan, samples: list[ErsSample], length_m: float) -> ErsPlanReview | None:
    """Ile deployu poszło na zaplanowane proste (z próbek baterii okrążenia)."""
    rows = [s for s in samples if s.distance_m >= 0]
    if len(rows) < 2:
        return None
    on_plan = 0.0
    prev = rows[0]
    for s in rows[1:]:
        delta = max(0.0, s.deployed_j - prev.deployed_j)
        st = plan_.straight_at(s.distance_m, length_m)
        if st is not None and st.deploy:
            on_plan += delta
        prev = s
    return ErsPlanReview(rows[-1].deployed_j, on_plan)


def empty_before_straight(plan_: ErsPlan, distance_m: float, store_j: float, length_m: float) -> Straight | None:
    """Najdłuższa prosta zaczyna się w WARN_AHEAD_M, a bateria jest prawie pusta: ostrzeżenie (albo None)."""
    top = plan_.longest
    if top is None or store_j > EMPTY_RATIO * ERS_MAX_J:
        return None
    ahead = (top.start_m - distance_m) % length_m
    return top if 0 < ahead <= WARN_AHEAD_M else None


def describe(plan_: ErsPlan) -> str:
    """Jedno zdanie do okna: „Deploy na prostych: po T11, po T1-T2, po T7 (razem 31 s)”."""
    chosen = sorted(plan_.planned, key=lambda s: s.number)
    if not chosen:
        return "Brak prostych do planu baterii."
    total = sum(min(s.seconds, s.share * BUDGET_S) for s in chosen)
    return "Deploy na prostych: " + ", ".join(f"po {s.from_corner}" for s in chosen) + f" (razem {total:.0f} s pełnej mocy)"
