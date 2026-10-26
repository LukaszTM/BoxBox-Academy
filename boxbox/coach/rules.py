"""Reguły trenera: porównanie zakrętu z referencją -> komunikaty z wagą.

Silnik nie dotyka UI ani dźwięku; zwraca listę Message. Progi pochodzą z nagrań
w recordings/: naturalne różnice między czystymi okrążeniami tego samego kierowcy
(Monza okr. 3 vs 6) sięgają ok. 0,3 s, +-50 m hamowania i +-125 m pełnego gazu
na zakręt, więc komunikat wymaga straty czasu wyraźnie powyżej tego szumu.
Celowe błędy (Monza okr. 4: T1 +290 m hamowania, +5 s; Suzuka: obroty bez TC)
są o rząd wielkości większe.
"""
from dataclasses import dataclass

from boxbox.coach.corners import CornerMetrics, LapAnalysis
from boxbox.coach.laps import Lap
from boxbox.tracks.model import Track

# progi
MIN_TIME_LOSS_S = 0.5  # poniżej tej straty na zakręt trener milczy (szum między czystymi okrążeniami)
BRAKE_LATE_M = 20.0  # hamowanie później niż referencja o tyle metrów
BRAKE_EARLY_M = 25.0
THROTTLE_LATE_M = 30.0  # pełny gaz później niż referencja
THROTTLE_EARLY_M = 25.0
GRIP_LOST_RATIO = 0.6  # v_min poniżej 60% referencji = utrata przyczepności / obrót
# Puszczanie hamulca: na czystych okrążeniach gracza 0,02-0,15 s (G29), u ducha Opmeera 0,7-1,1 s.
# Komunikat tylko gdy referencja naprawdę puszcza stopniowo, inaczej to stała cecha kierowcy, nie błąd.
ABRUPT_RELEASE_S = 0.25
REFERENCE_RELEASE_S = 0.4
TRAIL_END_EARLY_M = 40.0  # hamowanie kończy się o tyle metrów wcześniej przed apeksem niż u referencji
TOP_MESSAGES = 3


@dataclass(frozen=True)
class Message:
    lap: int
    corner: int
    corner_name: str
    rule: str  # brake_late, brake_early, brake_release, trail_missing, throttle_early, throttle_late, grip_lost, gear_low, gear_high
    problem: str  # co się stało, jedno zdanie
    hint: str  # co zrobić następnym razem
    weight: float  # im większa, tym ważniejsze; zwykle strata czasu w sekundach
    value_m: int | None = None  # metry do wypowiedzenia (np. o ile za późno), zaokrąglone do 10
    gear: int | None = None  # bieg do wypowiedzenia (reguły biegu)
    variant: str = ""  # odmiana komunikatu w głosie, np. "big" dla hamowania dużo za późno

    def spoken(self) -> str:
        return f"{self.problem} {self.hint}"


def _round_m(value: float, lo: int = 10, hi: int = 300) -> int:
    return int(min(hi, max(lo, round(value / 10) * 10)))


def _label(track: Track, corner: int) -> str:
    c = track.corners[corner - 1] if 0 < corner <= len(track.corners) else None
    return (c.name if c and c.name else f"zakręt {corner}")


