"""Wspólne dane testowe: okrążenia z prawdziwych nagrań, wczytywane raz na sesję testów."""
from dataclasses import dataclass
from pathlib import Path

import pytest

from boxbox.coach.laps import Lap, LapRecorder
from boxbox.telemetry.replay import replay
from boxbox.tracks.model import Track, load_track_by_id

RECORDINGS = Path(__file__).parent.parent / "recordings"


@dataclass
class RecordedSession:
    recorder: LapRecorder
    track: Track

    def lap(self, number: int) -> Lap:
        for lap in self.recorder.laps + ([self.recorder.current] if self.recorder.current else []):
            if lap.number == number:
                return lap
        raise KeyError(number)


def _load(name: str, track_id: int) -> RecordedSession:
    path = RECORDINGS / name
    if not path.exists():
        pytest.skip(f"brak nagrania {name}")
    recorder = LapRecorder()
    replay(path, recorder.feed, speed=0)
    return RecordedSession(recorder, load_track_by_id(track_id))


@pytest.fixture(scope="session")
def monza() -> RecordedSession:
    return _load("monza-trening_2026-10-26_153411.bin.xz", 11)


@pytest.fixture(scope="session")
def bahrajn() -> RecordedSession:
    return _load("bahrajn-tt_2026-10-26_122816.bin.xz", 3)


@pytest.fixture(scope="session")
def suzuka_pomiar() -> RecordedSession:
    return _load("suzuka-bez-tc-pomiar_2026-10-26_183728.bin.xz", 13)


@pytest.fixture(scope="session")
def suzuka_bledy() -> RecordedSession:
    return _load("suzuka-tt-bez-tc_2026-10-26_181552.bin.xz", 13)
