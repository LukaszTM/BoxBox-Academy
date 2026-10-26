"""Pakiet Car Damage (id 10): zużycie i uszkodzenia opon, skrzydeł, silnika.

W F1 25 doszły pęcherze na oponach (tyreBlisters, 4 B na auto, 46 B zamiast 42 B w F1 24).
Układ zgodny z docs/F1_25_Telemetry_Output_Structures.txt (2025)
i docs/2026_Season_Pack_Telemetry_Output_Structures.txt (2026, zmienia się tylko liczba aut).
"""
import struct
from dataclasses import dataclass

from boxbox.telemetry.header import HEADER_SIZE, NUM_CARS, PacketHeader, PacketId, check_packet

_CAR = struct.Struct("<4f4B4B4B" + "B" * 6 + "BB" + "B" * 8 + "BB")
CAR_SIZE = _CAR.size  # 46
PACKET_SIZE: dict[int, int] = {
    fmt: HEADER_SIZE + n * CAR_SIZE for fmt, n in NUM_CARS.items()
}  # 2025: 1041, 2026: 1133


@dataclass(frozen=True)
class CarDamage:
    tyres_wear_percent: tuple[float, float, float, float]  # RL, RR, FL, FR
    tyres_damage_percent: tuple[int, int, int, int]
    brakes_damage_percent: tuple[int, int, int, int]
    tyre_blisters_percent: tuple[int, int, int, int]
    front_left_wing_damage_percent: int
    front_right_wing_damage_percent: int
    rear_wing_damage_percent: int
    floor_damage_percent: int
    diffuser_damage_percent: int
    sidepod_damage_percent: int
    drs_fault: bool
    ers_fault: bool
    gearbox_damage_percent: int
    engine_damage_percent: int
    engine_mguh_wear_percent: int
    engine_es_wear_percent: int
    engine_ce_wear_percent: int
    engine_ice_wear_percent: int
    engine_mguk_wear_percent: int
    engine_tc_wear_percent: int
    engine_blown: bool
    engine_seized: bool

    @property
    def has_aero_damage(self) -> bool:
        return any((
            self.front_left_wing_damage_percent, self.front_right_wing_damage_percent,
            self.rear_wing_damage_percent, self.floor_damage_percent,
            self.diffuser_damage_percent, self.sidepod_damage_percent,
        ))


@dataclass(frozen=True)
class CarDamagePacket:
    header: PacketHeader
    cars: tuple[CarDamage, ...]

    @property
    def player(self) -> CarDamage:
        return self.cars[self.header.player_car_index]


def _parse_car(data: bytes, offset: int) -> CarDamage:
    f = _CAR.unpack_from(data, offset)
    return CarDamage(
        tyres_wear_percent=f[0:4], tyres_damage_percent=f[4:8],
        brakes_damage_percent=f[8:12], tyre_blisters_percent=f[12:16],
        front_left_wing_damage_percent=f[16], front_right_wing_damage_percent=f[17],
        rear_wing_damage_percent=f[18], floor_damage_percent=f[19],
        diffuser_damage_percent=f[20], sidepod_damage_percent=f[21],
        drs_fault=bool(f[22]), ers_fault=bool(f[23]),
        gearbox_damage_percent=f[24], engine_damage_percent=f[25],
        engine_mguh_wear_percent=f[26], engine_es_wear_percent=f[27],
        engine_ce_wear_percent=f[28], engine_ice_wear_percent=f[29],
        engine_mguk_wear_percent=f[30], engine_tc_wear_percent=f[31],
        engine_blown=bool(f[32]), engine_seized=bool(f[33]),
    )


def parse_car_damage(data: bytes) -> CarDamagePacket:
    header = check_packet(data, PacketId.CAR_DAMAGE, PACKET_SIZE)
    cars = tuple(_parse_car(data, HEADER_SIZE + i * CAR_SIZE) for i in range(header.num_cars))
    return CarDamagePacket(header, cars)
