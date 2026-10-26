"""Tabela zakrętów dla każdego pełnego okrążenia z nagrania.

Użycie: python -m boxbox.coach.analyze recordings/<plik>.bin [--track boxbox/tracks/data/<id>.json]
"""
import argparse
from collections.abc import Sequence
from pathlib import Path

from boxbox.coach.corners import LapAnalysis, analyze_lap
from boxbox.coach.laps import Lap, LapRecorder
from boxbox.telemetry.replay import replay
from boxbox.tracks.model import Track, load_track, track_path


def record_laps(path: Path) -> LapRecorder:
    recorder = LapRecorder()
    replay(path, recorder.feed, speed=0)
    return recorder


def format_time(ms: int | None) -> str:
    if ms is None:
        return "-"
    return f"{ms // 60000}:{(ms % 60000) / 1000:06.3f}"


def _fmt_m(value: float | None) -> str:
    return f"{value:6.0f}" if value is not None else "     -"


def render_table(analysis: LapAnalysis, lap: Lap) -> str:
    flags = " (nieważne)" if lap.invalid else ""
    lines = [f"Okrążenie {analysis.lap_number}{flags}: {format_time(analysis.lap_time_ms)}"]
    lines.append("  zakręt  v_min  bieg  hamow.   apex  p.gaz   v_wej  v_wyj   czas")
    for m in analysis.corners:
        lines.append(
            f"  Z{m.corner:<5} {m.min_speed_kmh:4d}   {m.gear_at_apex:2d}  {_fmt_m(m.brake_point_m)} "
            f"{m.apex_m:6.0f} {_fmt_m(m.full_throttle_m)}   {m.entry_speed_kmh:4d}  {m.exit_speed_kmh:4d}  {m.time_ms / 1000:5.2f}"
        )
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Metryki zakrętów z nagrania")
    parser.add_argument("recording", type=Path)
    parser.add_argument("--track", type=Path, help="plik JSON toru; domyślnie wg track_id z nagrania")
    args = parser.parse_args(argv)

    recorder = record_laps(args.recording)
    session = recorder.state.session
    path = args.track or (track_path(session.track_id) if session else None)
    if path is None:
        print("Nagranie nie ma pakietu Session - podaj --track.")
        return 1
    try:
        track: Track = load_track(path)
    except FileNotFoundError as exc:
        print(f"{exc}. Wyznacz zakręty: python -m boxbox.tracks.detect {args.recording}")
        return 1
    laps = [lap for lap in recorder.laps if lap.is_complete(track.length_m)]
    if recorder.current is not None and recorder.current.is_complete(track.length_m):
        laps.append(recorder.current)
    if not laps:
        print("Brak pełnych okrążeń w nagraniu.")
        return 1
    print(f"{track.name}, {len(track.corners)} zakrętów, {len(laps)} pełnych okrążeń\n")
    for lap in laps:
        print(render_table(analyze_lap(lap, track), lap))
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
