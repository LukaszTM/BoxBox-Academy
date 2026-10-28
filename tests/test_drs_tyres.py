"""DRS (strefy, reakcja, pominięcia) i opony (temperatury, zużycie, prognoza) na nagraniach i danych syntetycznych."""
from boxbox.coach.drs import LATE_MS, DrsAdvice, advise_drs, analyze_drs
from boxbox.coach.lap_samples import DrsSample, TyreSample
from boxbox.coach.tyres import TyreLapReport, advise_tyres, analyze_tyres, forecast_laps
from boxbox.voice.phrases import MISC_TEXTS, catalog, track_corner_names
from tests.conftest import RecordedSession


def test_monza_lap_has_two_drs_zones_with_fast_reaction(monza: RecordedSession) -> None:
    lap = monza.lap(3)
    assert len(lap.drs) > 1000 and len(lap.tyres) > 150 and lap.drs_assist is True  # trening z asystą DRS
    report = analyze_drs(lap.drs)
    assert report is not None and len(report.zones) == 2
    z1, z2 = report.zones
    assert 0 < z1.allowed_m < 40 and 700 < z1.end_m < 800  # prosta startowa do Rettifilo
    assert 3000 < z2.allowed_m < 3100 and 3700 < z2.end_m < 3900  # Serraglio do Ascari... do Parabolica
    assert all(z.reaction_ms is not None and z.reaction_ms < 100 and z.lost_m < 10 for z in report.zones)
    assert report.missed == () and report.late == () and report.worst is None
    assert advise_drs(report, False).kind == "none"
    assert advise_drs(report, lap.drs_assist).kind == "assist_on" and advise_drs(None, False).kind == "no_zones"


def test_bahrain_zone_through_finish_line_is_not_double_counted(bahrajn: RecordedSession) -> None:
    lap = bahrajn.lap(2)
    report = analyze_drs(lap.drs)
    assert report is not None
    # okrążenie zaczyna się z otwartym DRS (strefa od 5302 m poprzedniego okrążenia): nie liczy się jako strefa 1
    assert report.zones[0].allowed_m > 900
    assert [round(z.allowed_m, -2) for z in report.zones] == [1000.0, 2800.0, 5300.0]  # ostatnia otwarta na mecie, włączona: liczy się
    assert report.zones[2].activated_m is not None and report.zones[2].end_m > 5300


def _drs(points: list[tuple[float, int, bool, bool]]) -> list[DrsSample]:
    return [DrsSample(d, t, a, on) for d, t, a, on in points]


def test_missed_and_late_zones_and_advice_text() -> None:
    # strefa 1: lampka 100 m / 1000 ms, włączony 150 m / 1800 ms (za późno); strefa 2: lampka, nigdy nie włączył
    samples = _drs([
        (0.0, 0, False, False), (100.0, 1000, True, False), (120.0, 1300, True, False), (150.0, 1800, False, True),
        (400.0, 5000, False, True), (500.0, 6000, False, False),
        (2000.0, 20000, True, False), (2300.0, 23000, True, False), (2400.0, 24000, False, False),
        (2420.0, 24100, True, False), (2440.0, 24200, False, False),  # 20 m: szum, nie strefa
    ])
    report = analyze_drs(samples)
    assert report is not None and len(report.zones) == 2
    late, missed = report.zones
    assert late.reaction_ms == 800 and late.lost_m == 50 and late.reaction_ms > LATE_MS
    assert missed.activated_ms is None and missed.end_m == 2400.0
    assert report.late == (late,) and report.missed == (missed,) and report.worst is missed
    advice = advise_drs(report, False)
    assert advice == DrsAdvice("missed", missed) and advice.clip == "misc_drs_missed"
    only_late = analyze_drs(samples[:6])
    assert advise_drs(only_late, False).kind == "late"
    entries = catalog(track_corner_names())
    for key in ("drs_missed", "drs_late", "tyres_rear_hot", "tyres_front_hot", "tyres_side_hot", "tyres_wear_fast", "tyres_wear_uneven"):
        assert entries[f"misc_{key}"] == MISC_TEXTS[key]


def test_monza_tyre_report_and_forecast(monza: RecordedSession) -> None:
    lap = monza.lap(3)
    report = analyze_tyres(lap.tyres)
    assert report is not None and report.samples > 150
    assert all(40 < t < 80 for t in report.avg_surface_c) and all(70 < t < 110 for t in report.avg_inner_c)
    assert report.wear_lap is not None and 0 < max(report.wear_lap) < 5 and report.hottest in ("RL", "FL")
    laps_left = forecast_laps(report)
    assert laps_left is not None and 5 < laps_left < 80
    advice = advise_tyres(report)
    assert advice.kind in ("none", "side_hot")  # Monza: lewa strona cieplejsza (zakręty w prawo), różnice małe


