"""Atlas obrysów: wczytanie 27 układów, dopasowanie do współrzędnych gry, mapa bez recordera, zapis po sesji."""
import json
import math
from pathlib import Path

from boxbox.gui.data import map_for
from boxbox.session import CoachSession, SessionConfig
from boxbox.tracks.atlas import (
    ATLAS_DIR,
    Atlas,
    AtlasFit,
    ShapeSampler,
    fit,
    load_atlas,
    outline_shape,
    to_shape,
)
from boxbox.tracks.model import Corner, Track
from boxbox.tracks.shape import load_shape, shape_path
from tests.builders import lap_packet, motion_packet, session_packet, telemetry_packet

LENGTH = 5412.0  # Bahrajn (track_id 3) z session_packet()


def test_atlas_files_cover_f1_25_and_match_lengths() -> None:
    files = sorted(int(p.stem) for p in ATLAS_DIR.glob("*.json"))
    assert len(files) == 27 and {3, 11, 13, 42 - 42} <= set(files)  # Bahrajn, Monza, Suzuka, Melbourne
    for tid in files:
        a = load_atlas(tid)
        assert a is not None and len(a.points) >= 40 and a.name
        # obwód obrysu w jednostkach atlasu razy skala ~ długość toru: skala ok. 1-5 m/jednostkę
        assert 0.8 < a.length_m / a.perimeter < 6.0, (tid, a.length_m / a.perimeter)
    assert (ATLAS_DIR / "LICENSE_MIT.txt").read_text(encoding="utf-8").startswith("MIT License")


def _synthetic_atlas() -> Atlas:
    """Obrys „łezki” (nie koło, żeby skala i meta były jednoznaczne) w układzie 0..1000."""
    pts = []
    for i in range(80):
        a = 2 * math.pi * i / 80
        r = 400 + 120 * math.cos(2 * a) + 60 * math.sin(3 * a)
        pts.append((500 + r * math.cos(a), 500 + r * math.sin(a)))
    return Atlas(3, "Test", LENGTH, tuple(pts))


def _game_samples(atlas: Atlas, scale: float, tx: float, tz: float, start: float, forward: bool, d_max: float, step: float = 7.0):
    out = []
    d = 0.0
    while d < d_max:
        f = (start + d / LENGTH) if forward else (start - d / LENGTH)
        x, y = atlas.at_fraction(f)
        out.append((d, scale * x + tx + 0.5 * math.sin(d), scale * y + tz + 0.5 * math.cos(d)))  # lekki szum
        d += step
    return out


def test_fit_recovers_scale_start_and_direction_from_partial_lap() -> None:
    atlas = _synthetic_atlas()
    for forward in (True, False):
        samples = _game_samples(atlas, 2.0, -800.0, 300.0, 0.37, forward, d_max=1800.0)
        f = fit(atlas, samples, LENGTH)
        assert f is not None and f.forward is forward
        assert abs(f.scale - 2.0) < 0.03 and abs(f.tx + 800) < 12 and abs(f.tz - 300) < 12
        assert min(abs(f.start_fraction - 0.37), 1 - abs(f.start_fraction - 0.37)) < 0.01
        assert f.error_m < 8


def test_fit_refuses_too_little_driving() -> None:
    atlas = _synthetic_atlas()
    assert fit(atlas, _game_samples(atlas, 2.0, 0.0, 0.0, 0.1, True, d_max=200.0), LENGTH) is None
    assert fit(atlas, [], LENGTH) is None


def test_fit_refuses_pure_straight() -> None:
    square = Atlas(3, "Kwadrat", 4000.0, ((0.0, 0.0), (1000.0, 0.0), (1000.0, 1000.0), (0.0, 1000.0)))
    samples = [(d, d, 0.0) for d in range(0, 700, 5)]  # tylko po jednym boku: metę można przesuwać dowolnie
    assert fit(square, samples, 4000.0) is None


