"""Aktualny stan telemetrii: ostatni pakiet każdego znanego typu."""
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from boxbox.telemetry.car_status import CarStatusPacket, parse_car_status
from boxbox.telemetry.car_telemetry import CarTelemetryPacket, parse_car_telemetry
from boxbox.telemetry.header import PacketId, parse_header
from boxbox.telemetry.lap_data import LapDataPacket, parse_lap_data
from boxbox.telemetry.session import SessionPacket, parse_session

# id pakietu -> (nazwa pola w TelemetryState, parser)
_PARSERS: dict[PacketId, tuple[str, Callable[[bytes], Any]]] = {
    PacketId.SESSION: ("session", parse_session),
    PacketId.LAP_DATA: ("lap", parse_lap_data),
    PacketId.CAR_TELEMETRY: ("telemetry", parse_car_telemetry),
    PacketId.CAR_STATUS: ("status", parse_car_status),
}


@dataclass
class TelemetryState:
    session: SessionPacket | None = None
    lap: LapDataPacket | None = None
    telemetry: CarTelemetryPacket | None = None
    status: CarStatusPacket | None = None
    packets: Counter[str] = field(default_factory=Counter)  # ile pakietów każdego typu
    errors: Counter[str] = field(default_factory=Counter)  # ile się nie sparsowało

    @property
    def empty(self) -> bool:
        return not self.packets

    def feed(self, data: bytes) -> None:
        """Przyjmuje surowy pakiet; nieznane i uszkodzone pakiety liczy, nie wywraca się."""
        try:
            header = parse_header(data)
        except ValueError:
            self.errors["nagłówek"] += 1
            return
        kind = header.kind
        name = kind.name if kind else f"NIEZNANY_{header.packet_id}"
        self.packets[name] += 1
        if kind not in _PARSERS:
            return
        attr, parser = _PARSERS[kind]
        try:
            setattr(self, attr, parser(data))
        except ValueError:
            self.errors[name] += 1
