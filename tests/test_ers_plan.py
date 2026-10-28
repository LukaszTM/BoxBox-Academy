"""Plan baterii: proste z okrążenia referencyjnego, budżet 33 s, ocena deployu, ostrzeżenie przed prostą."""
from boxbox.coach.ers import ERS_MAX_J
from boxbox.coach.ers_plan import BUDGET_S, describe, empty_before_straight, plan, review, straights
from boxbox.coach.ers_sample import ErsSample
from boxbox.coach.laps import Lap, Sample
from boxbox.coach.live import LiveCoach
from boxbox.coach.laps import LapRecorder
from boxbox.telemetry.replay import replay
from boxbox.tracks.model import Corner, Track
from tests.conftest import RecordedSession
from tests.test_live import MONZA


def test_monza_plan_prefers_main_straight(monza: RecordedSession) -> None:
    ref = monza.lap(6)
    segs = straights(monza.track, ref)
    assert len(segs) == 6 and all(s.length_m >= 120 for s in segs)
    wrap = segs[-1]
    assert wrap.from_corner == "T11" and wrap.to_corner == "T1-T2" and wrap.end_m < wrap.start_m and 1100 < wrap.length_m < 1400  # wyjście z Parabolica do hamowania na Rettifilo
    assert 10 < wrap.seconds < 20  # ok. 1,3 km z 230-330 km/h
    p = plan(monza.track, ref)
    assert p.longest is wrap_in(p) and p.longest.deploy and p.longest.share > 0.3
    planned = p.planned
    assert 2 <= len(planned) <= 5 and abs(sum(min(s.seconds, s.share * BUDGET_S) for s in planned) - BUDGET_S) < 0.5
    assert p.straight_at(100.0, monza.track.length_m) is p.longest and p.straight_at(ref_apex(monza), monza.track.length_m) is None
    text = describe(p)
    assert text.startswith("Deploy na prostych: po ") and "po T11" in text and "pełnej mocy" in text  # w kolejności toru
    # ocena: asysta ERS na treningu wydaje baterię na prostych, więc większość deployu jest na planie
    rev = review(p, ref.ers, monza.track.length_m)
    assert rev is not None and rev.deployed_j > 1_000_000 and rev.on_plan_ratio > 0.6


def wrap_in(p):
    return p.straights[-1]


def ref_apex(monza: RecordedSession) -> float:
    return monza.track.corners[0].apex_m


def test_review_and_empty_warning_synthetic() -> None:
    track = Track(1, "t", 3000.0, (Corner(1, 400.0, 500.0, 600.0, "T1"), Corner(2, 1500.0, 1600.0, 1700.0, "T2"), Corner(3, 2800.0, 2850.0, 2900.0, "T3")))
    samples = [Sample(float(d), int(d * 30), 250, 1.0, 0.0, 7, 0.0) for d in range(0, 3000, 10)]  # stałe 30 ms na 10 m
    ref = Lap(1, samples, lap_time_ms=90_000)
    p = plan(track, ref, budget_s=5.0)
    # proste: 600-1500 (900 m, 27 s), 1700-2800 (1100 m, 33 s), 2900->400 przez metę (500 m, 15 s)
    assert [round(s.seconds) for s in p.straights] == [27, 33, 15] and p.longest.number == 2
    assert [s.deploy for s in p.straights] == [False, True, False] and p.straights[1].share == 1.0  # budżet 5 s mieści się w jednej
    assert p.straight_at(2950.0, 3000.0).number == 3 and p.straight_at(100.0, 3000.0).number == 3 and p.straight_at(450.0, 3000.0) is None
    # deploy 300 kJ w T1 (poza planem) + 700 kJ na prostej 2 (na planie)
    ers = [ErsSample(0.0, 4e6, 0.0, 0.0, 1), ErsSample(450.0, 4e6, 0.0, 0.0, 1), ErsSample(550.0, 3.7e6, 300_000.0, 0.0, 1),
           ErsSample(1800.0, 3.7e6, 300_000.0, 0.0, 1), ErsSample(2500.0, 3.0e6, 1_000_000.0, 0.0, 1)]
    rev = review(p, ers, 3000.0)
    assert rev is not None and rev.deployed_j == 1_000_000 and rev.on_plan_j == 700_000 and rev.ok
    bad = review(p, [ErsSample(0.0, 4e6, 0.0, 0.0, 1), ErsSample(500.0, 3e6, 1_000_000.0, 0.0, 1)], 3000.0)
    assert bad is not None and not bad.ok and bad.on_plan_ratio == 0.0
    assert review(p, [], 3000.0) is None
    # ostrzeżenie: najdłuższa prosta zaczyna się na 1700 m; bateria 10 %
    assert empty_before_straight(p, 1500.0, 0.1 * ERS_MAX_J, 3000.0) is p.straights[1]
    assert empty_before_straight(p, 1500.0, 0.5 * ERS_MAX_J, 3000.0) is None  # bateria jest
    assert empty_before_straight(p, 1000.0, 0.1 * ERS_MAX_J, 3000.0) is None  # za daleko
    assert empty_before_straight(p, 1750.0, 0.1 * ERS_MAX_J, 3000.0) is None  # już na prostej


def test_live_builds_plan_from_first_reference(monza: RecordedSession) -> None:
    recorder = LapRecorder()
    spoken: list[list[str]] = []
    coach = LiveCoach(monza.track, lambda ids, text: spoken.append(ids), None)
    replay(MONZA, lambda data: coach.update(recorder, recorder.feed(data)), speed=0)
    assert coach.ers_plan is not None and coach.ers_plan.longest.from_corner == "T11"
    # trening z asystą ERS: trener nie ostrzega ani nie ocenia baterii
    assert not any(i in ("misc_ers_empty_straight", "misc_ers_off_plan") for ids in spoken for i in ids)
