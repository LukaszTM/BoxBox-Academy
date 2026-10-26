import socket
from pathlib import Path

import pytest

from boxbox.app import main as app_main
from boxbox.coach.compare import compare_to_reference
from boxbox.coach.corners import analyze_lap
from boxbox.coach.laps import Lap, LapRecorder, Sample
from boxbox.storage.db import Database
from boxbox.telemetry.session import parse_session
from boxbox.tracks.model import save_track
from tests.builders import lap_packet, session_packet, status_packet, telemetry_packet
from tests.synthetic import LENGTH, gear_at, pedals_at, speed_at, track
from tests.test_laps import synthetic_samples


def slower(samples: list[Sample], corner_apex: float, extra_kmh: int = -20, shift_ms: int = 400) -> list[Sample]:
    """Wolniej w zakręcie: niższa v_min wokół apeksu i dłuższy czas od tego miejsca."""
    out = []
    for s in samples:
        v = s.speed_kmh + extra_kmh if abs(s.distance_m - corner_apex) < 60 else s.speed_kmh
        t = s.lap_time_ms + (shift_ms if s.distance_m > corner_apex else 0)
        out.append(Sample(s.distance_m, t, max(v, 1), s.throttle, s.brake, s.gear, s.steer))
    return out


def test_save_and_query_laps(tmp_path: Path) -> None:
    db = Database(tmp_path / "t.sqlite")
    session = parse_session(session_packet())
    sid = db.save_session(session, source="recordings/x.bin")
    assert db.save_session(session, source="recordings/x.bin") == sid  # ta sama sesja = ten sam wiersz
    t = track()
    fast = Lap(2, synthetic_samples(), 90_000)
    slow = Lap(3, slower(synthetic_samples(), 600.0), 90_400)
    invalid = Lap(4, synthetic_samples(), 85_000, invalid=True)
    partial = Lap(5, synthetic_samples(stop=3000.0), 80_000)
    for lap in (fast, slow, invalid, partial):
        db.save_lap(sid, lap, analyze_lap(lap, t), t.length_m, gearbox=3, traction_control=1, abs_on=True)
    stored = db.laps_for_track(3)
    assert [(s.number, s.valid, s.complete) for s in stored] == [(2, True, True), (3, True, True), (4, False, True), (5, True, False)]
    best = db.best_lap(3)
    assert best is not None and best.number == 2 and best.lap_time_ms == 90_000
    ref = db.reference(3)
    assert ref is not None and ref.lap.number == 2
    assert [m.corner for m in ref.corners] == [1, 2, 3, 4]
    assert ref.corners[0].min_speed_kmh == pytest.approx(90, abs=2)
    assert len(ref.samples) == len(fast.samples)
    assert ref.samples[10] == fast.samples[10]
    assert db.best_lap(99) is None and db.reference(99) is None


def test_session_uid_above_int64_is_stored(tmp_path: Path) -> None:
    from boxbox.telemetry.header import PacketHeader, PacketId, pack_header
    raw = bytearray(session_packet())
    raw[:29] = pack_header(PacketHeader(2025, 25, 1, 0, 1, int(PacketId.SESSION), 2**64 - 1, 0.0, 0, 0, 3, 255))
    session = parse_session(bytes(raw))
    db = Database(tmp_path / "t.sqlite")
    sid = db.save_session(session, source="x")
    assert db.save_session(session, source="x") == sid
    assert db.save_session(session, source="y") != sid


def test_lap_without_time_is_not_reference(tmp_path: Path) -> None:
    db = Database(tmp_path / "t.sqlite")
    sid = db.save_session(None, source="x")
    t = track()
    db.save_lap(sid, Lap(1, synthetic_samples(), None), analyze_lap(Lap(1, synthetic_samples(), None), t), t.length_m, track_id=3)
    assert db.best_lap(3) is None
    assert len(db.laps_for_track(3)) == 1


