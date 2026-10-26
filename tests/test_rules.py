"""Reguły trenera na nagraniach ze znanymi błędami i na czystych okrążeniach."""
from pathlib import Path

import pytest

from boxbox.coach.corners import analyze_lap
from boxbox.coach.ghost import extract_ghost_laps
from boxbox.coach.laps import Lap, Sample
from boxbox.coach.rules import Message, evaluate_lap, pick_top
from tests.conftest import RECORDINGS, RecordedSession
from tests.synthetic import gear_at, pedals_at, speed_at, track
from tests.test_laps import synthetic_samples


def messages(session: RecordedSession, lap_num: int, ref_num: int) -> list[Message]:
    lap, ref = session.lap(lap_num), session.lap(ref_num)
    return evaluate_lap(lap, analyze_lap(lap, session.track), analyze_lap(ref, session.track), session.track)


def by_corner(msgs: list[Message]) -> dict[int, list[str]]:
    out: dict[int, list[str]] = {}
    for m in msgs:
        out.setdefault(m.corner, []).append(m.rule)
    return out


def test_monza_known_errors_lap4(monza: RecordedSession) -> None:
    msgs = messages(monza, 4, 6)
    rules = by_corner(msgs)
    assert "brake_late" in rules[1]  # T1-T2: hamowanie 290 m później, obrót
    assert "brake_late" in rules[6]  # Parabolica: 209 m później, v_min 70 zamiast 173
    top = pick_top(msgs)
    assert 2 <= len(top) <= 3
    assert top[0].corner == 1 and top[0].weight >= top[-1].weight
    assert all(m.problem and m.hint and m.corner_name for m in top)
    assert len({m.corner for m in top}) == len(top)  # jeden komunikat na zakręt


def test_monza_clean_lap_is_quiet(monza: RecordedSession) -> None:
    from boxbox.coach.rules import biggest_loss
    msgs = messages(monza, 3, 6)
    assert [m.corner for m in pick_top(msgs)] in ([], [1])  # 1:28.0 vs 1:26.9; T1-T2 traci 0,33 s, tuż przy progu
    soft = biggest_loss(msgs)
    assert soft is not None and soft.corner == 1 and soft.rule == "throttle_late"
    # okrążenie 2 (1:33.5) nie jest czyste: w T1-T2 traci 1,5 s, więc trener ma prawo mówić
    assert [m.corner for m in pick_top(messages(monza, 2, 6))][0] == 1


def test_suzuka_spin_without_tc(suzuka_pomiar: RecordedSession) -> None:
    msgs = messages(suzuka_pomiar, 2, 3)
    rules = by_corner(msgs)
    assert "brake_late" in rules[3]  # spinka: hamowanie 155 m później, v_min 15 km/h zamiast 74
    top = pick_top(msgs)
    assert top and top[0].corner == 3 and top[0].rule == "brake_late" and "zwolnić" in top[0].problem


def test_suzuka_errors_lap_throttle_spin(suzuka_bledy: RecordedSession) -> None:
    msgs = messages(suzuka_bledy, 4, 2)
    rules = by_corner(msgs)
    assert "grip_lost" in rules[4]  # Spoon: hamowanie nie później, gaz do dechy bez TC, obrót do 0 km/h
    assert "brake_late" in rules[3]  # spinka: 126 m później
    top = pick_top(msgs)
    assert top[0].rule == "grip_lost" and top[0].corner == 4 and "gazem" in top[0].hint


def test_bahrajn_clean_vs_own_best_is_quiet(bahrajn: RecordedSession) -> None:
    # 1:37.9 vs 1:37.5: jedyna uwaga to T8 (hamowanie 98 m później, 0,45 s), reszta poniżej progu
    top = pick_top(messages(bahrajn, 3, 2))
    assert [(m.corner, m.rule) for m in top] in ([], [(4, "brake_late")])


def test_bahrajn_vs_ghost_says_brake_earlier_and_throttle_late(bahrajn: RecordedSession) -> None:
    ghost = extract_ghost_laps(RECORDINGS / "bahrajn-tt_2026-10-26_122816.bin.xz", "rival")
    assert ghost is not None
    ref = analyze_lap(ghost.best_lap(bahrajn.track.length_m), bahrajn.track)
    lap = bahrajn.lap(2)
    msgs = evaluate_lap(lap, analyze_lap(lap, bahrajn.track), ref, bahrajn.track)
    rules = by_corner(msgs)
    assert "brake_early" in rules[8] and "throttle_late" in rules[8]  # T14: -48 m hamowanie, +39 m gaz, +1.05 s
    assert "brake_release" in rules[1]  # duch puszcza hamulec 0,77 s, gracz 0,05 s
    top = pick_top(msgs)
    assert len(top) == 3 and top[0].corner == 3 and top[0].rule == "throttle_early"  # T5-T7: 1.5 s, duch nie hamuje


def _lap_with(samples: list[Sample], number: int = 2) -> Lap:
    return Lap(number, samples, 90_000)


def test_abrupt_brake_release_synthetic() -> None:
    t = track()
    ref = analyze_lap(_lap_with(synthetic_samples()), t)
    abrupt = []
    for s in synthetic_samples():
        throttle, brake = pedals_at(s.distance_m)
        if 0.0 < brake < 0.5:  # faza trail-brakingu zamieniona na zero: pedał puszczony naraz
            brake = 0.0
        abrupt.append(Sample(s.distance_m, s.lap_time_ms, s.speed_kmh, throttle, brake, s.gear, 0.0))
    lap = _lap_with(abrupt)
    msgs = evaluate_lap(lap, analyze_lap(lap, t), ref, t)
    assert {m.rule for m in msgs} == {"brake_release"}
    assert {m.corner for m in msgs} == {1, 2, 3, 4}
    assert "stopniowo" in msgs[0].hint


def test_gear_rule_synthetic() -> None:
    t = track()
    ref = analyze_lap(_lap_with(synthetic_samples()), t)
    low = [Sample(s.distance_m, s.lap_time_ms, s.speed_kmh, s.throttle, s.brake, max(1, s.gear - 2), 0.0) for s in synthetic_samples()]
    lap = _lap_with(low)
    msgs = evaluate_lap(lap, analyze_lap(lap, t), ref, t)
    assert all(m.rule == "gear_low" for m in msgs) and len(msgs) == 4
    assert "bieg" in msgs[0].hint
    assert pick_top(msgs) == []  # sam bieg bez straty czasu nie przebija progu
    from boxbox.coach.rules import biggest_loss
    assert biggest_loss(msgs) is None  # i nie jest "najwięcej do zyskania"


def test_messages_are_silent_without_reference() -> None:
    t = track()
    lap = _lap_with(synthetic_samples())
    assert evaluate_lap(lap, analyze_lap(lap, t), None, t) == []
