"""Tabela zakrętów dla każdego pełnego okrążenia z nagrania.

Użycie: python -m boxbox.coach.analyze recordings/<plik>.bin [--track boxbox/tracks/data/<id>.json]
"""
import argparse
from collections.abc import Sequence
from pathlib import Path

from boxbox.coach.compare import compare_to_reference
from boxbox.coach.corners import LapAnalysis, analyze_lap
from boxbox.coach.ghost import extract_ghost_laps
from boxbox.coach.rules import evaluate_lap, pick_top
from boxbox.coach.laps import Lap, LapRecorder
from boxbox.telemetry.replay import replay
from boxbox.storage.db import Database
from boxbox.tracks.model import find_track_path, load_track
from boxbox.ui.console import TC_NAMES


def record_laps(path: Path) -> LapRecorder:
    recorder = LapRecorder()
    replay(path, recorder.feed, speed=0)
    return recorder


def format_time(ms: int | None) -> str:
    if ms is None:
        return "-"
    return f"{ms // 60000}:{(ms % 60000) / 1000:06.3f}"


def format_sector(ms: int | None) -> str:
    return "-" if ms is None else f"{ms / 1000:.3f}"


def _fmt_m(value: float | None) -> str:
    return f"{value:6.0f}" if value is not None else "     -"


def _fmt_delta(value: float | None, width: int = 6, unit: str = "", digits: int = 0) -> str:
    if value is None:
        return "-".rjust(width)
    return f"{value:+.{digits}f}{unit}".rjust(width)


def render_table(analysis: LapAnalysis, lap: Lap, reference: LapAnalysis | None = None) -> str:
    """Tabela zakrętów; z referencją dochodzą kolumny różnic (Δ = to okrążenie minus referencja)."""
    flags = " (nieważne)" if lap.invalid else ""
    if lap.traction_control is not None:
        flags += f" [TC {TC_NAMES.get(lap.traction_control, lap.traction_control)}, ABS {'wł.' if lap.abs_on else 'wył.'}]"
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
    recorder: LapRecorder,
    track_file: Path | None,
    db_path: Path | None,
    source: str,
    reference: str = "best",
    recording: Path | None = None,
) -> str:
    """Zapisuje pełne okrążenia do bazy i zwraca tabele zakrętów z różnicą do referencji.

    reference: "best" = najlepsze własne okrążenie z bazy; "rival"/"pb" = duch z Time Trial
    (wymaga `recording`, bo ducha czytamy z pliku osobno).
    Bez pliku toru zwraca jedną linię z powodem; aplikacja ma wtedy działać dalej.
    """
    session = recorder.state.session
    path = track_file or (find_track_path(session.track_id) if session else None)
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
    ref_analysis: LapAnalysis | None = None
    ref_label = ""
    if reference in ("rival", "pb") and recording is not None:
        ghost = extract_ghost_laps(recording, reference)  # type: ignore[arg-type]
        best = ghost.best_lap(track.length_m) if ghost else None
        if ghost is None or best is None:
            ref_label = f"brak ducha ({reference}) w nagraniu, porównanie do własnego najlepszego"
        else:
            ref_analysis = analyze_lap(best, track)
            ref_label = f"referencja: duch {ghost.name or reference} ({format_time(best.lap_time_ms)})"
    if db_path is not None:
        db = Database(db_path)
        session_id = db.save_session(session, source=source)
        lap_ids = {}
        for lap in laps:
            lap_ids[lap.number] = db.save_lap(
                session_id, lap, analyses[lap.number], track.length_m, track_id=track.track_id,
                gearbox=lap.gearbox, traction_control=lap.traction_control, abs_on=lap.abs_on,
            )
        if ref_analysis is None:
            ref = db.reference(track.track_id)
            ref_analysis = ref.analysis if ref else None
            if ref is not None and not ref.lap.valid:
                ref_label = "referencja: najlepsze okrążenie jest nieważne (brak ważnych), porównanie orientacyjne"
        if ref_analysis is not None:
            progress = db.load_progress(track.track_id)
            for lap in laps:
                msgs = evaluate_lap(lap, analyses[lap.number], ref_analysis, track)
                db.save_messages(lap_ids[lap.number], msgs)
                progress.record(lap, msgs)
            db.save_progress(progress)
        db.close()
    head = f"{track.name}, {len(track.corners)} zakrętów, {len(laps)} pełnych okrążeń"
    lines = [head + (f"; {ref_label}" if ref_label else ""), ""]
    for lap in laps:
        lines += [render_table(analyses[lap.number], lap, ref_analysis)]
        if lap.pitted:
            lines += ["  Trener: okrążenie z pit lane, bez oceny."]
        elif ref_analysis is not None and ref_analysis.lap_number != lap.number:
            top = pick_top(evaluate_lap(lap, analyses[lap.number], ref_analysis, track))
            lines += ["  Trener: " + (" | ".join(f"{m.corner_name}: {m.problem} {m.hint}" for m in top) if top else "czyste okrążenie, nic do poprawy.")]
        lines += [""]
    return "\n".join(lines)


def render_progress(db: Database, track_ids: list[int] | None = None) -> str:
    """Ekran postępu: tor, krok asyst, seria czystych okrążeń, najlepsze czasy per krok, zakręty opanowane."""
    from boxbox.coach.progress import CLEAN_LAPS_TO_ADVANCE, STEPS
    from boxbox.tracks.model import load_track_by_id

    if track_ids is None:
        rows = db.conn.execute("SELECT DISTINCT track_id FROM laps WHERE track_id IS NOT NULL ORDER BY track_id").fetchall()
        track_ids = [r["track_id"] for r in rows]
    if not track_ids:
        return "Brak zapisanych okrążeń."
    lines = []
    for tid in track_ids:
        try:
            track = load_track_by_id(tid)
        except FileNotFoundError:
            continue
        p = db.load_progress(tid)
        best = db.best_time_per_step(tid)
        issues = db.recent_corner_issues(tid)
        lines.append(f"{track.name}: krok {p.step} ({STEPS[p.step]}), czyste z rzędu {p.streak}/{CLEAN_LAPS_TO_ADVANCE}"
                     + (f", osiągnięte kroki: {sorted(p.achieved_steps)}" if p.achieved_steps else ""))
        for step, ms in sorted(best.items()):
            lines.append(f"  najlepszy czas, krok {step} ({STEPS[step]}): {format_time(ms)}")
        mastered = [c.name for c in track.corners if c.number not in issues]
        todo = [f"{c.name} ({', '.join(sorted(set(issues[c.number])))})" for c in track.corners if c.number in issues]
        lines.append(f"  zakręty opanowane (ostatnie 3 ważne okrążenia bez uwag): {', '.join(mastered) or 'jeszcze żaden'}")
        if todo:
            lines.append(f"  do pracy: {'; '.join(todo)}")
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Metryki zakrętów z nagrania")
    parser.add_argument("recording", type=Path)
    parser.add_argument("--track", type=Path, help="plik JSON toru; domyślnie wg track_id z nagrania")
    parser.add_argument("--db", type=Path, help="baza SQLite; bez niej tylko tabela, bez zapisu i referencji")
    parser.add_argument("--reference", choices=["best", "rival", "pb"], default="best", help="z czym porównywać")
    args = parser.parse_args(argv)

    recorder = record_laps(args.recording)
    text = report_laps(recorder, args.track, args.db, str(args.recording), args.reference, args.recording)
    print(text)
    return 0 if "Okrążenie" in text else 1


if __name__ == "__main__":
    raise SystemExit(main())
