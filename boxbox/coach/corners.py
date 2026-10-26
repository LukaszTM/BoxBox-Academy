"""Metryki okrążenia w podziale na zakręty toru."""
from dataclasses import dataclass

from boxbox.coach.laps import Lap, Sample
from boxbox.tracks.model import Corner, Track

BRAKE_THRESHOLD = 0.1  # hamulec "wciśnięty"
FULL_THROTTLE = 0.95


@dataclass(frozen=True)
class CornerMetrics:
    corner: int
    min_speed_kmh: int
    apex_m: float  # gdzie faktycznie była najmniejsza prędkość
    gear_at_apex: int
    entry_speed_kmh: int
    exit_speed_kmh: int
    time_ms: int  # od wejścia do wyjścia
    brake_point_m: float | None  # początek ciągłego hamowania przed apeksem, None = nie hamował
    full_throttle_m: float | None  # pierwszy pełny gaz po apeksie, None = nie było w oknie


@dataclass(frozen=True)
class LapAnalysis:
    lap_number: int
    lap_time_ms: int | None
    corners: tuple[CornerMetrics, ...]


def _window(lap: Lap, corner: Corner, length: float, lookback: float, lookahead: float) -> list[tuple[float, Sample]]:
    """Próbki wokół zakrętu jako (dystans względem wejścia, próbka); działa też przez linię mety."""
    corner_len = corner.length_m(length)
    out = []
    for s in lap.samples:
        rel = (s.distance_m - corner.entry_m) % length
        if rel > length / 2:
            rel -= length  # próbki tuż przed wejściem mają rel ujemny
        if -lookback <= rel <= corner_len + lookahead:
            out.append((rel, s))
    out.sort(key=lambda item: item[0])
    return out


def _nearest(window: list[tuple[float, Sample]], rel: float) -> Sample:
    return min(window, key=lambda item: abs(item[0] - rel))[1]


def analyze_corner(lap: Lap, corner: Corner, track: Track, lookback_m: float = 150.0, lookahead_m: float = 150.0) -> CornerMetrics | None:
    window = _window(lap, corner, track.length_m, lookback_m, lookahead_m)
    corner_len = corner.length_m(track.length_m)
    inside = [(rel, s) for rel, s in window if 0 <= rel <= corner_len]
    if len(inside) < 2:
        return None
    # Prędkość jest całkowita, więc minimum to zwykle plateau kilku próbek; apex = jego środek.
    v_min = min(s.speed_kmh for _, s in inside)
    plateau = [rel for rel, s in inside if s.speed_kmh == v_min]
    apex_rel = plateau[len(plateau) // 2]
    apex_idx = next(i for i, (rel, _) in enumerate(window) if rel == apex_rel)
    apex = window[apex_idx][1]

    # Punkt hamowania: ostatnia faza ciągłego hamowania kończąca się najpóźniej w apeksie.
    brake_point: float | None = None
    i = apex_idx
    while i >= 0 and window[i][1].brake < BRAKE_THRESHOLD:
        i -= 1
    if i >= 0:
        while i > 0 and window[i - 1][1].brake >= BRAKE_THRESHOLD:
            i -= 1
        brake_point = window[i][1].distance_m

    full_throttle = next(
        (s.distance_m for rel, s in window[apex_idx:] if s.throttle >= FULL_THROTTLE), None
    )
    entry, exit_ = _nearest(inside, 0.0), _nearest(inside, corner_len)
    return CornerMetrics(
        corner=corner.number, min_speed_kmh=apex.speed_kmh, apex_m=apex.distance_m, gear_at_apex=apex.gear,
        entry_speed_kmh=entry.speed_kmh, exit_speed_kmh=exit_.speed_kmh,
        time_ms=max(0, exit_.lap_time_ms - entry.lap_time_ms),
        brake_point_m=brake_point, full_throttle_m=full_throttle,
    )


def analyze_lap(lap: Lap, track: Track) -> LapAnalysis:
    metrics = tuple(m for c in track.corners if (m := analyze_corner(lap, c, track)) is not None)
    return LapAnalysis(lap_number=lap.number, lap_time_ms=lap.lap_time_ms, corners=metrics)
