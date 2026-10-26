"""Okrążenia ducha z Time Trial (rywal albo rekord osobisty) jako Lap do analizy.

Z nagrania Bahrajn TT: duch jest w pakietach pod indeksem z Lap Data
(`time_trial_rival_car_idx` / `time_trial_pb_car_idx`). Jego dystans, czas
okrążenia, gaz, hamulec i bieg są poprawne, ale pole prędkości jest śmieciowe
(skoki do 486 km/h), więc prędkość liczymy z przyrostu dystansu w czasie.
Po każdym okrążeniu duch stoi na linii mety i czeka na gracza; te próbki
(bez przyrostu dystansu) pomijamy.
"""
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from boxbox.coach.laps import Lap, Sample
from boxbox.telemetry.header import PacketId
from boxbox.telemetry.replay import replay
from boxbox.telemetry.state import TelemetryState

GhostKind = Literal["rival", "pb"]
NO_CAR = 255


@dataclass
class GhostLaps:
    kind: GhostKind
    car_index: int
    name: str | None
    laps: list[Lap]

    def best_lap(self, track_length_m: float) -> Lap | None:
        full = [lap for lap in self.laps if lap.is_complete(track_length_m) and lap.lap_time_ms]
        return min(full, key=lambda lap: lap.lap_time_ms or 0) if full else None


@dataclass(frozen=True)
class _Raw:
    distance_m: float
    lap_time_ms: int
    throttle: float
    brake: float
    gear: int
    steer: float
    last_lap_time_ms: int


def _derive_speeds(raw: list[_Raw], half_window: int = 20) -> list[int]:
    """Prędkość z nachylenia dystansu po czasie w oknie ±half_window próbek (~0,67 s przy 60 Hz).

    Krótsze okno (±10) dawało fałszywe minima w strefach hamowania przy wykrywaniu zakrętów.
    """
    speeds = []
    n = len(raw)
    for i in range(n):
        lo, hi = max(0, i - half_window), min(n - 1, i + half_window)
        dt = (raw[hi].lap_time_ms - raw[lo].lap_time_ms) / 1000
        dd = raw[hi].distance_m - raw[lo].distance_m
        speeds.append(int(round(max(0.0, dd / dt * 3.6))) if dt > 0 else 0)
    return speeds


def _to_lap(number: int, raw: list[_Raw]) -> Lap:
    speeds = _derive_speeds(raw)
    samples = [
        Sample(r.distance_m, r.lap_time_ms, v, r.throttle, r.brake, r.gear, r.steer) for r, v in zip(raw, speeds)
    ]
    return Lap(number=number, samples=samples, lap_time_ms=raw[-1].last_lap_time_ms or None)


def extract_ghost_laps(path: Path, kind: GhostKind = "rival") -> GhostLaps | None:
    state = TelemetryState()
    laps: list[list[_Raw]] = []
    current: list[_Raw] = []
    car_index = NO_CAR
    lap_data_seen = False

    def handle(data: bytes) -> None:
        nonlocal current, car_index, lap_data_seen
        kind_id = state.feed(data)
        if kind_id is PacketId.LAP_DATA:
            lap_data_seen = True
            return
        if kind_id is not PacketId.CAR_TELEMETRY or not lap_data_seen or state.lap is None:
            return
        lap_data_seen = False
        idx = state.lap.time_trial_rival_car_idx if kind == "rival" else state.lap.time_trial_pb_car_idx
        if idx == NO_CAR or idx >= len(state.lap.cars):
            return
        car_index = idx
        lap = state.lap.cars[idx]
        car = state.telemetry.cars[idx]  # type: ignore[union-attr]
        if lap.lap_distance < 0:
            return
        if current and lap.lap_distance < current[-1].distance_m - 1000:
            laps.append(current)  # duch wrócił na linię mety: nowe okrążenie
            current = []
        if current and lap.lap_distance <= current[-1].distance_m:
            return  # brak postępu: duch czeka na gracza albo powtórzony pakiet
        current.append(_Raw(
            lap.lap_distance, lap.current_lap_time_ms, car.throttle, car.brake, car.gear, car.steer,
            lap.last_lap_time_ms,
        ))

    replay(path, handle, speed=0)
    if current:
        laps.append(current)
    if car_index == NO_CAR or not laps:
        return None
    name = None
    if state.participants is not None and car_index < len(state.participants.cars):
        name = state.participants.cars[car_index].name or None
    return GhostLaps(kind, car_index, name, [_to_lap(i + 1, raw) for i, raw in enumerate(laps)])
