"""Analiza telemetrii jako dane (bez wykresów): delta czasu do referencji wzdłuż toru, eksport CSV.

Okno (etap 7) tylko rysuje to, co tu policzone; raport PDF i CSV używają tych samych funkcji.
"""
import csv
import io
from bisect import bisect_left
from collections.abc import Sequence
from dataclasses import dataclass

from boxbox.coach.laps import Sample

GRID_M = 10.0


@dataclass(frozen=True)
class DeltaPoint:
    distance_m: float
    delta_s: float  # dodatnia = wolniej niż referencja (strata narasta)
    speed_kmh: float
    ref_speed_kmh: float


def _time_at(samples: Sequence[Sample], distances: list[float], d: float) -> float | None:
    """Czas okrążenia (s) w punkcie d przez interpolację między próbkami; None poza zakresem."""
    i = bisect_left(distances, d)
    if i == 0:
        return samples[0].lap_time_ms / 1000 if distances and distances[0] <= d else None
    if i >= len(samples):
        return None
    a, b = samples[i - 1], samples[i]
    span = b.distance_m - a.distance_m
    t = (d - a.distance_m) / span if span > 0 else 0.0
    return (a.lap_time_ms + (b.lap_time_ms - a.lap_time_ms) * t) / 1000


def _speed_at(samples: Sequence[Sample], distances: list[float], d: float) -> float:
    i = bisect_left(distances, d)
    if i == 0:
        return float(samples[0].speed_kmh)
    if i >= len(samples):
        return float(samples[-1].speed_kmh)
    a, b = samples[i - 1], samples[i]
    span = b.distance_m - a.distance_m
    t = (d - a.distance_m) / span if span > 0 else 0.0
    return a.speed_kmh + (b.speed_kmh - a.speed_kmh) * t


def _clean(samples: Sequence[Sample]) -> list[Sample]:
    """Próbki rosnąco po dystansie, bez cofnięć (np. z linii mety) i ujemnych dystansów."""
    out: list[Sample] = []
    for s in samples:
        if s.distance_m < 0:
            continue
        if out and s.distance_m <= out[-1].distance_m:
            continue
        out.append(s)
    return out


def delta_trace(samples: Sequence[Sample], reference: Sequence[Sample], grid_m: float = GRID_M) -> list[DeltaPoint]:
    """Delta czasu gracz − referencja co `grid_m` metrów, wyzerowana na początku wspólnego odcinka."""
    own, ref = _clean(samples), _clean(reference)
    if len(own) < 2 or len(ref) < 2:
        return []
    od = [s.distance_m for s in own]
    rd = [s.distance_m for s in ref]
    start = max(od[0], rd[0])
    end = min(od[-1], rd[-1])
    t0_own = _time_at(own, od, start)
    t0_ref = _time_at(ref, rd, start)
    if t0_own is None or t0_ref is None:
        return []
    out: list[DeltaPoint] = []
    d = (start // grid_m + 1) * grid_m
    while d <= end:
        t_own = _time_at(own, od, d)
        t_ref = _time_at(ref, rd, d)
        if t_own is not None and t_ref is not None:
            out.append(DeltaPoint(d, (t_own - t0_own) - (t_ref - t0_ref), _speed_at(own, od, d), _speed_at(ref, rd, d)))
        d += grid_m
    return out


def biggest_losses(trace: Sequence[DeltaPoint], window_m: float = 150.0, top: int = 3) -> list[tuple[float, float]]:
    """Odcinki toru, gdzie delta rośnie najszybciej: (dystans początku odcinka, strata w s w oknie)."""
    if len(trace) < 2:
        return []
    step = trace[1].distance_m - trace[0].distance_m
    n = max(1, int(window_m / step))
    gains = []
    for i in range(len(trace) - n):
        gains.append((trace[i].distance_m, trace[i + n].delta_s - trace[i].delta_s))
    gains.sort(key=lambda g: -g[1])
    picked: list[tuple[float, float]] = []
    for d, loss in gains:
        if loss <= 0:
            break
        if all(abs(d - p[0]) >= window_m for p in picked):
            picked.append((d, loss))
        if len(picked) == top:
            break
    return picked


CSV_COLUMNS = ("dystans_m", "czas_s", "predkosc_kmh", "gaz", "hamulec", "bieg", "kierownica")


def lap_csv(samples: Sequence[Sample], reference: Sequence[Sample] | None = None) -> str:
    """CSV okrążenia (średnik, przecinek dziesiętny jak w polskim Excelu); z referencją dokłada deltę."""
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";", lineterminator="\n")
    cols = list(CSV_COLUMNS) + (["delta_s", "predkosc_ref_kmh"] if reference else [])
    w.writerow(cols)
    deltas = {p.distance_m: p for p in delta_trace(samples, reference)} if reference else {}

    def num(x: float, nd: int = 3) -> str:
        return f"{x:.{nd}f}".replace(".", ",")

    for s in _clean(samples):
        row = [num(s.distance_m, 1), num(s.lap_time_ms / 1000), str(s.speed_kmh), num(s.throttle, 2), num(s.brake, 2), str(s.gear), num(s.steer, 2)]
        if reference:
            key = round(s.distance_m / GRID_M) * GRID_M
            p = deltas.get(key)
            row += [num(p.delta_s) if p else "", num(p.ref_speed_kmh, 0) if p else ""]
        w.writerow(row)
    return buf.getvalue()
