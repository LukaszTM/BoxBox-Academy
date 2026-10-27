"""Model toru: lista zakrętów z dystansem wejścia, apeksu i wyjścia od linii mety.

Plik JSON:
{
  "track_id": 3, "name": "Bahrajn", "length_m": 5412.0, "source": "recordings/...bin",
  "corners": [{"number": 1, "name": "Z1", "entry_m": 520.0, "apex_m": 600.0, "exit_m": 690.0}, ...]
}
Zakręt przez linię mety ma exit_m < entry_m.
"""
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).parent / "data"


@dataclass(frozen=True)
class Corner:
    number: int
    entry_m: float  # początek hamowania / wejście w zakręt
    apex_m: float  # punkt najmniejszej prędkości
    exit_m: float  # powrót do pełnego gazu / wyjście
    name: str = ""

    def length_m(self, track_length_m: float) -> float:
        if self.exit_m >= self.entry_m:
            return self.exit_m - self.entry_m
        return track_length_m - self.entry_m + self.exit_m  # przez linię mety

    def contains(self, lap_distance_m: float, track_length_m: float) -> bool:
        if self.exit_m >= self.entry_m:
            return self.entry_m <= lap_distance_m <= self.exit_m
        return lap_distance_m >= self.entry_m or lap_distance_m <= self.exit_m


@dataclass(frozen=True)
class Track:
    track_id: int
    name: str
    length_m: float
    corners: tuple[Corner, ...]
    source: str = ""  # nagranie, z którego wyznaczono zakręty


def corner_at(track: Track, lap_distance_m: float) -> Corner | None:
    """Zakręt, w którym jest auto, albo None na prostej (lub przed linią mety: dystans ujemny)."""
    if lap_distance_m < 0:
        return None
    for corner in track.corners:
        if corner.contains(lap_distance_m, track.length_m):
            return corner
    return None


def _validate(track: Track) -> None:
    length = track.length_m
    if length <= 0:
        raise ValueError("długość toru musi być dodatnia")
    for i, c in enumerate(track.corners):
        if c.number != i + 1:
            raise ValueError(f"zakręty muszą mieć kolejne numery od 1, a zakręt {i + 1} ma numer {c.number}")
        for value, label in ((c.entry_m, "entry_m"), (c.apex_m, "apex_m"), (c.exit_m, "exit_m")):
            if not 0 <= value <= length:
                raise ValueError(f"zakręt {c.number}: {label}={value} poza długością toru 0-{length}")
        wraps = c.exit_m < c.entry_m
        apex_ok = (c.entry_m <= c.apex_m <= c.exit_m) if not wraps else (c.apex_m >= c.entry_m or c.apex_m <= c.exit_m)
        if not apex_ok:
            raise ValueError(f"zakręt {c.number}: apex {c.apex_m} poza odcinkiem {c.entry_m}-{c.exit_m}")
        if wraps and i != len(track.corners) - 1:
            raise ValueError(f"zakręt {c.number}: tylko ostatni zakręt może przechodzić przez linię mety")
    for prev, nxt in zip(track.corners, track.corners[1:]):
        if nxt.entry_m < prev.entry_m:
            raise ValueError(f"zakręty muszą być w kolejności dystansu: {prev.number} przed {nxt.number}")
        if nxt.entry_m <= prev.exit_m and prev.exit_m >= prev.entry_m:
            raise ValueError(f"zakręty {prev.number} i {nxt.number} nachodzą na siebie")
    if track.corners and track.corners[-1].exit_m < track.corners[-1].entry_m:
        if track.corners[0].entry_m <= track.corners[-1].exit_m:
            raise ValueError(f"zakręty {track.corners[-1].number} i 1 nachodzą na siebie przez linię mety")


def track_from_dict(data: dict[str, Any]) -> Track:
    corners = tuple(
        Corner(
            number=int(c["number"]), entry_m=float(c["entry_m"]), apex_m=float(c["apex_m"]),
            exit_m=float(c["exit_m"]), name=str(c.get("name", "")),
        )
        for c in data["corners"]
    )
    track = Track(
        track_id=int(data["track_id"]), name=str(data["name"]), length_m=float(data["length_m"]),
        corners=corners, source=str(data.get("source", "")),
    )
    _validate(track)
    return track


def track_to_dict(track: Track) -> dict[str, Any]:
    corners = []
    for c in track.corners:
        d = asdict(c)
        if not c.name:
            del d["name"]
        corners.append(d)
    return {
        "track_id": track.track_id, "name": track.name, "length_m": track.length_m,
        "source": track.source, "corners": corners,
    }


def load_track(path: Path) -> Track:
    if not path.exists():
        raise FileNotFoundError(f"brak pliku toru: {path}")
    return track_from_dict(json.loads(path.read_text(encoding="utf-8")))


def save_track(track: Track, path: Path) -> None:
    _validate(track)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(track_to_dict(track), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def track_path(track_id: int, game_id: str = "f1_25") -> Path:
    """Plik toru: F1 25 leży wprost w data/, inne gry w podfolderze o id gry (bez zmian w kodzie trenera)."""
    if game_id == "f1_25":
        return DATA_DIR / f"{track_id}.json"
    return DATA_DIR / game_id / f"{track_id}.json"


def load_track_by_id(track_id: int) -> Track:
    return load_track(track_path(track_id))
