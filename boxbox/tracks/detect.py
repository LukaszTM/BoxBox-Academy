"""Wyznaczanie zakrętów z profilu prędkości jednego okrążenia.

Zakręt to lokalne minimum prędkości o spadku co najmniej `min_drop_kmh` względem
prostych po obu stronach. Granice z pedałów: wejście = początek ciągłego hamowania
przed apeksem, wyjście = pierwszy pełny gaz po apeksie. Bez danych pedałów (lub gdy
ich brak w oknie) zapasowo z prędkości: wejście tam, gdzie spadła o 10% różnicy
między prostą a apeksem, wyjście tam, gdzie odzyskała 90%.

Uwaga z nagrania Bahrajn TT: kompleksy zakrętów, w których prędkość po pierwszym
zakręcie już tylko rośnie (np. Z1-Z3), dają jedno minimum, czyli jedną strefę.

Użycie: python -m boxbox.tracks.detect recordings/<plik>.bin [--out boxbox/tracks/data/<id>.json]
"""
import argparse
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from boxbox.telemetry.replay import replay
from boxbox.telemetry.state import TelemetryState
from boxbox.tracks.model import Corner, Track, save_track, track_path


@dataclass(frozen=True)
class SpeedSample:
    distance_m: float
    speed_kmh: float
    throttle: float | None = None  # 0-1; None = brak danych pedałów
    brake: float | None = None


BRAKE_ON = 0.1
FULL_THROTTLE = 0.95


def _smooth(values: list[float], window: int) -> list[float]:
    half = window // 2
    out = []
    for i in range(len(values)):
        lo, hi = max(0, i - half), min(len(values), i + half + 1)
        out.append(sum(values[lo:hi]) / (hi - lo))
    return out


def detect_corners(
    samples: Sequence[SpeedSample],
    track_length_m: float,
    min_drop_kmh: float = 25.0,
    window: int = 9,
    edge_fraction: float = 0.9,
    max_reach_m: float = 400.0,
) -> tuple[Corner, ...]:
    """Zwraca zakręty ponumerowane od 1 w kolejności dystansu."""
    if len(samples) < window:
        return ()
    ordered = sorted(samples, key=lambda s: s.distance_m)
    dist = [s.distance_m for s in ordered]
    speed = _smooth([s.speed_kmh for s in ordered], window)
    n = len(speed)

    minima = [i for i in range(1, n - 1) if speed[i] <= speed[i - 1] and speed[i] < speed[i + 1]]

    def bounds_max(idx_list: list[int], k: int) -> tuple[float, float]:
        """Maksimum prędkości między k-tym minimum a sąsiednimi (lub końcami okrążenia)."""
        lo = idx_list[k - 1] if k > 0 else 0
        hi = idx_list[k + 1] if k + 1 < len(idx_list) else n - 1
        return max(speed[lo:idx_list[k] + 1]), max(speed[idx_list[k]:hi + 1])

    # Usuwaj najmniej wyraźne minimum, aż wszystkie mają spadek >= min_drop (łączy szykany).
    while minima:
        weakest, weakest_drop = -1, float("inf")
        for k, i in enumerate(minima):
            left, right = bounds_max(minima, k)
            drop = min(left, right) - speed[i]
            if drop < weakest_drop:
                weakest, weakest_drop = k, drop
        if weakest_drop >= min_drop_kmh:
            break
        del minima[weakest]

    brake = [s.brake for s in ordered]
    throttle = [s.throttle for s in ordered]

    def entry_from_brake(i: int) -> int | None:
        j = i
        while j > 0 and dist[i] - dist[j] <= max_reach_m and (brake[j] is None or brake[j] < BRAKE_ON):
            j -= 1
        if brake[j] is None or brake[j] < BRAKE_ON:
            return None
        while j > 0 and brake[j - 1] is not None and brake[j - 1] >= BRAKE_ON:  # type: ignore[operator]
            j -= 1
        return j

    def exit_from_throttle(i: int) -> int | None:
        for j in range(i, n):
            if dist[j] - dist[i] > max_reach_m:
                return None
            if throttle[j] is not None and throttle[j] >= FULL_THROTTLE:  # type: ignore[operator]
                return j
        return None

    corners = []
    for k, i in enumerate(minima):
        left, right = bounds_max(minima, k)
        v_min = speed[i]
        entry = entry_from_brake(i)
        if entry is None:
            entry = i
            while entry > 0 and speed[entry] < v_min + edge_fraction * (left - v_min):
                entry -= 1
        exit_ = exit_from_throttle(i)
        if exit_ is None:
            exit_ = i
            while exit_ < n - 1 and speed[exit_] < v_min + edge_fraction * (right - v_min):
                exit_ += 1
        corners.append(Corner(k + 1, round(dist[entry], 1), round(dist[i], 1), round(dist[exit_], 1)))
    return tuple(corners)


