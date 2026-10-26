"""Tabela zakrętów dla każdego pełnego okrążenia z nagrania.

Użycie: python -m boxbox.coach.analyze recordings/<plik>.bin [--track boxbox/tracks/data/<id>.json]
"""
import argparse
from collections.abc import Sequence
from pathlib import Path

from boxbox.coach.compare import compare_to_reference
from boxbox.coach.corners import LapAnalysis, analyze_lap
from boxbox.coach.laps import Lap, LapRecorder
from boxbox.telemetry.replay import replay
from boxbox.storage.db import Database
from boxbox.tracks.model import load_track, track_path


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


def _fmt_delta(value: float | None, width: int = 6, unit: str = "", digits: int = 0) -> str:
    if value is None:
        return "-".rjust(width)
    return f"{value:+.{digits}f}{unit}".rjust(width)


def render_table(analysis: LapAnalysis, lap: Lap, reference: LapAnalysis | None = None) -> str:
    """Tabela zakrętów; z referencją dochodzą kolumny różnic (Δ = to okrążenie minus referencja)."""
    flags = " (nieważne)" if lap.invalid else ""
    header = f"Okrążenie {analysis.lap_number}{flags}: {format_time(analysis.lap_time_ms)}"
    deltas = {}
    if reference is not None:
        header += f"   referencja: okrążenie {reference.lap_number} {format_time(reference.lap_time_ms)}"
        deltas = {d.corner: d for d in compare_to_reference(analysis, reference)}
    lines = [header, "  zakręt  v_min  bieg  hamow.   apex  p.gaz   v_wej  v_wyj   czas"]
    if reference is not None:
        lines[1] += "  | Δv_min  Δhamow  Δp.gaz   Δczas"
    for m in analysis.corners:
        line = (
            f"  Z{m.corner:<5} {m.min_speed_kmh:4d}   {m.gear_at_apex:2d}  {_fmt_m(m.brake_point_m)} "
            f"{m.apex_m:6.0f} {_fmt_m(m.full_throttle_m)}   {m.entry_speed_kmh:4d}  {m.exit_speed_kmh:4d}  {m.time_ms / 1000:5.2f}"
        )
        if reference is not None:
            d = deltas.get(m.corner)
            if d is None:
                line += "  |  (brak zakrętu w referencji)"
            else:
                line += (
                    f"  | {_fmt_delta(d.min_speed_delta_kmh)} {_fmt_delta(d.brake_point_delta_m, 7, 'm')}"
                    f" {_fmt_delta(d.full_throttle_delta_m, 7, 'm')} {_fmt_delta(d.time_delta_ms / 1000, 7, 's', 2)}"
                )
        lines.append(line)
    return "\n".join(lines)


def report_laps(
    recorder: LapRecorder, track_file: Path | None, db_path: Path | None, source: str
) -> str:
    """Zapisuje pełne okrążenia do bazy i zwraca tabele zakrętów z różnicą do referencji.

    Bez pliku toru zwraca jedną linię z powodem; aplikacja ma wtedy działać dalej.
    """
    session = recorder.state.session
    path = track_file or (track_path(session.track_id) if session else None)
    if path is None:
        return "Brak pakietu Session - nie wiadomo, który to tor."
    try:
        track = load_track(path)
    except FileNotFoundError as exc:
        return f"{exc}. Wyznacz zakręty: python -m boxbox.tracks.detect {source}"
    laps = [lap for lap in recorder.laps if lap.is_complete(track.length_m)]
    if recorder.current is not None and recorder.current.is_complete(track.length_m):
        laps.append(recorder.current)
    if not laps:
        return "Brak pełnych okrążeń."
    analyses = {lap.number: analyze_lap(lap, track) for lap in laps}
    reference: LapAnalysis | None = None
    if db_path is not None:
        db = Database(db_path)
        session_id = db.save_session(session, source=source)
        status = recorder.state.status.player if recorder.state.status else None
        for lap in laps:
            db.save_lap(
                session_id, lap, analyses[lap.number], track.length_m, track_id=track.track_id,
                gearbox=session.assists.gearbox if session else None,
                traction_control=status.traction_control if status else None,
                abs_on=status.anti_lock_brakes if status else None,
            )
        ref = db.reference(track.track_id)
        reference = ref.analysis if ref else None
        db.close()
    lines = [f"{track.name}, {len(track.corners)} zakrętów, {len(laps)} pełnych okrążeń", ""]
    for lap in laps:
        lines += [render_table(analyses[lap.number], lap, reference), ""]
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Metryki zakrętów z nagrania")
    parser.add_argument("recording", type=Path)
    parser.add_argument("--track", type=Path, help="plik JSON toru; domyślnie wg track_id z nagrania")
    parser.add_argument("--db", type=Path, help="baza SQLite; bez niej tylko tabela, bez zapisu i referencji")
    args = parser.parse_args(argv)

    recorder = record_laps(args.recording)
    text = report_laps(recorder, args.track, args.db, str(args.recording))
    print(text)
    return 0 if "Okrążenie" in text else 1


if __name__ == "__main__":
    raise SystemExit(main())
