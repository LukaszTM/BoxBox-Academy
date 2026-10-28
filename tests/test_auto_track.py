"""Tor bez pliku: zakręty wyznaczone z pierwszego pełnego okrążenia sesji, zapis do data/tracks, trener startuje."""
from pathlib import Path

import pytest

from boxbox.coach.laps import Lap
from boxbox.session import CoachSession, SessionConfig
from boxbox.tracks import model
from boxbox.tracks.auto import lap_samples, track_from_lap
from boxbox.tracks.detect import detect_corners
from boxbox.tracks.model import find_track_path, load_track, user_track_path
from boxbox.ui.overlay_model import guide_from_track
from tests.conftest import RECORDINGS, RecordedSession

MONZA = RECORDINGS / "monza-trening_2026-10-26_153411.bin.xz"


def _run(tmp_path: Path, auto_dir: Path | None, track: Path | None = None) -> tuple[CoachSession, list[str]]:
    notes: list[str] = []
    cfg = SessionConfig(replay=MONZA, speed=0, db=None, no_voice=True, track=track, auto_track_dir=auto_dir)
    session = CoachSession(cfg, on_note=notes.append)
    session.start()
    session.loop()
    session.finish()
    return session, notes


def test_track_from_lap_matches_detect_and_names_corners(monza: RecordedSession) -> None:
    lap = monza.lap(3)
    track = track_from_lap(lap, 11, "Monza", monza.track.length_m, source="test")
    assert track is not None and track.track_id == 11 and track.length_m == monza.track.length_m
    expected = detect_corners(lap_samples(lap), monza.track.length_m)  # ten sam algorytm co python -m boxbox.tracks.detect
    assert [(c.entry_m, c.apex_m, c.exit_m) for c in track.corners] == [(c.entry_m, c.apex_m, c.exit_m) for c in expected]
    assert [c.name for c in track.corners] == [f"T{i}" for i in range(1, len(track.corners) + 1)]
    assert "test" in track.source and "automatycznie" in track.source
    # okrążenie niepełne albo z pit lane nie nadaje się
    assert track_from_lap(Lap(9, lap.samples[: len(lap.samples) // 2]), 11, "Monza", monza.track.length_m) is None
    pitted = Lap(9, list(lap.samples), pitted=True)
    assert track_from_lap(pitted, 11, "Monza", monza.track.length_m) is None
    guide = guide_from_track(track)
    assert [c.name for c in guide.corners] == [c.name for c in track.corners] and guide.accuracy == "z pliku toru"


def test_session_without_track_file_detects_corners_and_starts_coach(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(model, "DATA_DIR", tmp_path / "pakiet")  # jakby Monza nie miała pliku w pakiecie
    auto_dir = tmp_path / "tracks"
    session, notes = _run(tmp_path, auto_dir)
    assert session.coach is not None and session.track_source == "sesja" and not session.coach_failed
    assert session.shared.error is None
    assert any(n.startswith("Brak pliku toru") and "pierwszym pełnym okrążeniu" in n for n in notes)
    done = [n for n in notes if n.startswith("Zakręty toru Monza wyznaczone z okrążenia")]
    assert len(done) == 1 and str(user_track_path(11, user_dir=auto_dir)) in done[0]
    assert done[0] in [t for _, t in session.messages]  # okno i nakładka widzą to w liście komunikatów
    saved = load_track(user_track_path(11, user_dir=auto_dir))
    assert saved.track_id == 11 and 6 <= len(saved.corners) <= 10 and saved.corners[0].name == "T1"
    # trener zaczął od okrążenia, z którego wyznaczono zakręty: ma referencję i podsumowania z kolejnych
    texts = [t for _, t in session.messages]
    assert any(t.startswith("Pierwsze okrążenie zapisane") for t in texts)
    assert session.coach.reference is not None and session.result is not None and session.result.summary is not None
    # następna sesja wczytuje plik z data/tracks od razu (pakiet nadal pusty)
    assert find_track_path(11, user_dir=auto_dir) == user_track_path(11, user_dir=auto_dir)
    session2, notes2 = _run(tmp_path, auto_dir)
    assert session2.track_source == "automatyczny" and not any(n.startswith("Brak pliku toru") for n in notes2)
    # plik wbudowany ma pierwszeństwo, gdy się pojawi
    monkeypatch.setattr(model, "DATA_DIR", Path(__file__).parent.parent / "boxbox" / "tracks" / "data")
    assert find_track_path(11, user_dir=auto_dir).parent.name == "data"


def test_explicit_missing_track_file_is_filled_from_first_lap(tmp_path: Path) -> None:
    out = tmp_path / "wlasny" / "11.json"
    session, notes = _run(tmp_path, None, track=out)
    assert out.exists() and session.coach is not None and session.track_source == "sesja"
    assert load_track(out).name == "Monza"


def test_no_auto_dir_keeps_track_in_memory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(model, "DATA_DIR", tmp_path / "pakiet")
    session, notes = _run(tmp_path, None)
    assert session.coach is not None and not (tmp_path / "tracks").exists()
    assert any("Trener aktywny" in n and "plik" not in n for n in notes)
