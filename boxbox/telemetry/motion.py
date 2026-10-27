"""Pakiet Motion (id 0): pozycja i orientacja aut w świecie gry.

Potrzebny tylko do rysowania realnego kształtu toru (recorder); trener go nie używa,
więc parsujemy wyłącznie auto gracza. 2025: 60 B na auto (przeciążenia jako float),
2026: 54 B (przeciążenia skwantowane do int16). Układ z docs/*Output_Structures.txt.
"""
import struct
from dataclasses import dataclass

from boxbox.telemetry.header import HEADER_SIZE, NUM_CARS, PacketHeader, PacketId, check_packet

_CAR: dict[int, struct.Struct] = {2025: struct.Struct("<6f6h6f"), 2026: struct.Struct("<6f9h3f")}
CAR_SIZE: dict[int, int] = {fmt: s.size for fmt, s in _CAR.items()}  # 60, 54
PACKET_SIZE: dict[int, int] = {fmt: HEADER_SIZE + NUM_CARS[fmt] * CAR_SIZE[fmt] for fmt in _CAR}  # 1349, 1325


@dataclass(frozen=True)
class CarMotion:
    x: float  # metry, układ świata gry
    y: float  # wysokość
    z: float
    yaw: float  # radiany


@dataclass(frozen=True)
class MotionPacket:
    header: PacketHeader
    player: CarMotion


def parse_motion(data: bytes) -> MotionPacket:
    header = check_packet(data, PacketId.MOTION, PACKET_SIZE)
    fmt = header.packet_format
    f = _CAR[fmt].unpack_from(data, HEADER_SIZE + header.player_car_index * CAR_SIZE[fmt])
    yaw = f[-3]  # ostatnie trzy pola to yaw, pitch, roll w obu formatach
    return MotionPacket(header, CarMotion(f[0], f[1], f[2], yaw))