@dataclass
class LapSamples:
    samples: list[SpeedSample]

    @property
    def coverage(self) -> tuple[float, float]:
        d = [s.distance_m for s in self.samples]
        return (min(d), max(d)) if d else (0.0, 0.0)


def collect_laps(path: Path) -> tuple[TelemetryState, dict[int, LapSamples]]:
    """Próbki (dystans, prędkość) auta gracza pogrupowane po numerze okrążenia."""
    state = TelemetryState()
    laps: dict[int, LapSamples] = defaultdict(lambda: LapSamples([]))

    def handle(data: bytes) -> None:
        state.feed(data)
        if state.lap is None or state.telemetry is None:
            return
        lap = state.lap.player
        if lap.lap_distance < 0 or lap.pit_status != 0:
            return
        car = state.telemetry.player
        laps[lap.current_lap_num].samples.append(
            SpeedSample(lap.lap_distance, float(car.speed_kmh), car.throttle, car.brake)
        )

    replay(path, handle, speed=0)
    return state, dict(laps)


def pick_full_lap(laps: dict[int, LapSamples], track_length_m: float, min_coverage: float = 0.95) -> int | None:
    best, best_cov = None, 0.0
    for num, lap in laps.items():
        lo, hi = lap.coverage
        cov = (hi - lo) / track_length_m
        if lo <= 0.05 * track_length_m and cov >= min_coverage and cov > best_cov:
            best, best_cov = num, cov
    return best


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Wyznacza zakręty toru z nagrania telemetrii")
    parser.add_argument("recording", type=Path)
    parser.add_argument("--out", type=Path, help="domyślnie boxbox/tracks/data/<track_id>.json")
    parser.add_argument("--min-drop", type=float, default=25.0, help="min. spadek prędkości w zakręcie (km/h)")
    parser.add_argument("--track-length", type=float, help="długość toru w m, jeśli brak pakietu Session")
    args = parser.parse_args(argv)

    state, laps = collect_laps(args.recording)
    if state.session is None and args.track_length is None:
        print("Nagranie nie ma pakietu Session - podaj --track-length i --out.")
        return 1
    length = args.track_length or float(state.session.track_length_m)  # type: ignore[union-attr]
    track_id = state.session.track_id if state.session else -1
    name = state.session.track_name if state.session else args.recording.stem
    lap_num = pick_full_lap(laps, length)
    if lap_num is None:
        print("Brak pełnego okrążenia w nagraniu (potrzebne co najmniej jedno od linii mety do linii mety).")
        for num, lap in sorted(laps.items()):
            lo, hi = lap.coverage
            print(f"  okrążenie {num}: {lo:.0f}-{hi:.0f} m, {len(lap.samples)} próbek")
        return 1
    corners = detect_corners(laps[lap_num].samples, length, min_drop_kmh=args.min_drop)
    track = Track(track_id=track_id, name=name, length_m=length, corners=corners, source=str(args.recording))
    out = args.out or track_path(track_id)
    save_track(track, out)
    print(f"{name} ({length:.0f} m), okrążenie {lap_num}, {len(corners)} zakręty -> {out}")
    for c in corners:
        print(f"  Z{c.number}: wejście {c.entry_m:.0f} m, apex {c.apex_m:.0f} m, wyjście {c.exit_m:.0f} m")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
