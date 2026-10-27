from boxbox.coach.ers import ErsLapReport, advise_ers, analyze_ers
from boxbox.coach.ers_sample import ErsSample
from boxbox.coach.laps import Lap
from tests.conftest import RecordedSession
from tests.synthetic import LENGTH, track


def test_monza_practice_ers_goes_to_straights(monza: RecordedSession) -> None:
    lap = monza.lap(6)
    assert lap.ers_assist is True and len(lap.ers) > 1000
    report = analyze_ers(lap, lap.ers, monza.track)
    assert report is not None
    assert report.deployed_j > 1_000_000 and report.harvested_j > report.deployed_j
    assert report.wasted_ratio < 0.1  # asysta: deploy na prostych
    assert 0.9 < report.store_end_ratio <= 1.0
    advice = advise_ers(report, lap.ers_assist)
    assert advice.kind == "assist_on"


def test_time_trial_has_full_battery(bahrajn: RecordedSession) -> None:
    lap = bahrajn.lap(2)
    report = analyze_ers(lap, lap.ers, bahrajn.track)
    assert report is not None and report.deployed_j == 0 and report.store_end_ratio == 1.0


def _samples(deploy_in_corner_ratio: float, end_store: float) -> list[ErsSample]:
    t = track()
    out = []
    deployed = 0.0
    for d in range(0, int(LENGTH), 10):
        from boxbox.tracks.model import corner_at
        in_corner = corner_at(t, d) is not None
        deployed += 1000.0 * (deploy_in_corner_ratio if in_corner else (1 - deploy_in_corner_ratio))
        out.append(ErsSample(float(d), end_store, deployed, deployed * 1.5, 1))
    return out


def test_advice_without_assist() -> None:
    t = track()
    lap = Lap(2, [], 90_000)
    wasted = analyze_ers(lap, _samples(0.8, 2_000_000), t)
    assert wasted is not None and wasted.wasted_ratio > 0.25
    assert advise_ers(wasted, False).kind == "wasted_in_corners"
    unused = analyze_ers(lap, _samples(0.05, 3_900_000), t)
    assert advise_ers(unused, False).kind == "unused_battery"
    assert "ostatnim" in advise_ers(unused, False, last_lap=True).text
    ok = analyze_ers(lap, _samples(0.05, 1_000_000), t)
    assert advise_ers(ok, False).kind == "ok"
    assert advise_ers(None, False).kind == "no_data"
    assert analyze_ers(lap, [], t) is None
