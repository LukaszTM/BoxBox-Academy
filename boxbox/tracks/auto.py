"""Automatyczny plik toru: zakręty z pierwszego pełnego okrążenia sesji, gdy tor nie ma pliku w pakiecie.

Ten sam algorytm co `python -m boxbox.tracks.detect` (minima prędkości potwierdzone hamowaniem),
tylko na okrążeniu z `LapRecorder` zamiast z nagrania. Zakręty dostają nazwy T1..Tn według kolejności
stref hamowania; szykana liczona jako jedna strefa, więc numeracja może różnić się od tej w grze.
Plik ląduje w `data/tracks/<id>.json` i można go poprawić ręcznie (nazwy, granice); plik wbudowany
w `boxbox/tracks/data/` ma zawsze pierwszeństwo.
"""
from pathlib import Path

from boxbox.coach.laps import Lap
from boxbox.tracks.detect import SpeedSample, detect_corners
from boxbox.tracks.model import Corner, Track, _validate, save_track

MIN_CORNERS = 3  # mniej stref hamowania na pełnym okrążeniu = okrążenie nietypowe (np. jazda za SC), czekamy na następne
MIN_SAMPLES = 200  # pełne okrążenie z gry ma ich tysiące; mniej = dziurawe nagranie
SOURCE_NOTE = "automatycznie z okrążenia w sesji; numeracja według stref hamowania (może różnić się od gry)"


def lap_samples(lap: Lap) -> list[SpeedSample]:
    return [SpeedSample(s.distance_m, float(s.speed_kmh), s.throttle, s.brake) for s in lap.samples]


def track_from_lap(lap: Lap, track_id: int, name: str, length_m: float, source: str = "") -> Track | None:
    """Tor z jednego pełnego okrążenia albo None, gdy okrążenie się nie nadaje (niepełne, pit, za mało zakrętów)."""
    if length_m <= 0 or lap.pitted or not lap.is_complete(length_m) or len(lap.samples) < MIN_SAMPLES:
        return None
    detected = detect_corners(lap_samples(lap), length_m)
    if len(detected) < MIN_CORNERS:
        return None
    corners = tuple(Corner(c.number, c.entry_m, c.apex_m, c.exit_m, f"T{c.number}") for c in detected)
    track = Track(track_id=track_id, name=name, length_m=float(length_m), corners=corners,
                  source=f"{source}: {SOURCE_NOTE}" if source else SOURCE_NOTE)
    try:
        _validate(track)
    except ValueError:
        return None
    return track


def save_auto_track(track: Track, path: Path) -> Path:
    save_track(track, path)
    return path
