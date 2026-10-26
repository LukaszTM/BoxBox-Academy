"""Pakiet Car Telemetry (id 6): prędkość, gaz, hamulec, bieg, temperatury.

Układ zgodny z docs/F1_25_Telemetry_Output_Structures.txt (format pakietu 2025).
"""
import struct
from dataclasses import dataclass

from boxbox.telemetry.header import HEADER_SIZE, PacketHeader, PacketId, parse_header

NUM_CARS = 22
_CAR = struct.Struct("<HfffBbHBBH4H4B4BH4f4B")
CAR_SIZE = _CAR.size  # 60
_TAIL = struct.Struct("<BBb")
PACKET_SIZE = HEADER_SIZE + NUM_CARS * CAR_SIZE + _TAIL.size  # 1352


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
    header: PacketHeader
    cars: tuple[CarTelemetry, ...]
    suggested_gear: int  # 0 = brak sugestii

    @property
    def player(self) -> CarTelemetry:
        return self.cars[self.header.player_car_index]


def _parse_car(data: bytes, offset: int) -> CarTelemetry:
    f = _CAR.unpack_from(data, offset)
    return CarTelemetry(
        speed_kmh=f[0], throttle=f[1], steer=f[2], brake=f[3], clutch=f[4],
        gear=f[5], engine_rpm=f[6], drs=bool(f[7]), rev_lights_percent=f[8],
        rev_lights_bit_value=f[9], brakes_temperature=f[10:14],
        tyres_surface_temperature=f[14:18], tyres_inner_temperature=f[18:22],
        engine_temperature=f[22], tyres_pressure=f[23:27], surface_type=f[27:31],
    )


def parse_car_telemetry(data: bytes) -> CarTelemetryPacket:
    header = parse_header(data)
    if header.kind is not PacketId.CAR_TELEMETRY:
        raise ValueError(f"to nie pakiet Car Telemetry (id {header.packet_id})")
    if len(data) != PACKET_SIZE:
        raise ValueError(f"zła długość pakietu: {len(data)} B, oczekiwano {PACKET_SIZE} B")
    cars = tuple(_parse_car(data, HEADER_SIZE + i * CAR_SIZE) for i in range(NUM_CARS))
    suggested_gear = _TAIL.unpack_from(data, HEADER_SIZE + NUM_CARS * CAR_SIZE)[2]
    return CarTelemetryPacket(header, cars, suggested_gear)
