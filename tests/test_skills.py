"""Profil umiejętności 0–100: wzory na danych syntetycznych, nagranie Monzy, zapis i odczyt z bazy, profil łączny."""
from dataclasses import replace

from boxbox.coach.corners import CornerMetrics, analyze_lap
from boxbox.coach.rules import evaluate_lap
from boxbox.coach.skills import (
    DIMENSIONS, MIN_LAPS, WINDOW, LapRecord, combine, profile_for_track, profile_past, profiles_from_db, render, skill_profile,
)
from boxbox.storage.db import Database
from tests.conftest import RecordedSession


def _m(corner: int, brake: float, full: float, time_ms: int = 5000, max_brake: float = 0.9, release: float | None = 0.6) -> CornerMetrics:
    return CornerMetrics(corner, 120, brake + 100, 3, 250, 180, time_ms, brake, full, brake + 90, release, max_brake)


REF = (_m(1, 500.0, 700.0), _m(2, 1500.0, 1700.0, max_brake=0.5, release=0.1))


def _lap(time_ms: int = 90000, corners=REF, messages=(), valid: bool = True, tc: int = 1, abs_on: bool = True) -> LapRecord:
    return LapRecord(time_ms, valid, True, False, tuple(corners), tuple(messages), tc, abs_on)


def test_perfect_laps_score_100_and_too_few_laps_give_none() -> None:
    laps = [_lap() for _ in range(6)]
    p = skill_profile(laps, REF, 90000, {1: "T1", 2: "T2"}, 3, "Bahrajn")
    assert [s.key for s in p.skills] == [d[0] for d in DIMENSIONS]
    assert {s.key: s.score for s in p.skills} == {"braking": 100, "brake_control": 100, "throttle": 100, "consistency": 100, "pace": 100, "independence": 25}
    assert p.laps_used == 6 and p.note == "" and all(s.trend is None for s in p.skills)
    few = skill_profile(laps[:MIN_LAPS - 1], REF, 90000)
    assert few.note.startswith("za mało danych") and all(s.score is None for s in few.skills if s.key != "independence")
    assert few.by_key("independence").score == 25  # krok asyst liczony zawsze (TC średnia = krok 2 = 25 pkt)


def test_braking_throttle_and_grip_formulas_with_hints() -> None:
    late = [_m(1, 540.0, 700.0), _m(2, 1500.0, 1760.0, max_brake=0.5, release=0.1)]  # T1 +40 m hamowania, T2 +60 m gazu
    p = skill_profile([_lap(corners=late) for _ in range(6)], REF, 90000, {1: "T1", 2: "T2"})
    assert p.by_key("braking").score == 75 and "40 m wcześniej w T1" in p.by_key("braking").hint
    assert p.by_key("throttle").score == 75 and "60 m wcześniej" in p.by_key("throttle").hint and "T2" in p.by_key("throttle").hint
    spun = [_lap(corners=late, messages=((1, "grip_lost", 3.0),)) for _ in range(6)]
    q = skill_profile(spun, REF, 90000, {1: "T1", 2: "T2"})
    assert q.by_key("braking").score == 50 and q.by_key("throttle").score == 25  # zakręt z obrotem = 0, drugi jak wyżej (100 i 50)
    assert "przyczepność" in q.by_key("throttle").hint and "T1" in q.by_key("throttle").hint
    assert q.by_key("consistency").score == 50 and "0 z 6 okrążeń czystych" in q.by_key("consistency").hint
    assert q.by_key("pace").score is None  # bez czystego okrążenia nie ma tempa
    # praca hamulcem: w T1 referencja puszcza stopniowo (0,6 s), gracz naraz (0,1 s) -> połowa składnika
    abrupt = [_m(1, 500.0, 700.0, release=0.1), REF[1]]
    r = skill_profile([_lap(corners=abrupt) for _ in range(6)], REF, 90000, {1: "T1", 2: "T2"})
    assert 50 < r.by_key("brake_control").score < 100 and "stopniowo" in r.by_key("brake_control").hint and "T1" in r.by_key("brake_control").hint
    weak = [_m(1, 500.0, 700.0, max_brake=0.4), REF[1]]
    w = skill_profile([_lap(corners=weak) for _ in range(6)], REF, 90000, {1: "T1", 2: "T2"})
    assert w.by_key("brake_control").score < 100 and "hamuj mocniej w T1" in w.by_key("brake_control").hint


def test_consistency_pace_independence_and_trend() -> None:
    slow = [_lap(time_ms=90000 + 900 * (i % 3)) for i in range(6)]  # rozrzut średniej do najlepszego 1 %
    p = skill_profile(slow, REF, 90000)
    assert 40 < p.by_key("consistency").score < 100 and "rozrzut" in p.by_key("consistency").hint
    assert p.by_key("pace").score == 80  # 1 % straty do referencji z 5 % = 0
    assert "1,0 %" in p.by_key("pace").hint
    # tempo z zakrętem, który traci czas
    lossy = [_lap(time_ms=91000, corners=[replace(REF[0], time_ms=5400), REF[1]]) for _ in range(6)]
    assert "najwięcej czasu tracisz w zakręt 1: 0,4 s" in skill_profile(lossy, REF, 90000).by_key("pace").hint
    # samodzielność: krok z postępu, seria dodaje do 25 pkt
    assert skill_profile(slow, REF, 90000, step=4, streak=3).by_key("independence").score == 100
    s = skill_profile(slow, REF, 90000, step=3, streak=1)
    assert s.by_key("independence").score == 58 and "2 czyste okrążenia do kroku: ABS wyłączony" in s.by_key("independence").hint
    assert skill_profile([_lap(tc=0, abs_on=False)], REF).by_key("independence").hint == "jedziesz bez asyst"
    # trend: poprzednie okno gorsze o 40 m hamowania -> teraz lepiej
    worse = [_lap(corners=[_m(1, 540.0, 700.0), REF[1]]) for _ in range(WINDOW)]
    t = skill_profile(worse + [_lap() for _ in range(WINDOW)], REF, 90000)
    assert t.by_key("braking").score == 100 and t.by_key("braking").trend == 25
    # referencja zewnętrzna (duch) zmienia opis podstawy
    ext = skill_profile(slow, REF, 90000, external_reference=True)
    assert "ducha" in ext.by_key("braking").basis and "ducha" in ext.by_key("pace").basis and "ducha" not in ext.by_key("consistency").basis