def test_to_shape_maps_distance_to_game_coordinates_and_corners() -> None:
    atlas = _synthetic_atlas()
    f = AtlasFit(3, 2.0, -800.0, 300.0, 0.37, True)
    track = Track(3, "Bahrajn", LENGTH, (Corner(1, 500.0, 600.0, 700.0, "Z1"),))
    shape = to_shape(atlas, f, "Bahrajn", LENGTH, track)
    assert len(shape.points) == int(LENGTH // 10) + 1 and shape.points[0].distance_m == 0.0
    x, y = atlas.at_fraction(0.37 + 600.0 / LENGTH)
    c = shape.corners[0]
    assert c.name == "Z1" and abs(c.x - (2 * x - 800)) < 2.0 and abs(c.z - (2 * y + 300)) < 2.0
    fit_json = json.loads(json.dumps(f.__dict__))
    assert AtlasFit(**fit_json).start_fraction == 0.37


def test_map_for_falls_back_to_atlas_outline_then_fit(tmp_path: Path) -> None:
    m = map_for(11, tmp_path / "shape", fit_dir=tmp_path / "fit")  # Monza: tylko obrys z atlasu
    assert m is not None and m["source"] == "outline" and len(m["points"]) > 30 and m["corners"] == [] and m["start"] is None
    assert all(30 <= x <= 470 and 20 <= y <= 250 for x, y in m["points"])
    AtlasFit(11, 2.64, -1321.0, -1321.0, 0.963, True).save(tmp_path / "fit" / "11.json")
    m2 = map_for(11, tmp_path / "shape", fit_dir=tmp_path / "fit")
    assert m2["source"] == "atlas" and m2["start"] is not None and len(m2["corners"]) == 6  # zakręty z boxbox/tracks/data/11.json
    assert map_for(999, tmp_path / "shape", fit_dir=tmp_path / "fit") is None


def _circle_session_packets(d_max: float, laps: tuple[int, ...] = (1,)) -> list[bytes]:
    out = [session_packet(2025)]
    radius = LENGTH / (2 * math.pi)
    for lap in laps:
        d = 0.0
        while d < d_max:
            a = 2 * math.pi * d / LENGTH
            out += [lap_packet(2025, lap_distance=d, lap_num=lap, lap_invalid=False), motion_packet(2025, radius * math.cos(a), radius * math.sin(a)), telemetry_packet(2025)]
            d += 7.0
    return out


def test_session_saves_real_shape_after_complete_lap(tmp_path: Path, monkeypatch) -> None:
    rec = tmp_path / "n.bin"
    from boxbox.telemetry.recording import RecordingWriter
    with RecordingWriter(rec) as w:
        for i, pkt in enumerate(_circle_session_packets(LENGTH, laps=(1, 2))):
            w.write(i * 0.01, pkt)
    cfg = SessionConfig(replay=rec, speed=0, db=tmp_path / "s.sqlite", no_voice=True, shape_dir=tmp_path / "shape", fit_dir=tmp_path / "fit")
    s = CoachSession(cfg)
    s.start()
    s.loop()
    s.finish()
    path = shape_path(3, tmp_path / "shape")
    assert path.exists() and len(load_shape(path).points) == int(LENGTH // 10) + 1
    assert not (tmp_path / "fit").exists()  # pełne okrążenie: dopasowanie atlasu niepotrzebne


def test_sampler_dedups_frames_and_skips_pits() -> None:
    from boxbox.telemetry.state import TelemetryState
    st = TelemetryState()
    sampler = ShapeSampler()
    for pkt in (session_packet(2025), lap_packet(2025, lap_distance=100.0, lap_num=1), motion_packet(2025, 1.0, 2.0)):
        st.feed(pkt)
        sampler.feed(st)
    sampler.feed(st)  # ta sama klatka drugi raz
    assert sampler.laps == {1: [(100.0, 1.0, 2.0)]}
    st.feed(lap_packet(2025, lap_distance=120.0, lap_num=1, pit_status=1))
    sampler.feed(st)
    assert sampler.all_samples() == [(100.0, 1.0, 2.0)]
    assert sampler.complete_lap(LENGTH) is None
    assert outline_shape(_synthetic_atlas()).points[0].distance_m == 0.0