def evaluate_corner(
    lap_number: int, m: CornerMetrics, ref: CornerMetrics, track: Track, assists_tc: int | None = None
) -> list[Message]:
    """Wszystkie reguły dla jednego zakrętu. Wagi: strata czasu + dodatek za rodzaj błędu."""
    name = _label(track, m.corner)
    loss_s = (m.time_ms - ref.time_ms) / 1000
    out: list[Message] = []

    def msg(rule: str, problem: str, hint: str, weight: float, value_m: float | None = None,
            gear: int | None = None, variant: str = "") -> None:
        out.append(Message(
            lap_number, m.corner, name, rule, problem, hint, round(weight, 2),
            _round_m(value_m) if value_m is not None else None, gear, variant,
        ))

    brake_delta = (m.brake_point_m - ref.brake_point_m) if (m.brake_point_m is not None and ref.brake_point_m is not None) else None
    loss = max(loss_s, 0.0)

    # 1. Dramatyczny spadek v_min: albo skutek hamowania dużo za późno, albo utrata przyczepności (obrót).
    if ref.min_speed_kmh > 0 and m.min_speed_kmh < GRIP_LOST_RATIO * ref.min_speed_kmh:
        if brake_delta is not None and brake_delta >= BRAKE_LATE_M:
            msg("brake_late", f"Hamowanie za późno w {name}, o {brake_delta:.0f} m; musiałeś mocno zwolnić.",
                f"Zacznij hamować ok. {brake_delta:.0f} m wcześniej.", max(loss, 2.0) + 0.5, brake_delta, variant="big")
        else:
            on_exit = m.full_throttle_m is not None and ref.full_throttle_m is not None and m.full_throttle_m < ref.full_throttle_m
            cause = "Łagodniej z gazem na wyjściu, zwłaszcza bez kontroli trakcji." if (on_exit or assists_tc == 0) \
                else "Wolniej na wejściu i mniej kierownicy, zanim dodasz gaz."
            msg("grip_lost", f"Utrata przyczepności w {name}.", cause, max(loss, 2.0) + 1.0,
                variant="throttle" if (on_exit or assists_tc == 0) else "entry")
        return out  # reszta reguł nie ma sensu, gdy auto prawie stanęło

    # 2. Punkt hamowania.
    if brake_delta is not None:
        if brake_delta >= BRAKE_LATE_M and (loss_s >= 0.2 or m.min_speed_kmh < ref.min_speed_kmh - 10):
            msg("brake_late", f"Hamowanie za późno w {name}, o {brake_delta:.0f} m.",
                f"Zacznij hamować ok. {brake_delta:.0f} m wcześniej i puszczaj pedał stopniowo.", loss + 0.05, brake_delta)
        elif brake_delta <= -BRAKE_EARLY_M and loss_s >= 0.2 and m.min_speed_kmh <= ref.min_speed_kmh + 5:
            msg("brake_early", f"Hamowanie za wcześnie w {name}, o {-brake_delta:.0f} m.",
                f"Możesz hamować ok. {-brake_delta:.0f} m później; do apeksu dojeżdżasz z zapasem.", loss + 0.03, -brake_delta)

    # 3. Puszczanie hamulca, tylko względem referencji, która robi to stopniowo.
    if (
        m.brake_release_s is not None and ref.brake_release_s is not None
        and m.max_brake >= 0.4 and ref.brake_release_s >= REFERENCE_RELEASE_S
    ):
        if m.brake_release_s < ABRUPT_RELEASE_S and ref.brake_release_s >= 2 * m.brake_release_s:
            msg("brake_release", f"Hamulec puszczony naraz przed {name}.",
                "Zwalniaj hamulec stopniowo, aż do apeksu.", loss + 0.02)
        elif m.brake_end_m is not None and ref.brake_end_m is not None and ref.brake_end_m - m.brake_end_m >= TRAIL_END_EARLY_M:
            msg("trail_missing", f"Hamowanie kończy się za wcześnie przed {name}.",
                "Trzymaj lekki hamulec do apeksu, auto lepiej skręci.", loss + 0.02)

    # 4. Pełny gaz na wyjściu.
    if m.full_throttle_m is not None and ref.full_throttle_m is not None:
        delta = m.full_throttle_m - ref.full_throttle_m
        if delta >= THROTTLE_LATE_M and loss_s >= 0.2:
            msg("throttle_late", f"Pełny gaz za późno na wyjściu z {name}, o {delta:.0f} m.",
                "Gdy kierownica się prostuje, dodawaj gaz pewniej.", loss + 0.01, delta)
        elif delta <= -THROTTLE_EARLY_M and m.exit_speed_kmh < ref.exit_speed_kmh - 5:
            msg("throttle_early", f"Gaz za wcześnie na wyjściu z {name}.",
                "Poczekaj z pełnym gazem, aż auto się wyprostuje; koła ślizgają się zamiast przyspieszać.", loss + 0.04)

    # 5. Bieg w apeksie (niska waga: sam w sobie rzadko kosztuje czas).
    if m.gear_at_apex > 0 and ref.gear_at_apex > 0:
        if m.gear_at_apex < ref.gear_at_apex:
            msg("gear_low", f"Za niski bieg w {name}.", f"W apeksie {ref.gear_at_apex}. bieg.", 0.1 * (ref.gear_at_apex - m.gear_at_apex), gear=ref.gear_at_apex)
        elif m.gear_at_apex > ref.gear_at_apex:
            msg("gear_high", f"Za wysoki bieg w {name}.", f"W apeksie {ref.gear_at_apex}. bieg, silnik ma wtedy siłę.", 0.1 * (m.gear_at_apex - ref.gear_at_apex), gear=ref.gear_at_apex)
    return out


def evaluate_lap(lap: Lap, analysis: LapAnalysis, reference: LapAnalysis | None, track: Track) -> list[Message]:
    """Komunikaty dla wszystkich zakrętów okrążenia; bez referencji trener milczy."""
    if reference is None:
        return []
    ref = {c.corner: c for c in reference.corners}
    out: list[Message] = []
    for m in analysis.corners:
        if m.corner in ref:
            out.extend(evaluate_corner(lap.number, m, ref[m.corner], track, lap.traction_control))
    return out


def pick_top(messages: list[Message], limit: int = TOP_MESSAGES, min_weight: float = MIN_TIME_LOSS_S) -> list[Message]:
    """2-3 najważniejsze komunikaty po okrążeniu: jeden na zakręt, tylko powyżej progu wagi."""
    best: dict[int, Message] = {}
    for m in messages:
        if m.weight >= min_weight and (m.corner not in best or m.weight > best[m.corner].weight):
            best[m.corner] = m
    return sorted(best.values(), key=lambda m: m.weight, reverse=True)[:limit]
