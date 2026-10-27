import json
import math
import zipfile
from pathlib import Path

import pytest

from boxbox.reporter import ShapeCollector, build_report, main as reporter_main, make_shape
from boxbox.telemetry.motion import PACKET_SIZE, parse_motion
from boxbox.telemetry.recording import SKIPPED_FOR_SHAPE, RecordingWriter, is_needed
from boxbox.telemetry.state import TelemetryState
from boxbox.tracks.shape import build_shape, load_shape, save_shape, to_svg
from tests.builders import lap_packet, motion_packet, session_packet, telemetry_packet

LENGTH = 5412.0  # Bahrajn z session_packet()
RADIUS = LENGTH / (2 * math.pi)


def pos(distance: float) -> tuple[float, float]:
    a = 2 * math.pi * distance / LENGTH
    return 100 + RADIUS * math.cos(a), -50 + RADIUS * math.sin(a)


def circle_packets(laps: tuple[int, ...] = (1, 2), step: float = 7.0, fmt: int = 2025) -> list[bytes]:
    out = [session_packet(fmt)]
    for lap in laps:
        d = 0.0
        while d < LENGTH:
            x, z = pos(d)
            out += [lap_packet(fmt, lap_distance=d, lap_num=lap, lap_invalid=False), motion_packet(fmt, x, z), telemetry_packet(fmt)]
            d += step
    return out


def test_parse_motion_both_formats() -> None:
    for fmt in (2025, 2026):
        pkt = motion_packet(fmt, 12.5, -7.25, 0.5)
        assert len(pkt) == PACKET_SIZE[fmt]
        m = parse_motion(pkt)
        assert (m.player.x, m.player.z, round(m.player.yaw, 3)) == (12.5, -7.25, 0.5)
    state = TelemetryState()
    assert state.feed(motion_packet()) is not None and state.motion is not None
    assert not is_needed(motion_packet()) and is_needed(motion_packet(), SKIPPED_FOR_SHAPE)


def test_build_shape_resamples_circle_and_places_corners() -> None:
    from boxbox.tracks.model import Corner, Track

    samples = [(d, *pos(d)) for d in range(0, int(LENGTH), 3)]
    track = Track(3, "Bahrajn", LENGTH, (Corner(1, 500, 600, 700, "T1"), Corner(2, 2600, 2706, 2800, "T4")), "test")
    shape = build_shape(samples, 3, "Bahrajn", LENGTH, track)
    assert len(shape.points) == math.ceil(LENGTH / 10) and shape.points[0].distance_m == 0
    x, z = shape.position_at(2706.0)
    ex, ez = pos(2706.0)
    assert abs(x - ex) < 1.0 and abs(z - ez) < 1.0
    assert [c.name for c in shape.corners] == ["T1", "T4"] and abs(shape.corners[1].x - ex) < 1.0
    with pytest.raises(ValueError):
        build_shape(samples[: len(samples) // 2], 3, "Bahrajn", LENGTH)
    svg = to_svg(shape)
    assert svg.startswith("<svg") and "META" in svg and ">T4<" in svg


def test_shape_roundtrip(tmp_path: Path) -> None:
    samples = [(d, *pos(d)) for d in range(0, int(LENGTH), 5)]
    shape = build_shape(samples, 3, "Bahrajn", LENGTH)
    save_shape(shape, tmp_path / "3.json")
    again = load_shape(tmp_path / "3.json")
    assert len(again.points) == len(shape.points) and again.length_m == LENGTH
    doc = json.loads((tmp_path / "3.json").read_text(encoding="utf-8"))
    assert doc["points"][1][0] == 10.0


def test_collector_picks_complete_lap_and_report_zip(tmp_path: Path, monkeypatch) -> None:
    rec = tmp_path / "recordings" / "ksztalt.bin"
    rec.parent.mkdir()
    with RecordingWriter(rec) as w:
        for i, p in enumerate(circle_packets((1, 2))):
            w.write(i * 0.016, p)
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "boxbox.log").write_text("log", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    rc = reporter_main(["--replay", str(rec), "--out", str(tmp_path / "raporty"), "--data-dir", str(tmp_path / "data"),
                        "--shape-dir", str(tmp_path / "shape")])
    assert rc == 0 and (tmp_path / "shape" / "3.json").exists()
    zips = list((tmp_path / "raporty").glob("raport-bahrajn-*.zip"))
    assert len(zips) == 1
    names = zipfile.ZipFile(zips[0]).namelist()
    assert "shape/3.json" in names and "shape/3.svg" in names and "tracks/data/3.json" in names
    assert "data/boxbox.log" in names and "recordings/ksztalt.bin" in names
    assert any(n.endswith(".txt") for n in names)


def test_reporter_without_motion_reports_missing_shape(tmp_path: Path) -> None:
    rec = tmp_path / "bez.bin"
    with RecordingWriter(rec) as w:
        for i, p in enumerate(circle_packets((1,))):
            if not p[6] == 0:  # bez pakietów Motion
                w.write(i * 0.016, p)
    rc = reporter_main(["--replay", str(rec), "--out", str(tmp_path / "r"), "--data-dir", str(tmp_path / "data"),
                        "--shape-dir", str(tmp_path / "shape")])
    assert rc == 2
    assert list((tmp_path / "r").glob("*.zip"))  # raport i tak powstaje (nagranie + podsumowanie)
