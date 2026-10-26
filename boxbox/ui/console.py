"""Konsola: jedna linia ze stanem auta gracza, odświeżana w miejscu."""
import sys
import time
from collections.abc import Callable
from typing import TextIO

from boxbox.telemetry.state import TelemetryState

NO_DATA_MESSAGE = "brak danych"
GEARBOX_NAMES = {1: "ręczna", 2: "ręczna+sugestie", 3: "automat"}
TC_NAMES = {0: "wył.", 1: "średnia", 2: "pełna"}


def _gear(gear: int) -> str:
    return {-1: "R", 0: "N"}.get(gear, str(gear))


def render(state: TelemetryState) -> str:
    """Składa linię stanu; brakujące pakiety pokazuje jako '-'."""
    if state.empty:
        return NO_DATA_MESSAGE
    parts: list[str] = []
    if state.session:
        parts.append(f"{state.session.track_name} ({state.session.session_type_name})")
    if state.lap:
        lap = state.lap.player
        parts.append(f"okr {lap.current_lap_num}")
        parts.append(f"{lap.lap_distance:6.0f} m")
    else:
        parts += ["okr -", "     - m"]
    if state.telemetry:
        car = state.telemetry.player
        parts.append(f"{car.speed_kmh:3d} km/h")
        parts.append(f"bieg {_gear(car.gear)}")
        parts.append(f"gaz {car.throttle * 100:3.0f}%")
        parts.append(f"ham {car.brake * 100:3.0f}%")
    else:
        parts += ["  - km/h", "bieg -", "gaz   -", "ham   -"]
    if state.status:
        status = state.status.player
        parts.append(f"ERS {status.ers_store_percent:3.0f}%")
    else:
        parts.append("ERS   -")
    parts.append("asysty: " + _assists(state))
    return " | ".join(parts)


def _assists(state: TelemetryState) -> str:
    items: list[str] = []
    if state.session:
        a = state.session.assists
        items.append("skrzynia " + GEARBOX_NAMES.get(a.gearbox, str(a.gearbox)))
        if a.braking:
            items.append(f"hamowanie {a.braking}")
    if state.status:
        s = state.status.player
        items.append("TC " + TC_NAMES.get(s.traction_control, str(s.traction_control)))
        items.append("ABS " + ("wł." if s.anti_lock_brakes else "wył."))
    return ", ".join(items) or "-"


class Console:
    """Wypisuje stan nie częściej niż co `interval` sekund, nadpisując linię."""

    def __init__(
        self,
        out: TextIO | None = None,
        interval: float = 0.1,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._out = out or sys.stdout  # sys.stdout brany teraz, nie przy definicji (testy go podmieniają)
        self._interval = interval
        self._clock = clock
        self._last_print = -interval
        self._last_len = 0

    def update(self, state: TelemetryState, force: bool = False) -> None:
        now = self._clock()
        if not force and now - self._last_print < self._interval:
            return
        self._last_print = now
        line = render(state)
        self._out.write("\r" + line.ljust(self._last_len))
        self._out.flush()
        self._last_len = len(line)

    def finish(self) -> None:
        self._out.write("\n")
        self._out.flush()
