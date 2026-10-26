"""Różnice metryk zakrętów między okrążeniem a referencją."""
from dataclasses import dataclass

from boxbox.coach.corners import LapAnalysis


@dataclass(frozen=True)
class CornerDelta:
    corner: int
    min_speed_delta_kmh: int  # ujemne = wolniej w apeksie niż referencja
    time_delta_ms: int  # dodatnie = dłużej w zakręcie niż referencja
    gear_delta: int
    brake_point_delta_m: float | None  # dodatnie = hamowanie później (dalej w metrach) niż referencja
    full_throttle_delta_m: float | None  # dodatnie = pełny gaz później niż referencja


def _delta(a: float | None, b: float | None) -> float | None:
    return None if a is None or b is None else a - b


def compare_to_reference(current: LapAnalysis, reference: LapAnalysis) -> list[CornerDelta]:
    """Dla zakrętów obecnych w obu okrążeniach; brakujące pomija."""
    ref = {m.corner: m for m in reference.corners}
    out = []
    for m in current.corners:
        r = ref.get(m.corner)
        if r is None:
            continue
        out.append(CornerDelta(
            corner=m.corner,
            min_speed_delta_kmh=m.min_speed_kmh - r.min_speed_kmh,
            time_delta_ms=m.time_ms - r.time_ms,
            gear_delta=m.gear_at_apex - r.gear_at_apex,
            brake_point_delta_m=_delta(m.brake_point_m, r.brake_point_m),
            full_throttle_delta_m=_delta(m.full_throttle_m, r.full_throttle_m),
        ))
    return out
