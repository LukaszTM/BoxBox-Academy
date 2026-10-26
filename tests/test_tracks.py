import json
from pathlib import Path

import pytest

from boxbox.tracks.model import Corner, Track, corner_at, load_track, save_track, track_from_dict


def sample_track() -> Track:
    return Track(
        track_id=3, name="Bahrajn", length_m=5412.0, source="recordings/test.bin",
        corners=(
            Corner(1, 520.0, 600.0, 690.0, "Z1"),
            Corner(2, 700.0, 740.0, 800.0),
            Corner(3, 5300.0, 5380.0, 60.0),  # przez linię mety
        ),
    )


def test_roundtrip_json(tmp_path: Path) -> None:
    path = tmp_path / "3.json"
    save_track(sample_track(), path)
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["track_id"] == 3 and data["corners"][0]["entry_m"] == 520.0
    assert data["corners"][0]["name"] == "Z1" and "name" not in data["corners"][1]
    assert load_track(path) == sample_track()


def test_corner_at() -> None:
    track = sample_track()
    assert corner_at(track, 100.0) is None  # prosta
    assert corner_at(track, 520.0).number == 1
    assert corner_at(track, 690.0).number == 1
    assert corner_at(track, 695.0) is None
    assert corner_at(track, 750.0).number == 2
    assert corner_at(track, 5350.0).number == 3  # przed metą
    assert corner_at(track, 30.0).number == 3  # tuż za metą, ten sam zakręt
    assert corner_at(track, -5.0) is None  # przed pierwszym przejazdem linii


def test_corner_length_handles_wrap() -> None:
    track = sample_track()
    assert track.corners[0].length_m(track.length_m) == pytest.approx(170.0)
    assert track.corners[2].length_m(track.length_m) == pytest.approx(172.0)


@pytest.mark.parametrize(
    "corners,message",
    [
        ([{"number": 2, "entry_m": 10, "apex_m": 20, "exit_m": 30}], "numer"),
        ([{"number": 1, "entry_m": 10, "apex_m": 20, "exit_m": 30},
          {"number": 2, "entry_m": 25, "apex_m": 40, "exit_m": 50}], "nachodz"),
        ([{"number": 1, "entry_m": 10, "apex_m": 50, "exit_m": 30}], "apex"),
        ([{"number": 1, "entry_m": 10, "apex_m": 20, "exit_m": 6000}], "długo"),
        ([{"number": 1, "entry_m": 200, "apex_m": 220, "exit_m": 240},
          {"number": 2, "entry_m": 10, "apex_m": 20, "exit_m": 30}], "kolejno"),
    ],
)
def test_invalid_tracks_rejected(corners: list[dict], message: str) -> None:
    with pytest.raises(ValueError, match=message):
        track_from_dict({"track_id": 3, "name": "x", "length_m": 5412, "corners": corners})


def test_missing_file_has_clear_error(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="brak pliku toru"):
        load_track(tmp_path / "99.json")