def test_monza_recording_profile_and_render(monza: RecordedSession) -> None:
    ref_lap = monza.lap(6)
    ref = analyze_lap(ref_lap, monza.track)
    laps = []
    for lap in monza.recorder.laps:
        analysis = analyze_lap(lap, monza.track)
        msgs = tuple((m.corner, m.rule, m.weight) for m in evaluate_lap(lap, analysis, ref, monza.track))
        laps.append(LapRecord(lap.lap_time_ms, not lap.invalid, lap.is_complete(monza.track.length_m), lap.pitted, analysis.corners, msgs, lap.traction_control, lap.abs_on))
    names = {c.number: c.name for c in monza.track.corners}
    p = skill_profile(laps, ref.corners, ref_lap.lap_time_ms, names, 11, "Monza")
    assert p.laps_used == 5 and p.note == ""
    scores = {s.key: s.score for s in p.skills}
    assert all(v is not None and 0 <= v <= 100 for v in scores.values()), scores
    # okrążenie 4 z hamowaniem dużo za późno w T1-T2 obniża hamowanie i powtarzalność poniżej profilu z samych czystych
    clean = skill_profile([lap for lap in laps if lap.clean] * 3, ref.corners, ref_lap.lap_time_ms, names)  # powtórzone, żeby było >= 5
    assert scores["braking"] < clean.by_key("braking").score and scores["consistency"] < clean.by_key("consistency").score
    assert "T1-T2" in p.by_key("consistency").hint
    text = render(p)
    assert text.startswith("Monza: 5 okrążeń") and "Hamowanie" in text and "Samodzielność" in text


def test_profile_from_database_and_combined(tmp_path, monza: RecordedSession) -> None:
    db = Database(tmp_path / "s.sqlite")
    sid = db.save_session(monza.recorder.state.session, "test")
    ref = analyze_lap(monza.lap(6), monza.track)
    for lap in monza.recorder.laps:
        analysis = analyze_lap(lap, monza.track)
        lap_id = db.save_lap(sid, lap, analysis, monza.track.length_m, track_id=11, traction_control=lap.traction_control, abs_on=lap.abs_on)
        db.save_messages(lap_id, evaluate_lap(lap, analysis, ref, monza.track))
    p = profile_for_track(db, 11, "Monza", {c.number: c.name for c in monza.track.corners})
    assert p.track_id == 11 and p.laps_used == 5 and all(s.score is not None for s in p.skills)
    assert 0 < p.by_key("pace").score < 100 and "T1-T2" in p.by_key("pace").hint  # tempo z czystych okrążeń (bez okr. 4)
    # profile z bazy: Monza + łączny na końcu (nazwy zakrętów z pliku toru)
    profiles = profiles_from_db(db)
    assert [x.track_name for x in profiles] == ["Monza", "wszystkie tory"]
    assert profiles[0].to_dict()["skills"][0]["name"] == "Hamowanie" and "T1-T2" in profiles[0].by_key("consistency").hint
    both = combine([profiles[0], skill_profile([_lap() for _ in range(5)], REF, 90000, track_id=3, track_name="Bahrajn")])
    assert both.track_name == "wszystkie tory" and both.laps_used == 10
    b, m = both.by_key("braking").score, profiles[0].by_key("braking").score
    assert m < b < 100  # średnia ważona okrążeniami: między Monzą a idealnym Bahrajnem
    assert both.by_key("braking").hint == profiles[0].by_key("braking").hint  # podpowiedź z najsłabszego toru
    empty = combine([skill_profile([], None, track_id=3, track_name="Bahrajn")])
    assert all(s.score is None for s in empty.skills)
    # „ty miesiąc temu”: profil z okrążeń zapisanych do danej chwili; za mało okrążeń wtedy = None
    assert profile_past(db, 11) is None  # wszystko zapisane dziś
    db.conn.execute("UPDATE laps SET created_at = '2026-09-01 10:00:00' WHERE number <= 3")
    db.conn.commit()
    old = profile_for_track(db, 11, "Monza", until="2026-09-02 00:00:00")
    assert old.laps_used == 3 and old.note.startswith("za mało danych")
    db.conn.execute("UPDATE laps SET created_at = '2026-09-01 10:00:00'")
    db.conn.commit()
    past = profile_past(db, 11, track_name="Monza")
    assert past is not None and past.laps_used == 5 and past.by_key("braking").score == profiles[0].by_key("braking").score
    assert "[" in render(profiles[0], past) and render(profiles[0]).count("[") == 0
    db.close()
