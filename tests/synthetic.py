"""Syntetyczne okrążenie: profil prędkości z 4 zakrętami plus spójny gaz, hamulec i bieg."""
import math

from boxbox.tracks.model import Corner, Track

LENGTH = 5000.0
# (apex_m, prędkość w apeksie, połowa szerokości "doliny" w m)
CORNERS = [(600.0, 90.0, 120.0), (1500.0, 160.0, 150.0), (3200.0, 70.0, 100.0), (4800.0, 200.0, 120.0)]
STRAIGHT = 300.0


def speed_at(distance: float) -> float:
    speed = STRAIGHT
    for apex, v_min, half_width in CORNERS:
        d = abs(distance - apex)
        if d < half_width:
            # łagodna dolina: kosinus od prostej do apeksu i z powrotem
            speed = min(speed, v_min + (STRAIGHT - v_min) * (1 - math.cos(math.pi * d / half_width)) / 2)
    return speed


def pedals_at(distance: float) -> tuple[float, float]:
    """(gaz, hamulec): hamowanie od 0,8 szerokości przed apeksem do apeksu, pełny gaz od 0,5 szerokości za apeksem."""
    for apex, _, half_width in CORNERS:
        rel = distance - apex
        if -0.8 * half_width <= rel < 0:
            return 0.0, 0.9 if rel < -0.3 * half_width else 0.3  # mocno, potem trail-braking
        if 0 <= rel < 0.5 * half_width:
            return 0.5, 0.0  # częściowy gaz na wyjściu
    return 1.0, 0.0


def gear_at(distance: float) -> int:
    return max(1, min(8, int(speed_at(distance) // 40) + 1))


def track() -> Track:
    corners = tuple(
        Corner(i + 1, apex - 0.795 * hw, apex, apex + 0.795 * hw) for i, (apex, _, hw) in enumerate(CORNERS)
    )
    return Track(track_id=3, name="Bahrajn", length_m=LENGTH, corners=corners)