def test_compare_to_reference() -> None:
    t = track()
    ref = analyze_lap(Lap(1, synthetic_samples(), 90_000), t)
    cur = analyze_lap(Lap(2, slower(synthetic_samples(), 600.0), 90_400), t)
    deltas = compare_to_reference(cur, ref)
    assert [d.corner for d in deltas] == [1, 2, 3, 4]
    d1 = deltas[0]
    assert d1.min_speed_delta_kmh == pytest.approx(-20, abs=2)
    assert d1.time_delta_ms == pytest.approx(400, abs=60)
    assert d1.brake_point_delta_m == pytest.approx(0, abs=4)
    assert d1.full_throttle_delta_m == pytest.approx(0, abs=4)
    assert deltas[1].min_speed_delta_kmh == 0 and deltas[1].time_delta_ms == pytest.approx(0, abs=60)


def test_compare_with_missing_corner_and_none_fields() -> None:
    from boxbox.coach.corners import CornerMetrics, LapAnalysis
    ref = LapAnalysis(1, 1000, (CornerMetrics(1, 90, 600, 3, 200, 200, 3000, 500.0, 650.0), CornerMetrics(2, 100, 1500, 4, 200, 200, 3000, None, 1550.0)))
    cur = LapAnalysis(2, 1100, (CornerMetrics(1, 85, 601, 3, 200, 200, 3300, None, 660.0),))
    deltas = compare_to_reference(cur, ref)
    assert len(deltas) == 1
    assert deltas[0].brake_point_delta_m is None and deltas[0].full_throttle_delta_m == pytest.approx(10)


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def make_recording(path: Path, laps: dict[int, float]) -> None:
    """Pełne okrążenia; wartość to przesunięcie czasu (ms) za zakrętem 1 - symuluje wolniejsze okrążenie."""
    from boxbox.telemetry.recording import RecordingWriter
    with RecordingWriter(path) as w:
        w.write(0.0, session_packet())
        w.write(0.0, status_packet())
        t = 0.0
        for lap_num, shift in laps.items():
            d = 0.0
            while d < LENGTH:
                throttle, brake = pedals_at(d)
                lap_time = int(d / LENGTH * 90_000 + (shift if d > 600 else 0))
                w.write(t, lap_packet(lap_distance=d, lap_num=lap_num, lap_invalid=False, current_lap_time_ms=lap_time))
                w.write(t, telemetry_packet(speed=int(speed_at(d)), throttle=throttle, brake=brake, gear=gear_at(d)))
                d += 2.0
                t += 1 / 60
        w.write(t, lap_packet(lap_distance=1.0, lap_num=max(laps) + 1, lap_invalid=False))
        w.write(t, telemetry_packet(speed=280))


def test_app_replay_saves_laps_and_prints_reference_table(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    rec = tmp_path / "r.bin"
    make_recording(rec, {1: 0.0, 2: 500.0})
    track_file = tmp_path / "3.json"
    save_track(track(), track_file)
    db_file = tmp_path / "boxbox.sqlite"
    assert app_main(["--replay", str(rec), "--speed", "0", "--track", str(track_file), "--db", str(db_file)]) == 0
    out = capsys.readouterr().out
    assert "Okrążenie 1" in out and "Okrążenie 2" in out
    assert "referencja: okrążenie 1" in out
    assert "Δczas" in out  # kolumny różnic
    db = Database(db_file)
    assert [s.number for s in db.laps_for_track(3)] == [1, 2]
    assert db.best_lap(3).number == 1
    # drugie odtworzenie tego samego nagrania nie dubluje okrążeń
    assert app_main(["--replay", str(rec), "--speed", "0", "--track", str(track_file), "--db", str(db_file)]) == 0
    assert [s.number for s in Database(db_file).laps_for_track(3)] == [1, 2]


def test_app_replay_without_track_file_still_works(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    rec = tmp_path / "r.bin"
    make_recording(rec, {1: 0.0})
    assert app_main(["--replay", str(rec), "--speed", "0", "--track", str(tmp_path / "none.json"), "--db", str(tmp_path / "d.sqlite")]) == 0
    out = capsys.readouterr().out
    assert "brak pliku toru" in out and "Odebrano" in out
