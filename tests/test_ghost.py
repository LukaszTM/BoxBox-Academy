from pathlib import Path

import pytest

from boxbox.coach.ghost import extract_ghost_laps
from boxbox.telemetry import participants as pp
from boxbox.telemetry.header import NUM_CARS
from boxbox.telemetry.recording import RecordingWriter
from boxbox.tracks.detect import main as detect_main
from tests.builders import FORMATS, RIVAL, lap_packet, participants_packet, session_packet, telemetry_packet
from tests.synthetic import LENGTH, gear_at, pedals_at, speed_at


def test_participants_sizes() -> None:
    assert pp.PACKET_SIZE == {2025: 1284, 2026: 1470}


@pytest.mark.parametrize("fmt", FORMATS)
def test_parse_participants(fmt: int) -> None:
    packet = pp.parse_participants(participants_packet(fmt))
    assert len(packet.cars) == NUM_CARS[fmt] and packet.num_active_cars == 2
    assert packet.player.name == "Gracz" and packet.player.ai_controlled is False
    assert packet.cars[RIVAL].name == "Jarno Opmeer"
    assert packet.cars[0].name == "" and packet.cars[0].ai_controlled is True
    assert packet.cars[RIVAL].race_number == 44 and packet.cars[RIVAL].colours == ((255, 0, 0), (0, 0, 255))


def ghost_recording(path: Path, laps: int = 2, wait_samples: int = 30) -> None:
    """Duch jedzie syntetyczny profil ze śmieciową prędkością w polu; po okrążeniu czeka na linii."""
    with RecordingWriter(path) as w:
        w.write(0.0, session_packet())
        w.write(0.0, participants_packet())
        t = 0.0
        for _ in range(laps):
            d, lap_time = 0.0, 0
            while d < LENGTH:
                v = speed_at(d)
                throttle, brake = pedals_at(d)
                w.write(t, lap_packet(lap_distance=1000.0, lap_num=1, rival=(d, lap_time, 86_764)))
                w.write(t, telemetry_packet(speed=200, rival=(486, throttle, brake, gear_at(d))))  # pole v = śmieci
                step = v / 3.6 / 60  # m na klatkę przy 60 Hz
                d += step
                lap_time += 17
                t += 1 / 60
            for _ in range(wait_samples):  # duch stoi na mecie, czas rośnie
                w.write(t, lap_packet(lap_distance=1000.0, lap_num=1, rival=(LENGTH - 0.5, lap_time, 86_764)))
                w.write(t, telemetry_packet(rival=(0, 0.0, 0.0, 0)))
                lap_time += 17
                t += 1 / 60


def test_extract_ghost_laps(tmp_path: Path) -> None:
    rec = tmp_path / "g.bin"
    ghost_recording(rec)
    ghost = extract_ghost_laps(rec, "rival")
    assert ghost is not None
    assert (ghost.car_index, ghost.name) == (RIVAL, "Jarno Opmeer")
    assert [lap.number for lap in ghost.laps] == [1, 2]
    best = ghost.best_lap(LENGTH)
    assert best is not None and best.lap_time_ms == 86_764
    assert best.is_complete(LENGTH)
    # prędkość policzona z dystansu, nie z pola (486): na prostej ~300, w apeksie Z3 ~70
    straight = [s.speed_kmh for s in best.samples if 2000 < s.distance_m < 3000]
    apex = min(s.speed_kmh for s in best.samples if 3150 < s.distance_m < 3250)
    assert 290 <= max(straight) <= 310 and 65 <= apex <= 80
    assert all(s.speed_kmh < 320 for s in best.samples)
    # próbki z oczekiwania na mecie odrzucone (dystans musi rosnąć)
    assert all(b.distance_m > a.distance_m for a, b in zip(best.samples, best.samples[1:]))


def test_no_ghost_returns_none(tmp_path: Path) -> None:
    rec = tmp_path / "n.bin"
    with RecordingWriter(rec) as w:
        w.write(0.0, lap_packet())
        w.write(0.0, telemetry_packet())
    assert extract_ghost_laps(rec, "rival") is None
    assert extract_ghost_laps(rec, "pb") is None


def test_detect_from_ghost(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    rec = tmp_path / "g.bin"
    ghost_recording(rec, laps=1)
    out = tmp_path / "3.json"
    assert detect_main([str(rec), "--car", "rival", "--out", str(out), "--track-length", str(LENGTH)]) == 0
    text = capsys.readouterr().out
    assert "duch: Jarno Opmeer" in text and "4 zakręty" in text


REAL = Path(__file__).parent.parent / "recordings" / "bahrajn-tt_2026-10-26_122816.bin.xz"


@pytest.mark.skipif(not REAL.exists(), reason="brak nagrania")
def test_real_recording_rival_ghost() -> None:
    ghost = extract_ghost_laps(REAL, "rival")
    assert ghost is not None and ghost.car_index == 5
    best = ghost.best_lap(5408.0)
    assert best is not None and best.lap_time_ms == 86_764  # Jarno Opmeer 1:26,764
    assert max(s.speed_kmh for s in best.samples) <= 345
    assert sum(1 for s in best.samples if s.brake > 0.1) > 300
