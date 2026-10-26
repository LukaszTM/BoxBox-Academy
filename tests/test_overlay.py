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
    guide = load_guide_for(13)  # Suzuka: jeszcze bez nagrania, pozycje z pamięci
    assert "orientacyjne" in build_view(state, plan, guide, 5, None).status_line
    assert "orientacyjne" not in build_view(state, plan, load_guide_for(11), 5, None).status_line  # Monza z nagrania


def test_plan_goal_after_last_lap() -> None:
    plan = load_plan(PLANS / "bahrajn-tt.json")
    assert plan.goal_for_lap(6).startswith("Zjazd")
    assert plan.goal_for_lap(9) == plan.goal_for_lap(6)
    assert plan.goal_for_lap(0) == ""


def test_calibrate_guide_snaps_to_detected_zones(tmp_path: Path) -> None:
    guide = load_guide(GUIDE_DIR / "11.json")  # Monza (T1-T2 984, T4-T5 2154, T6 2616, T7 2905, T8-T10 3968, T11 5189)
    zones = (
        Corner(1, 900, 1100, 1160),  # T1-T2; bliżej T3 (1500)? nie, T3 jest "flat" i nie bierze udziału
        Corner(2, 2000, 2200, 2250),  # T4-T5
        Corner(3, 2500, 2560, 2600),  # T6
        Corner(4, 2800, 2900, 2950),  # T7
        Corner(5, 3400, 3450, 3500),  # strefa spoza przewodnika
        Corner(6, 3900, 4050, 4100),  # T8-T10
        Corner(7, 5000, 5180, 5250),  # T11
    )
    cal = calibrate_guide(guide, zones)
    by_name = {c.name: c.apex_m for c in cal.corners}
    assert by_name["T1-T2"] == 1100 and by_name["T7"] == 2900 and by_name["T11"] == 5180
    assert by_name["T3"] == 1500  # bez hamowania: zostaje
    assert by_name["hamowanie 1"] == 3450
    assert [c.apex_m for c in cal.corners] == sorted(c.apex_m for c in cal.corners)
    assert cal.accuracy.startswith("skalibrowane")
    out = tmp_path / "g.json"
    save_guide(cal, out)
    again = load_guide(out)
    assert again.corners == cal.corners
    assert next(c for c in again.corners if c.name == "T3").flat is True
    state = TelemetryState()
    state.feed(session_packet())
    state.feed(lap_packet(lap_distance=100.0, lap_num=2, lap_invalid=False))
    state.feed(telemetry_packet())
    assert "skalibrowane" in build_view(state, load_plan(PLANS / "monza-trening.json"), cal, 5, None).status_line


def test_resolve_plan(tmp_path: Path, capsys) -> None:
    from boxbox.ui.overlay_model import load_plan as _lp  # noqa: F401
    import importlib.util
    spec = importlib.util.spec_from_file_location("ov", Path("boxbox/ui/overlay.py"))
    try:
        import tkinter  # noqa: F401
    except ModuleNotFoundError:
        import pytest
        pytest.skip("brak tkinter w tym środowisku")
    ov = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ov)  # type: ignore[union-attr]
    assert ov.resolve_plan(None, "monza-trening-z-AI", PLANS).stem == "monza-trening"
    assert ov.resolve_plan(None, "suzuka", PLANS).stem == "suzuka-tt-bez-tc"
    assert ov.resolve_plan("bahrajn-tt", None, PLANS).stem == "bahrajn-tt"
    assert ov.resolve_plan(str(PLANS / "pakiet2026.json"), None, PLANS).stem == "pakiet2026"
    assert ov.resolve_plan("nie-ma", None, PLANS) is None
    assert "Dostępne" in capsys.readouterr().out


def test_checklist_and_progress() -> None:
    from boxbox.ui.overlay_model import checklist, update_progress
    plan = load_plan(PLANS / "bahrajn-tt.json")
    guide = load_guide_for(3)
    items = checklist(plan, guide, set())
    labels = [i.label for i in items]
    assert labels[0].startswith("Okr. 1:") and len([i for i in items if i.key.startswith("lap:")]) == 6
    assert "    T1: HAMUJ ZA PÓŹNO" in labels and "    T9-T10: ZAHAMUJ I PUŚĆ HAMULEC NARAZ" in labels
    assert len([i for i in items if i.key.startswith("task:4:")]) == 3 and len([i for i in items if i.key.startswith("task:5:")]) == 3
    assert not any(i.done for i in items)

    done: set[str] = set()
    state = TelemetryState()
    state.feed(session_packet())
    state.feed(lap_packet(lap_distance=800.0, lap_num=4, lap_invalid=False))  # za T1 na okrążeniu 4
    state.feed(telemetry_packet())
    update_progress(done, state, plan, guide)
    assert {"lap:1", "lap:2", "lap:3", "task:4:T1"} == done  # okrążenia 1-3 minęły, T1 zaliczone
    state.feed(lap_packet(lap_distance=3000.0, lap_num=4, lap_invalid=False))
    state.feed(telemetry_packet())
    update_progress(done, state, plan, guide)
    assert {"task:4:T4", "task:4:T9-T10"} <= done and "task:5:T1" not in done
    state.feed(lap_packet(lap_distance=50.0, lap_num=6, lap_invalid=False, pit_status=1))  # zjazd
    state.feed(telemetry_packet())
    update_progress(done, state, plan, guide)
    assert {"lap:4", "lap:5", "lap:6"} <= done
    view = build_view(state, plan, guide, 10, None, done)
    assert sum(1 for i in view.items if i.done) == 6 + 3
    assert all(i.done for i in view.items if i.key.startswith("lap:"))
