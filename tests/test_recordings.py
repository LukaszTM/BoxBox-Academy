"""Testy parsera na prawdziwych nagraniach z recordings/ (kryterium etapu 1)."""
from pathlib import Path

import pytest

from boxbox.telemetry.recording import read_recording
from boxbox.telemetry.state import TelemetryState

RECORDINGS = sorted(Path(__file__).parent.parent.joinpath("recordings").glob("*.bin*"))
REQUIRED = {"SESSION", "LAP_DATA", "CAR_TELEMETRY", "CAR_STATUS", "CAR_DAMAGE"}


@pytest.mark.parametrize("path", RECORDINGS, ids=[p.name for p in RECORDINGS])
def test_every_packet_parses(path: Path) -> None:
    state = TelemetryState()
    for packet in read_recording(path):
        state.feed(packet.data)
    assert not state.unsupported_formats, state.unsupported_formats
    assert not state.errors, dict(state.errors)
    assert REQUIRED <= set(state.packets), set(state.packets)
    assert not [k for k in state.packets if k.startswith("NIEZNANY")]
    assert state.session is not None and state.session.track_length_m > 3000
    assert state.telemetry is not None and 0 <= state.telemetry.player.throttle <= 1
    assert state.lap is not None and state.lap.player.current_lap_num >= 1


def test_recordings_present() -> None:
    assert RECORDINGS, "brak nagrań w recordings/"
