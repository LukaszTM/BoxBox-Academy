"""Pakiet Car Telemetry 2 (id 16, tylko format 2026): aktywne aero, tryb overtake.

Układ zgodny z docs/2026_Season_Pack_Telemetry_Output_Structures.txt.
"""
import struct
from dataclasses import dataclass

from boxbox.telemetry.header import HEADER_SIZE, NUM_CARS, PacketHeader, PacketId, check_packet

_CAR = struct.Struct("<BBHBBHBB")
CAR_SIZE = _CAR.size  # 10
PACKET_SIZE: dict[int, int] = {2026: HEADER_SIZE + NUM_CARS[2026] * CAR_SIZE}  # 269


@dataclass(frozen=True)
class CarTelemetry2:
    active_aero_mode: int  # 0 tryb zakrętowy, 1 tryb prosta
    active_aero_available: bool
    active_aero_activation_distance_m: int  # 0 = niedostępne
    overtake_available: bool
    overtake_active: bool
    overtake_activation_distance_m: int  # 0 = niedostępny
    regulations_2026: bool  # czy auto jedzie wg przepisów 2026
    driving_wrong_way: bool


@dataclass(frozen=True)
class CarTelemetry2Packet:
    header: PacketHeader
    cars: tuple[CarTelemetry2, ...]

    @property
    def player(self) -> CarTelemetry2:
        return self.cars[self.header.player_car_index]


def _parse_car(data: bytes, offset: int) -> CarTelemetry2:
    f = _CAR.unpack_from(data, offset)
    return CarTelemetry2(
        active_aero_mode=f[0], active_aero_available=bool(f[1]),
        active_aero_activation_distance_m=f[2], overtake_available=bool(f[3]),
        overtake_active=bool(f[4]), overtake_activation_distance_m=f[5],
        regulations_2026=bool(f[6]), driving_wrong_way=bool(f[7]),
    )


def parse_car_telemetry2(data: bytes) -> CarTelemetry2Packet:
    header = check_packet(data, PacketId.CAR_TELEMETRY_2, PACKET_SIZE)
    cars = tuple(_parse_car(data, HEADER_SIZE + i * CAR_SIZE) for i in range(header.num_cars))
    return CarTelemetry2Packet(header, cars)
