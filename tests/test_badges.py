"""Odznaki i cele dnia: warunki, postęp, zbieranie z bazy, seria dni."""
from boxbox.coach.badges import BADGE_DEFS, BadgeInput, badges, collect, day_streak, goal_text, goals_of_the_day, render
from boxbox.coach.corners import analyze_lap
from boxbox.coach.progress import TrackProgress
from boxbox.coach.rules import evaluate_lap
from boxbox.storage.db import Database
from tests.conftest import RecordedSession


def test_badges_progress_and_goals() -> None:
    empty = badges(BadgeInput())
    assert len(empty) == len(BADGE_DEFS) and not any(b.earned for b in empty)
    goals = goals_of_the_day(empty)
    assert len(goals) == 3 and all(b.target == 1 for b in goals)  # przy zerowym postępie: najmniejsze cele
    some = badges(BadgeInput(sessions=4, complete_laps=37, clean_laps=7, laps_no_tc=2, tracks_driven=2, day_streak=2, hours=1.2))
    by = {b.key: b for b in some}
    assert by["first_clean"].earned and by["no_tc"].earned and not by["no_assists"].earned
    assert by["clean_10"].value == 7 and by["clean_10"].remaining == 3 and round(by["clean_10"].fraction, 2) == 0.7
    assert by["hours_10"].value == 1 and by["laps_100"].fraction == 0.37
    goals = goals_of_the_day(some)
    assert [g.key for g in goals] == ["clean_10", "tracks_3", "sessions_10"]  # 0,7; 0,67; 0,4
    assert goal_text(by["clean_10"]) == "Dziesięć czystych: jeszcze 3 okrążenia"
    assert goal_text(by["tracks_3"]) == "Trzy tory: jeszcze 1 tor" and goal_text(by["streak_7"]) == "Tydzień z rzędu: jeszcze 5 dni"
    assert goal_text(by["sessions_10"]) == "Dziesięć sesji: jeszcze 6 sesji" and goal_text(by["hours_10"]) == "Dziesięć godzin: jeszcze 9 godzin"
    assert by["no_assists"].to_dict() == {"key": "no_assists", "name": "Bez asyst", "description": by["no_assists"].description,
                                          "target": 1, "value": 0, "unit": "okrążeń", "earned": False, "fraction": 0.0}
    text = render(some, goals)
    assert "[x] Pierwsze czyste okrążenie" in text and "[ ] Dziesięć czystych" in text and "Cele dnia:" in text


def test_day_streak_counts_back_from_last_session() -> None:
    assert day_streak([]) == 0
    assert day_streak(["2026-10-20", "2026-10-21", "2026-10-22"]) == 3
    assert day_streak(["2026-10-01", "2026-10-21 10:00", "2026-10-22"]) == 2
    assert day_streak(["2026-10-22", "2026-10-22"]) == 1


def test_collect_from_database(tmp_path, monza: RecordedSession) -> None:
    db = Database(tmp_path / "b.sqlite")
    ref = analyze_lap(monza.lap(6), monza.track)
    for n, laps in enumerate((monza.recorder.laps[:3], monza.recorder.laps[3:]), start=1):
        sid = db.save_session(monza.recorder.state.session, f"sesja {n}")
        for lap in laps:
            analysis = analyze_lap(lap, monza.track)
            lap_id = db.save_lap(sid, lap, analysis, monza.track.length_m, track_id=11, traction_control=0 if n == 2 else 1, abs_on=True)
            db.save_messages(lap_id, evaluate_lap(lap, analysis, ref, monza.track))
    db.conn.execute("UPDATE sessions SET created_at = CASE id WHEN 1 THEN '2026-10-25 18:00:00' ELSE '2026-10-26 18:00:00' END")
    db.save_progress(TrackProgress(11, step=4, streak=3))
    db.conn.commit()
    data = collect(db)
    assert data.sessions == 2 and data.complete_laps == 6 and data.tracks_driven == 1 and data.tracks_mastered == 1
    assert data.clean_laps == 2 and data.laps_no_tc == 2 and data.laps_no_assists == 0  # okr. 4 z dużym błędem, 5 nieważne, inne z uwagami > 1 s
    assert data.day_streak == 2 and data.improved_sessions == 1  # sesja 2 ma okrążenie 6 (najlepsze)
    assert 0.1 < data.hours < 0.2
    by = {b.key: b for b in badges(data)}
    assert by["first_clean"].earned and by["no_tc"].earned and by["track_mastered"].earned and by["faster"].earned
    assert not by["no_assists"].earned and by["clean_10"].value == 2
    db.close()
