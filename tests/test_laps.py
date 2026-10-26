from pathlib import Path

import pytest

from boxbox.coach.analyze import main
from boxbox.coach.corners import analyze_lap
from boxbox.coach.laps import Lap, LapRecorder, Sample
from boxbox.telemetry.recording import RecordingWriter
from boxbox.tracks.model import save_track
from tests.builders import lap_packet, session_packet, status_packet, telemetry_packet
from tests.synthetic import CORNERS, LENGTH, gear_at, pedals_at, speed_at, track


def synthetic_samples(step_m: float = 2.0, start: float = 0.0, stop: float = LENGTH) -> list[Sample]:
    out = []
    d = start
    while d < stop:
        throttle, brake = pedals_at(d)
        out.append(Sample(d, int(d / stop * 90_000), int(speed_at(d)), throttle, brake, gear_at(d), 0.0))
        d += step_m
    return out


def test_analyze_corner_metrics() -> None:
    lap = Lap(number=2, samples=synthetic_samples(), lap_time_ms=90_000)
    analysis = analyze_lap(lap, track())
    assert analysis.lap_number == 2 and analysis.lap_time_ms == 90_000
    assert [c.corner for c in analysis.corners] == [1, 2, 3, 4]
    for m, (apex, v_min, hw) in zip(analysis.corners, CORNERS):
        assert m.min_speed_kmh == pytest.approx(v_min, abs=2)
        assert m.apex_m == pytest.approx(apex, abs=3)
        assert m.gear_at_apex == gear_at(apex)
        assert m.brake_point_m == pytest.approx(apex - 0.8 * hw, abs=3)  # początek hamowania
        assert m.full_throttle_m == pytest.approx(apex + 0.5 * hw, abs=3)  # pełny gaz na wyjściu
        assert m.entry_speed_kmh > m.min_speed_kmh < m.exit_speed_kmh
        assert m.time_ms > 0


def test_missing_pedal_events_give_none() -> None:
    samples = [Sample(s.distance_m, s.lap_time_ms, s.speed_kmh, 0.5, 0.0, s.gear, 0.0) for s in synthetic_samples()]
    m = analyze_lap(Lap(1, samples, None), track()).corners[0]
    assert m.brake_point_m is None and m.full_throttle_m is None
    assert m.min_speed_kmh == pytest.approx(90, abs=2)


def test_corner_without_samples_is_skipped() -> None:
    lap = Lap(1, synthetic_samples(stop=2000.0), None)
    assert [c.corner for c in analyze_lap(lap, track()).corners] == [1, 2]


def test_wrap_corner_uses_samples_from_both_sides() -> None:
    from boxbox.tracks.model import Corner, Track
    t = Track(3, "x", LENGTH, (Corner(1, 4950.0, 10.0, 60.0),))
    samples = [Sample(d, 0, 100 if d >= 4950 or d <= 60 else 300, 1.0, 0.0, 3, 0.0) for d in range(0, 5000, 2)]
    m = analyze_lap(Lap(1, samples, None), t).corners[0]
    assert m.min_speed_kmh == 100 and (m.apex_m >= 4950 or m.apex_m <= 60)


def feed(recorder: LapRecorder, lap_num: int, distance: float, speed: int, invalid: bool = False, pit: int = 0) -> Lap | None:
    recorder.feed(lap_packet(lap_distance=distance, lap_num=lap_num, lap_invalid=invalid, pit_status=pit))
    return recorder.feed(telemetry_packet(speed=speed))


