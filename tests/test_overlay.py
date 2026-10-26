import json
from pathlib import Path

from boxbox.telemetry.state import TelemetryState
from boxbox.tracks.model import Corner
from boxbox.ui.overlay_model import (
    GUIDE_DIR, build_view, calibrate_guide, load_guide, load_guide_for, load_plan, save_guide,
)
from tests.builders import lap_packet, session_packet, telemetry_packet

PLANS = Path(__file__).parent.parent / "tools" / "package" / "plany"


def test_guides_and_plans_load() -> None:
    guides = sorted(GUIDE_DIR.glob("*.json"))
    assert {g.stem for g in guides} >= {"3", "11", "13"}
    for g in guides:
        guide = load_guide(g)
        assert guide.corners and all(0 < c.apex_m < guide.length_m for c in guide.corners)
        assert [c.apex_m for c in guide.corners] == sorted(c.apex_m for c in guide.corners)
    for p in sorted(PLANS.glob("*.json")):
        plan = load_plan(p)
        assert plan.title and plan.laps
        if plan.tasks:
            guide_id = {"bahrajn-tt": 3, "monza-trening": 11, "suzuka-tt-bez-tc": 13}[p.stem]
            names = {c.name for c in load_guide(GUIDE_DIR / f"{guide_id}.json").corners}
            assert set(plan.tasks) <= names, (p.name, set(plan.tasks) - names)


def test_next_corner_and_wrap() -> None:
    guide = load_guide(GUIDE_DIR / "3.json")
    corner, dist = guide.next_corner(500.0)
    assert corner.name == "T1" and dist == 257
    corner, _ = guide.next_corner(780.0)  # 23 m za apeksem T1: nadal T1
    assert corner.name == "T1"
    corner, _ = guide.next_corner(800.0)
    assert corner.name == "T2-T3"
    corner, dist = guide.next_corner(5400.0)  # za ostatnim: wraca do T1 przez metę
    assert corner.name == "T1" and dist == 5408 - 5400 + 757


def test_view_waiting_and_live(tmp_path: Path) -> None:
    plan = load_plan(PLANS / "bahrajn-tt.json")
    state = TelemetryState()
    view = build_view(state, plan, None, 0, "x.bin")
    assert view.title.startswith("Sesja 1") and "czekam" in view.status_line and view.lap_line == ""
    state.feed(session_packet())
    state.feed(lap_packet(lap_distance=700.0, lap_num=4, lap_invalid=False))
    state.feed(telemetry_packet(speed=250, gear=5))
    guide = load_guide_for(3)
    view = build_view(state, plan, guide, 1000, "x.bin")
    assert view.lap_line == "OKRĄŻENIE 4" and view.goal_line.startswith("Celowe błędy")
    assert view.corner_line == "T1  za 57 m" and view.task_line == "HAMUJ ZA PÓŹNO"
    assert "250 km/h, bieg 5" in view.status_line and "nagrywam: x.bin" in view.status_line
    # czyste okrążenie: zakręt pokazany, zadania brak
    state.feed(lap_packet(lap_distance=1500.0, lap_num=2, lap_invalid=False))
    state.feed(telemetry_packet())
    view = build_view(state, plan, guide, 1001, None)
    assert view.corner_line == "T4  za 74 m" and view.task_line == "" and "bez nagrywania" in view.status_line
    # tuż przed apeksem: TERAZ
    state.feed(lap_packet(lap_distance=1570.0, lap_num=4, lap_invalid=False))
    state.feed(telemetry_packet())
    view = build_view(state, plan, guide, 1002, None)
    assert view.corner_line == "T4  TERAZ" and view.task_line == "GAZ DO DECHY W APEKSIE"


def test_view_without_guide_and_orientational_flag(tmp_path: Path) -> None:
    plan = load_plan(PLANS / "monza-trening.json")
    state = TelemetryState()
    state.feed(session_packet())
    state.feed(lap_packet(lap_distance=100.0, lap_num=1, lap_invalid=False))
    state.feed(telemetry_packet())
    assert "brak przewodnika" in build_view(state, plan, None, 5, None).corner_line
    guide = load_guide_for(11)
    assert "orientacyjne" in build_view(state, plan, guide, 5, None).status_line


def test_plan_goal_after_last_lap() -> None:
    plan = load_plan(PLANS / "bahrajn-tt.json")
    assert plan.goal_for_lap(6).startswith("Zjazd")
    assert plan.goal_for_lap(9) == plan.goal_for_lap(6)
    assert plan.goal_for_lap(0) == ""


def test_calibrate_guide_snaps_to_detected_zones(tmp_path: Path) -> None:
    guide = load_guide(GUIDE_DIR / "11.json")  # Monza, orientacyjny
    zones = (
        Corner(1, 560, 700, 760),  # T1-T2 (przewodnik: 640)
        Corner(2, 1950, 2110, 2170),  # T4-T5 (2050)
        Corner(3, 2400, 2560, 2600),  # T6 (2520)
        Corner(4, 2700, 2900, 2950),  # T7 (2830)
        Corner(5, 3500, 3600, 3650),  # strefa spoza przewodnika
        Corner(6, 4050, 4250, 4300),  # T8-T10 (4200)
        Corner(7, 4950, 5180, 5250),  # T11 (5100)
    )
    cal = calibrate_guide(guide, zones)
    by_name = {c.name: c.apex_m for c in cal.corners}
    assert by_name["T1-T2"] == 700 and by_name["T7"] == 2900 and by_name["T11"] == 5180
    assert by_name["T3"] == 1250  # bez strefy hamowania: zostaje
    assert by_name["hamowanie 1"] == 3600
    assert [c.apex_m for c in cal.corners] == sorted(c.apex_m for c in cal.corners)
    assert cal.accuracy.startswith("skalibrowane")
    out = tmp_path / "g.json"
    save_guide(cal, out)
    again = load_guide(out)
    assert again.corners == cal.corners
    state = TelemetryState()
    state.feed(session_packet())
    state.feed(lap_packet(lap_distance=100.0, lap_num=2, lap_invalid=False))
    state.feed(telemetry_packet())
    assert "skalibrowane" in build_view(state, load_plan(PLANS / "monza-trening.json"), cal, 5, None).status_line
