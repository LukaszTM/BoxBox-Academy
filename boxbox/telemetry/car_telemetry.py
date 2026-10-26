"""Pakiet Car Telemetry (id 6): prędkość, gaz, hamulec, bieg, temperatury.

Układ zgodny z docs/F1_25_Telemetry_Output_Structures.txt (2025)
i docs/2026_Season_Pack_Telemetry_Output_Structures.txt (2026).
Różnica w 2026: temperatura silnika to uint8 zamiast uint16 (59 B zamiast 60 B na auto).
"""
import struct
from dataclasses import dataclass, field
from functools import cached_property

from boxbox.telemetry.header import HEADER_SIZE, NUM_CARS, PacketHeader, PacketId, check_packet

_CAR: dict[int, struct.Struct] = {
    2025: struct.Struct("<HfffBbHBBH4H4B4BH4f4B"),  # 60 B
    2026: struct.Struct("<HfffBbHBBH4H4B4BB4f4B"),  # 59 B
}
_TAIL = struct.Struct("<BBb")  # panel MFD gracza 1 i 2, sugerowany bieg
PACKET_SIZE: dict[int, int] = {
    fmt: HEADER_SIZE + NUM_CARS[fmt] * _CAR[fmt].size + _TAIL.size for fmt in _CAR
}  # 2025: 1352, 2026: 1448


@dataclass(frozen=True)
class CarTelemetry:
    speed_kmh: int
    throttle: float  # 0.0 - 1.0
    steer: float  # -1.0 (lewo) - 1.0 (prawo)
    brake: float  # 0.0 - 1.0
    clutch: int  # 0 - 100
    gear: int  # -1 wsteczny, 0 luz, 1-8
    engine_rpm: int
    drs: bool
    rev_lights_percent: int
    rev_lights_bit_value: int
    brakes_temperature: tuple[int, int, int, int]  # RL, RR, FL, FR
    tyres_surface_temperature: tuple[int, int, int, int]
    tyres_inner_temperature: tuple[int, int, int, int]
    engine_temperature: int
    tyres_pressure: tuple[float, float, float, float]
    surface_type: tuple[int, int, int, int]


@dataclass(frozen=True)
class CarTelemetryPacket:
    """Auta parsowane leniwie: `car(i)` tylko jedno, `cars` wszystkie (raz, z pamięcią)."""

    header: PacketHeader
    suggested_gear: int  # 0 = brak sugestii
    _data: bytes = field(repr=False, compare=False)

    def car(self, index: int) -> CarTelemetry:
        layout = _CAR[self.header.packet_format]
        return _parse_car(layout, self._data, HEADER_SIZE + index * layout.size)

    @cached_property
    def cars(self) -> tuple[CarTelemetry, ...]:
        return tuple(self.car(i) for i in range(self.header.num_cars))

    @property
    def player(self) -> CarTelemetry:
        return self.car(self.header.player_car_index)


def _parse_car(layout: struct.Struct, data: bytes, offset: int) -> CarTelemetry:
    f = layout.unpack_from(data, offset)
    return CarTelemetry(
        speed_kmh=f[0], throttle=f[1], steer=f[2], brake=f[3], clutch=f[4],
        gear=f[5], engine_rpm=f[6], drs=bool(f[7]), rev_lights_percent=f[8],
        rev_lights_bit_value=f[9], brakes_temperature=f[10:14],
        tyres_surface_temperature=f[14:18], tyres_inner_temperature=f[18:22],
        engine_temperature=f[22], tyres_pressure=f[23:27], surface_type=f[27:31],
    )


def parse_car_telemetry(data: bytes) -> CarTelemetryPacket:
    header = check_packet(data, PacketId.CAR_TELEMETRY, PACKET_SIZE)
    layout = _CAR[header.packet_format]
    suggested_gear = _TAIL.unpack_from(data, HEADER_SIZE + header.num_cars * layout.size)[2]
    return CarTelemetryPacket(header, suggested_gear, bytes(data))
