import json
from pathlib import Path

import pytest

from boxbox.tracks.detect import SpeedSample, detect_corners, main
from boxbox.telemetry.recording import RecordingWriter
from tests.builders import lap_packet, session_packet, telemetry_packet

from tests.synthetic import CORNERS, LENGTH, gear_at, pedals_at, speed_at


def synthetic_lap(step_m: float = 1.5) -> list[SpeedSample]:
    n = int(LENGTH / step_m)
    return [SpeedSample(i * step_m, speed_at(i * step_m)) for i in range(n)]


def test_detects_all_corners_with_sensible_bounds() -> None:
    corners = detect_corners(synthetic_lap(), LENGTH)
    assert [c.number for c in corners] == [1, 2, 3, 4]
    for found, (apex, _, half_width) in zip(corners, CORNERS):
        assert found.apex_m == pytest.approx(apex, abs=5)
        assert apex - half_width < found.entry_m < apex  # hamowanie zaczyna się przed apeksem
        assert apex < found.exit_m < apex + half_width  # wyjście kończy się przed powrotem na prostą
        # 10% spadku prędkości na kosinusowej dolinie wypada 0,795 szerokości przed apeksem
        assert found.entry_m == pytest.approx(apex - half_width * 0.795, abs=15)
        assert found.exit_m == pytest.approx(apex + half_width * 0.795, abs=15)


def test_pedals_define_bounds_when_available() -> None:
    samples = [SpeedSample(s.distance_m, s.speed_kmh, *pedals_at(s.distance_m)) for s in synthetic_lap()]
    corners = detect_corners(samples, LENGTH)
    assert len(corners) == 4
    for found, (apex, _, hw) in zip(corners, CORNERS):
        assert found.entry_m == pytest.approx(apex - 0.8 * hw, abs=3)  # początek hamowania
        assert found.exit_m == pytest.approx(apex + 0.5 * hw, abs=3)  # pełny gaz


def test_speed_fallback_when_pedals_missing_in_window() -> None:
    # pedały tylko w pierwszym zakręcie; reszta ma None -> granice z prędkości
    samples = [
        SpeedSample(s.distance_m, s.speed_kmh, *(pedals_at(s.distance_m) if s.distance_m < 1000 else (None, None)))
        for s in synthetic_lap()
    ]
    corners = detect_corners(samples, LENGTH)
    assert corners[0].entry_m == pytest.approx(600 - 0.8 * 120, abs=3)
    assert corners[1].entry_m == pytest.approx(1500 - 0.795 * 150, abs=15)


def test_small_dips_are_not_corners() -> None:
    samples = [SpeedSample(s.distance_m, s.speed_kmh - (15 if 2400 < s.distance_m < 2450 else 0)) for s in synthetic_lap()]
    assert len(detect_corners(samples, LENGTH, min_drop_kmh=25)) == 4


def test_chicane_counts_once() -> None:
    # dwa minima 40 m od siebie z małym wzrostem prędkości między nimi
    samples = []
    for s in synthetic_lap():
        v = s.speed_kmh
        if 2380 < s.distance_m < 2420:
            v = 95.0 + 8 * abs(s.distance_m - 2400) / 20  # 95 w obu dołkach, 103 pośrodku
        elif 2300 < s.distance_m <= 2380:
            v = 300 - (300 - 103) * (s.distance_m - 2300) / 80
        elif 2420 <= s.distance_m < 2500:
            v = 103 + (300 - 103) * (s.distance_m - 2420) / 80
        samples.append(SpeedSample(s.distance_m, v))
    corners = detect_corners(samples, LENGTH)
    assert len(corners) == 5
    assert 2370 < corners[2].apex_m < 2430


def test_empty_or_flat_profile() -> None:
    assert detect_corners([], LENGTH) == ()
    assert detect_corners([SpeedSample(i * 10.0, 300.0) for i in range(500)], LENGTH) == ()


def make_recording(path: Path) -> None:
    """Nagranie: okrążenie 1 niepełne, okrążenie 2 pełne z syntetycznym profilem, okrążenie 3 urwane."""
    with RecordingWriter(path) as w:
        w.write(0.0, session_packet())
        t = 0.0
        for lap, (start, stop) in ((1, (3000.0, LENGTH)), (2, (0.0, LENGTH)), (3, (0.0, 1000.0))):
            d = start
            while d < stop:
                throttle, brake = pedals_at(d)
                w.write(t, lap_packet(lap_distance=d, lap_num=lap))
                w.write(t, telemetry_packet(speed=int(speed_at(d)), throttle=throttle, brake=brake, gear=gear_at(d)))
                d += 2.0
                t += 1 / 60


def test_cli_writes_track_json(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    rec = tmp_path / "bahrajn.bin"
    make_recording(rec)
    out = tmp_path / "3.json"
    assert main([str(rec), "--out", str(out), "--track-length", str(LENGTH)]) == 0
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["track_id"] == 3 and data["name"] == "Bahrajn" and data["length_m"] == LENGTH
    assert [c["number"] for c in data["corners"]] == [1, 2, 3, 4]
    assert data["corners"][2]["apex_m"] == pytest.approx(3200, abs=6)
    assert data["corners"][2]["entry_m"] == pytest.approx(3200 - 80, abs=4)  # z hamulca
    assert data["corners"][2]["exit_m"] == pytest.approx(3200 + 50, abs=4)  # z gazu
    assert data["source"].endswith("bahrajn.bin")
    out_text = capsys.readouterr().out
    assert "okrążenie 2" in out_text and "4 zakręty" in out_text


def test_cli_without_full_lap(tmp_path: Path) -> None:
    rec = tmp_path / "short.bin"
    with RecordingWriter(rec) as w:
        w.write(0.0, session_packet())
        for i in range(50):
            w.write(i / 60, lap_packet(lap_distance=i * 2.0, lap_num=1))
            w.write(i / 60, telemetry_packet(speed=250))
    assert main([str(rec), "--out", str(tmp_path / "x.json")]) == 1