def _tyres(surface: tuple[int, int, int, int], wear_start=None, wear_end=None) -> list[TyreSample]:
    return [TyreSample(0.0, surface, surface, wear_start), TyreSample(1000.0, surface, surface, wear_end)]


def test_tyre_advice_rules_and_window() -> None:
    assert advise_tyres(None).kind == "none" and analyze_tyres([]) is None
    rear = analyze_tyres(_tyres((105, 104, 88, 87)))
    assert rear is not None and advise_tyres(rear).kind == "rear_hot" and rear.hottest == "RL" and rear.in_window
    front = analyze_tyres(_tyres((85, 85, 100, 101)))
    assert advise_tyres(front).kind == "front_hot" and not analyze_tyres(_tyres((60, 60, 60, 60))).in_window
    side = advise_tyres(analyze_tyres(_tyres((110, 90, 110, 90))))
    assert side.kind == "side_hot" and side.detail == "lewa"
    fast = analyze_tyres(_tyres((95, 95, 95, 95), (10.0, 10.0, 10.0, 10.0), (15.0, 12.0, 11.0, 11.0)))
    assert fast is not None and fast.wear_lap == (5.0, 2.0, 1.0, 1.0)
    assert advise_tyres(fast) .kind == "wear_fast" and advise_tyres(fast).detail == "lewy tył"
    assert forecast_laps(fast) == 11  # (70 - 15) // 5
    uneven = analyze_tyres(_tyres((95, 95, 95, 95), (30.0, 20.0, 20.0, 20.0), (31.0, 21.0, 21.0, 21.0)))
    assert advise_tyres(uneven).kind == "wear_uneven" and forecast_laps(uneven) == 39
    assert forecast_laps(TyreLapReport((90.0,) * 4, (90.0,) * 4, None, None, 2)) is None


def test_drs_and_ers_channels_round_trip_database_and_map(tmp_path, monza: RecordedSession) -> None:
    """Kanały DRS i ERS okrążenia trafiają do bazy i wracają bez zmian; strefy DRS lądują na mapie Analizy."""
    from boxbox.coach.corners import analyze_lap
    from boxbox.gui.data import map_for
    from boxbox.storage.db import Database

    lap = monza.lap(3)
    db = Database(tmp_path / "k.sqlite")
    sid = db.save_session(monza.recorder.state.session, "test")
    lap_id = db.save_lap(sid, lap, analyze_lap(lap, monza.track), monza.track.length_m, track_id=11)
    drs, ers = db.drs_samples(lap_id), db.ers_samples(lap_id)
    assert len(drs) == len(lap.drs) and len(ers) == len(lap.ers)
    assert drs[500].active == lap.drs[500].active and abs(drs[500].distance_m - lap.drs[500].distance_m) < 0.01
    assert abs(ers[700].store_j - lap.ers[700].store_j) < 1.0 and ers[700].deploy_mode == lap.ers[700].deploy_mode
    assert db.drs_samples(lap_id + 99) == () and db.ers_samples(lap_id + 99) == ()
    report = analyze_drs(list(drs))
    assert report is not None and len(report.zones) == 2
    zones = [(z.allowed_m, z.end_m, z.activated_m is not None) for z in report.zones]
    assert map_for(11, shape_dir=tmp_path, fit_dir=tmp_path, drs_zones=zones)["drsZones"] == []  # sam obrys atlasu: bez dystansów
    import math
    from boxbox.tracks.shape import build_shape, save_shape, shape_path
    length = monza.track.length_m  # kształt „z recordera”: okrąg o długości toru, dystanse są wtedy umieszczone
    circle = [(length * i / 400, 1000 * math.cos(2 * math.pi * i / 400), 1000 * math.sin(2 * math.pi * i / 400)) for i in range(400)]
    save_shape(build_shape(circle, 11, "Monza", length), shape_path(11, tmp_path))
    m = map_for(11, shape_dir=tmp_path, fit_dir=tmp_path, drs_zones=zones)
    assert m is not None and len(m["drsZones"]) == 2 and all(z["used"] and len(z["points"]) >= 2 for z in m["drsZones"])
    assert all(0 <= x <= 500 and 0 <= y <= 270 for z in m["drsZones"] for x, y in z["points"])
    db.close()
