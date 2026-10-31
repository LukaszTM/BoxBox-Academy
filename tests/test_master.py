"""Trening względem najlepszych: duch z rankingu na żywo, strata do mistrza, zapis w bazie, sesja."""
from pathlib import Path

import pytest

from boxbox.coach.corners import CornerMetrics, LapAnalysis, analyze_lap
from boxbox.coach.ghost import GhostRecorder, extract_ghost_laps
from boxbox.coach.laps import Lap
from boxbox.coach.master import format_gap, master_gap, master_utterance
from boxbox.storage.db import Database
from boxbox.telemetry.replay import replay
from boxbox.telemetry.state import TelemetryState
from boxbox.voice.phrases import catalog, track_corner_names
from tests.test_ghost import LENGTH, ghost_recording
from tests.test_laps import synthetic_samples

REAL = Path(__file__).parent.parent / "recordings" / "bahrajn-tt_2026-10-26_122816.bin.xz"


def cm(corner: int, brake: float, time_ms: int, vmin: int = 120, full: float | None = 700.0) -> CornerMetrics:
    return CornerMetrics(corner, vmin, 650.0, 3, 250, 200, time_ms, brake, full, brake + 60, 0.6, 0.9, brake - 40)


def test_master_gap_picks_worst_corner_and_hint() -> None:
    own = LapAnalysis(3, 95_000, (cm(1, 500, 6500), cm(2, 1500, 4300, vmin=100), cm(3, 3000, 5200, full=3400.0)))
    master = LapAnalysis(0, 88_000, (cm(1, 540, 6000), cm(2, 1500, 4000, vmin=120), cm(3, 3000, 4500, full=3350.0)))
    gap = master_gap(own, master)
    assert gap is not None and gap.total_ms == 7_000 and gap.corner == 3 and gap.corner_loss_ms == 700
    assert gap.hint == "throttle_earlier" and gap.hint_m == 50  # Z3: ten sam punkt hamowania, gaz 50 m później niż mistrz
    ids, text = master_utterance(gap, "T3")
    assert ids == ["misc_master_gap", "misc_loss_8", "misc_master_in", "corner_t3", "misc_master_throttle_earlier", "num_50", "misc_master_target_half"]
    assert text.startswith("Do najlepszych na świecie tracisz około osiem sekund. Najwięcej w Zakręt trzeci. Najlepsi dodają pełny gaz wcześniej, o jakieś pięćdziesiąt metrów.")
    assert text.endswith("(20 m)")  # krok na dziś: połowa, maks. 20 m
    brake = master_gap(LapAnalysis(3, 90_000, (cm(1, 500, 6500),)), LapAnalysis(0, 88_000, (cm(1, 540, 6000),)))
    assert brake is not None and brake.hint == "brake_later" and brake.hint_m == 40 and master_utterance(brake, "T1")[0][4:6] == ["misc_master_brake_later", "num_40"]
    apex = master_gap(LapAnalysis(3, 90_000, (cm(1, 500, 6500, vmin=100),)), LapAnalysis(0, 88_000, (cm(1, 505, 6000, vmin=120),)))
    assert apex is not None and apex.hint == "apex" and master_utterance(apex, "T1")[0][-1] == "misc_master_apex"
    assert master_gap(LapAnalysis(3, 88_100, (cm(1, 500, 6100),)), LapAnalysis(0, 88_000, (cm(1, 500, 6000),))) is None  # poniżej 0,3 s: cicho
    assert master_gap(LapAnalysis(3, None, (cm(1, 500, 6100),)), master) is None
    entries = catalog(track_corner_names())
    assert all(i in entries for i in ids)
    assert format_gap(7_000) == "−7,0 s" and format_gap(None) == "—"


def test_ghost_recorder_live_matches_extract(tmp_path: Path) -> None:
    rec = tmp_path / "g.bin"
    ghost_recording(rec)
    state = TelemetryState()
    ghost = GhostRecorder("rival")
    closed: list[Lap] = []

    def handle(data: bytes) -> None:
        state.feed(data)
        done = ghost.feed(state)  # po każdym pakiecie: próbka tylko gdy dystans wzrósł
        if done is not None:
            closed.append(done)

    replay(rec, handle, speed=0)
    assert ghost.car_index == 5 and [lap.number for lap in closed] == [1]  # drugie okrążenie trwa (bez powrotu na metę)
    best = ghost.best_lap(LENGTH)
    assert best is not None and best.lap_time_ms == 86_764 and best.is_complete(LENGTH)
    offline = extract_ghost_laps(rec, "rival")
    assert offline is not None and [lap.number for lap in offline.laps] == [1, 2] and offline.best_lap(LENGTH).lap_time_ms == best.lap_time_ms
    assert ghost.name(state) == "Jarno Opmeer"


def test_master_lap_round_trip_in_database(tmp_path: Path) -> None:
    db = Database(tmp_path / "m.sqlite")
    assert db.master(3) is None
    slow = Lap(1, synthetic_samples(), 92_000)
    fast = Lap(2, synthetic_samples(), 88_000)
    assert db.save_master(3, slow) and db.save_master(3, fast) and not db.save_master(3, slow)  # tylko szybsze nadpisuje
    master = db.master(3)
    assert master is not None and master.lap_time_ms == 88_000 and len(master.samples) == len(fast.samples) and master.samples[7] == fast.samples[7]
    assert not db.save_master(3, Lap(3, [], 80_000))  # bez próbek nie zapisujemy
    db.close()


@pytest.mark.skipif(not REAL.exists(), reason="brak nagrania")
def test_session_learns_master_from_time_trial_ghost(tmp_path: Path) -> None:
    """Bahrajn TT z duchem rywala: trener mówi o stracie do najlepszych już w tej sesji, a druga sesja startuje z mistrzem z bazy."""
    from boxbox.session import CoachSession, SessionConfig

    said: list[str] = []
    cfg = SessionConfig(replay=REAL, speed=0, db=tmp_path / "s.sqlite", no_voice=True)
    s = CoachSession(cfg, on_message=lambda ids, text: said.append(text))
    s.start()
    s.loop()
    s.finish()
    assert s.master_time_ms == 86_764 and s.coach is not None and s.coach.master is not None
    assert any(t.startswith("Mam okrążenie najlepszych") for t in said)
    gaps = [t for t in said if t.startswith("Do najlepszych na świecie tracisz")]
    assert gaps and all("Najwięcej w Zakręt" in t or "Najwięcej w Zakręty" in t for t in gaps)
    db = Database(cfg.db)
    master = db.master(3)
    db.close()
    assert master is not None and master.lap_time_ms == 86_764
    said2: list[str] = []
    s2 = CoachSession(cfg, on_message=lambda ids, text: said2.append(text))
    s2.start()
    s2.loop()
    s2.finish()
    assert s2.master_time_ms == 86_764 and not any(t.startswith("Mam okrążenie najlepszych") for t in said2)  # z bazy: bez ponownego wstępu
    assert any(t.startswith("Do najlepszych na świecie tracisz") for t in said2)
    assert s2.coach is not None and s2.coach.last_master_gap is not None and s2.coach.last_master_gap.total_ms > 0