def test_recorder_splits_laps_and_flags() -> None:
    rec = LapRecorder()
    rec.feed(session_packet())
    assert feed(rec, 1, 3000.0, 200) is None
    assert feed(rec, 1, 3500.0, 210, invalid=True) is None
    done = feed(rec, 2, 5.0, 220)
    assert done is not None and done.number == 1 and done.invalid is True and len(done.samples) == 2
    assert done.lap_time_ms == 83_123  # z last_lap_time_ms pakietu, który zaczął okrążenie 2
    assert feed(rec, 2, 100.0, 230, pit=1) is None  # pit lane: próbka pominięta, okrążenie oznaczone
    assert feed(rec, 2, 200.0, 240) is None
    done = feed(rec, 3, 3.0, 250)
    assert done is not None and done.number == 2 and done.pitted is True and done.invalid is False
    assert [s.distance_m for s in done.samples] == [5.0, 200.0]
    assert rec.current is not None and rec.current.number == 3
    assert [lap.number for lap in rec.laps] == [1, 2]


def test_recorder_ignores_negative_distance_and_duplicate_frames() -> None:
    rec = LapRecorder()
    rec.feed(lap_packet(lap_distance=-20.0, lap_num=1))
    assert rec.feed(telemetry_packet(speed=50)) is None
    assert rec.current is None  # przed linią mety nic nie zbieramy
    rec.feed(lap_packet(lap_distance=10.0, lap_num=1))
    rec.feed(telemetry_packet(speed=60))
    rec.feed(telemetry_packet(speed=60))  # ten sam dystans, bez nowego Lap Data
    assert rec.current is not None and len(rec.current.samples) == 1


def test_lap_is_complete_only_when_it_covers_the_track() -> None:
    assert Lap(1, synthetic_samples(), 90_000).is_complete(LENGTH)
    assert not Lap(1, synthetic_samples(start=3000.0), 90_000).is_complete(LENGTH)
    assert not Lap(1, synthetic_samples(stop=4000.0), 90_000).is_complete(LENGTH)


def make_recording(path: Path) -> None:
    with RecordingWriter(path) as w:
        w.write(0.0, session_packet())
        t = 0.0
        for lap, (start, stop) in ((1, (3000.0, LENGTH)), (2, (0.0, LENGTH)), (3, (0.0, 1500.0))):
            d = start
            while d < stop:
                throttle, brake = pedals_at(d)
                w.write(t, lap_packet(lap_distance=d, lap_num=lap, lap_invalid=False, current_lap_time_ms=int(d / stop * 90_000)))
                w.write(t, telemetry_packet(speed=int(speed_at(d)), throttle=throttle, brake=brake, gear=gear_at(d)))
                d += 2.0
                t += 1 / 60


def test_cli_prints_corner_table(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    rec = tmp_path / "r.bin"
    make_recording(rec)
    track_file = tmp_path / "3.json"
    save_track(track(), track_file)
    assert main([str(rec), "--track", str(track_file)]) == 0
    out = capsys.readouterr().out
    assert "Okrążenie 2" in out and "Okrążenie 1" not in out  # tylko pełne okrążenia
    assert "Z3" in out and " 70 " in out  # min. prędkość w zakręcie 3


def test_cli_without_track_file(tmp_path: Path) -> None:
    rec = tmp_path / "r.bin"
    make_recording(rec)
    assert main([str(rec), "--track", str(tmp_path / "missing.json")]) == 1


def test_recorder_votes_assists_per_lap() -> None:
    import struct
    from boxbox.telemetry import car_status as cs
    from tests.builders import PLAYER
    rec = LapRecorder()
    rec.feed(session_packet())

    def status(tc: int) -> bytes:
        raw = bytearray(status_packet())
        offset = 29 + PLAYER * cs._CAR[2025].size
        struct.pack_into("<B", raw, offset, tc)
        return bytes(raw)

    rec.feed(status(2))  # TC pełna jeszcze w garażu
    feed(rec, 1, 5.0, 100)
    rec.feed(status(0))  # wyłączona na okrążeniu
    for d in (100.0, 200.0, 300.0):
        feed(rec, 1, d, 150)
    done = feed(rec, 2, 3.0, 200)
    assert done is not None and done.number == 1
    assert (done.gearbox, done.traction_control, done.abs_on) == (3, 0, True)  # większość próbek bez TC
