"""Podsumowanie sesji po polsku: jedna rzecz, która poszła dobrze, jedna do pracy.

Dane: komunikaty trenera z sesji i metryki zakrętów (teraz vs poprzednie sesje z bazy).
Zero UI: zwraca teksty, okno i raport PDF je pokazują.
"""
from collections.abc import Sequence
from dataclasses import dataclass

from boxbox.coach.corners import CornerMetrics, LapAnalysis
from boxbox.coach.laps import Lap
from boxbox.coach.rules import Message
from boxbox.tracks.model import Track

RULE_PL = {
    "brake_late": "hamowanie za późno", "brake_late_big": "hamowanie dużo za późno", "brake_early": "hamowanie za wcześnie",
    "brake_release": "hamulec puszczony naraz", "trail_missing": "hamowanie kończy się za wcześnie",
    "throttle_late": "pełny gaz za późno", "throttle_early": "gaz za wcześnie", "grip_lost": "utrata przyczepności",
    "gear_low": "za niski bieg", "gear_high": "za wysoki bieg",
}


@dataclass(frozen=True)
class SessionSummary:
    good: str
    to_work: str
    best_lap_ms: int | None
    laps: int
    clean_laps: int
    corner_scores: dict[int, float]  # zakręt -> suma strat (s) w sesji


def rule_pl(rule: str) -> str:
    return RULE_PL.get(rule, rule.replace("_", " "))


def _corner_name(track: Track | None, corner: int) -> str:
    if track is not None:
        for c in track.corners:
            if c.number == corner:
                return c.name or f"Z{corner}"
    return f"Z{corner}"


def _improvements(now: LapAnalysis | None, before: Sequence[CornerMetrics] | None, track: Track | None) -> list[tuple[float, str]]:
    """(waga, zdanie) za poprawy względem najlepszego okrążenia sprzed tej sesji."""
    if now is None or not before:
        return []
    prev = {m.corner: m for m in before}
    out: list[tuple[float, str]] = []
    for m in now.corners:
        p = prev.get(m.corner)
        if p is None:
            continue
        name = _corner_name(track, m.corner)
        if m.brake_point_m is not None and p.brake_point_m is not None and m.brake_point_m - p.brake_point_m >= 8:
            out.append((m.brake_point_m - p.brake_point_m, f"{name}: hamujesz {m.brake_point_m - p.brake_point_m:.0f} m później niż w poprzednich sesjach"))
        if m.min_speed_kmh - p.min_speed_kmh >= 5:
            out.append((float(m.min_speed_kmh - p.min_speed_kmh), f"{name}: w apeksie {m.min_speed_kmh - p.min_speed_kmh} km/h szybciej niż wcześniej"))
        if m.full_throttle_m is not None and p.full_throttle_m is not None and p.full_throttle_m - m.full_throttle_m >= 8:
            out.append((p.full_throttle_m - m.full_throttle_m, f"{name}: pełny gaz {p.full_throttle_m - m.full_throttle_m:.0f} m wcześniej niż wcześniej"))
    out.sort(key=lambda x: -x[0])
    return out


def summarize(
    laps: Sequence[Lap], messages: Sequence[Message], track: Track | None = None,
    best_now: LapAnalysis | None = None, best_before: Sequence[CornerMetrics] | None = None,
    best_before_ms: int | None = None,
) -> SessionSummary:
    valid = [lap for lap in laps if not lap.pitted and lap.lap_time_ms]
    times = [lap.lap_time_ms for lap in valid if not lap.invalid and lap.lap_time_ms]
    best_ms = min(times) if times else None
    scores: dict[int, float] = {}
    for m in messages:
        scores[m.corner] = scores.get(m.corner, 0.0) + m.weight
    per_lap: dict[int, float] = {}
    for m in messages:
        per_lap[m.lap] = per_lap.get(m.lap, 0.0) + m.weight
    clean = sum(1 for lap in valid if not lap.invalid and per_lap.get(lap.number, 0.0) < 1.0)

    good_candidates = _improvements(best_now, best_before, track)
    if best_ms is not None and best_before_ms is not None and best_ms < best_before_ms:
        good_candidates.insert(0, (99.0, f"nowe najlepsze okrążenie, o {(best_before_ms - best_ms) / 1000:.3f} s lepsze niż dotąd"))
    if not good_candidates:
        if clean:
            good_candidates.append((1.0, f"{clean} {'czyste okrążenie' if clean == 1 else 'czyste okrążenia'} bez poważnych błędów"))
        elif track is not None and scores:
            quiet = [c.name or f"Z{c.number}" for c in track.corners if c.number not in scores]
            if quiet:
                good_candidates.append((0.5, f"bez uwag w: {', '.join(quiet[:4])}"))
    good = good_candidates[0][1] if good_candidates else "pierwsza sesja na tym torze zapisana jako punkt odniesienia"

    if scores:
        worst = max(scores, key=scores.get)
        rules = [m.rule for m in messages if m.corner == worst]
        top_rule = max(set(rules), key=rules.count)
        worst_single = max(m.weight for m in messages if m.corner == worst)
        to_work = f"{_corner_name(track, worst)}: {rule_pl(top_rule)} (do {worst_single:.1f} s na okrążeniu)"
    else:
        to_work = "nic pilnego; następny krok to kolejne czyste okrążenia"
    return SessionSummary(good, to_work, best_ms, len(valid), clean, scores)
