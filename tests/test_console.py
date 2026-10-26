import io

import pytest

from boxbox.telemetry.state import TelemetryState
from boxbox.ui.console import NO_DATA_MESSAGE, Console, render
from tests.builders import FORMATS, lap_packet, session_packet, status_packet, telemetry_packet


def full_state(fmt: int = 2025) -> TelemetryState:
    state = TelemetryState()
    for packet in (session_packet(fmt), lap_packet(fmt), telemetry_packet(fmt), status_packet(fmt)):
        state.feed(packet)
    return state


def test_render_empty_state() -> None:
    assert render(TelemetryState()) == NO_DATA_MESSAGE


@pytest.mark.parametrize("fmt", FORMATS)
def test_render_full_state(fmt: int) -> None:
    line = render(full_state(fmt))
    assert line.startswith(
        "Bahrajn (time trial) | okr 3 |   1234 m | 287 km/h | bieg 6 | gaz  75% | ham  25% | ERS  75%"
    )
    assert line.endswith("asysty: skrzynia automat, hamowanie 2, TC średnia, ABS wł.")


def test_render_partial_state_uses_placeholders() -> None:
    state = TelemetryState()
    state.feed(telemetry_packet())
    line = render(state)
    assert "okr -" in line and "287 km/h" in line and "ERS   -" in line
    assert line.endswith("asysty: -")


def test_state_counts_unknown_and_broken_packets() -> None:
    state = TelemetryState()
    state.feed(b"\x00" * 10)  # za krótki na nagłówek
    state.feed(telemetry_packet()[:-1])  # dobry nagłówek, zła długość
    broken = bytearray(lap_packet())
    broken[6] = 200  # nieznany id pakietu (bajt 6 nagłówka)
    state.feed(bytes(broken))
    assert state.errors["nagłówek"] == 1
    assert state.errors["CAR_TELEMETRY"] == 1 and state.telemetry is None
    assert state.packets["NIEZNANY_200"] == 1


def test_console_rate_limits_and_overwrites_line() -> None:
    out = io.StringIO()
    now = 0.0
    console = Console(out, interval=0.1, clock=lambda: now)
    state = TelemetryState()
    console.update(state)  # pierwszy zapis zawsze
    console.update(state)  # za wcześnie - pominięty
    now = 0.2
    state.feed(telemetry_packet())
    console.update(state)
    console.finish()
    text = out.getvalue()
    assert text.count("\r") == 2
    assert text.startswith("\r" + NO_DATA_MESSAGE + "\r")
    assert text.endswith("\n")
