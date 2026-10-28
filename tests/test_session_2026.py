"""Cała ścieżka na nagraniu w formacie 2026 (Season Pack): sesja, trener, próbki DRS/opon/baterii, prowadzenie, baza, profil."""
from pathlib import Path

import pytest

from boxbox.coach.analyze import report_laps
from boxbox.coach.skills import profile_for_track
from boxbox.session import CoachSession, SessionConfig
from boxbox.storage.db import Database
from tests.conftest import RECORDINGS

PAKIET_2026 = RECORDINGS / "pakiet2026-monza_2026-10-26_185457.bin.xz"


def test_2026_recording_runs_through_session_and_database(tmp_path: Path) -> None:
    if not PAKIET_2026.exists():
        pytest.skip("brak nagrania 2026")
    notes: list[str] = []
    cfg = SessionConfig(replay=PAKIET_2026, speed=0, db=tmp_path / "b.sqlite", no_voice=True, shape_dir=tmp_path / "shape",
                        fit_dir=tmp_path / "fit", auto_track_dir=tmp_path / "tracks")
    s = CoachSession(cfg, on_note=notes.append)
    s.start()
    s.loop()
    r = s.finish()
    assert set(r.state.formats) == {2026} and r.state.session is not None and r.state.session.track_name == "Monza"
    assert r.coach_started and s.track_source == "pakiet" and not notes
    laps = [lap for lap in r.recorder.laps if lap.samples]
    assert len(laps) == 3 and all(len(lap.drs) > 1000 and len(lap.tyres) > 150 and len(lap.ers) > 1000 for lap in laps)
    assert all(lap.drs_assist is True and lap.tyres[0].wear_percent is not None for lap in laps)  # Car Damage 2026 parsowany
    texts = [t for _, t in s.messages]
    assert any(t.startswith("Pierwsze okrążenie zapisane") for t in texts) and any(t == "Nowe najlepsze okrążenie." for t in texts)
    assert any(t.endswith("Prowadzę.") for t in texts) and "Mocny hamulec." in texts  # po obrocie w Rettifilo: prowadzenie T1-T2
    assert s.coach is not None and s.coach.ers_plan is not None and s.coach.ers_plan.longest.from_corner == "T11"
    assert r.summary is not None and r.summary.good
    # zapis do bazy jak w aplikacji (raport po sesji), potem profil (3 ważne okrążenia = za mało na wynik, samodzielność liczona)
    assert "Monza" in report_laps(r.recorder, None, cfg.db, "test", "best", cfg.replay)
    db = Database(cfg.db)
    try:
        assert len(db.laps_for_track(11)) == 3
        p = profile_for_track(db, 11, "Monza")
        assert p.note.startswith("za mało danych") and p.by_key("independence").score is not None
    finally:
        db.close()
