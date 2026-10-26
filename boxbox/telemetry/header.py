"""Nagłówek pakietu telemetrii F1 25 (29 bajtów, little endian).

Układ zgodny z docs/F1_25_Telemetry_Output_Structures.txt. Obsługujemy dwa
formaty pakietów: 2025 (podstawowa gra) i 2026 (2026 Season Pack). Format
jest w nagłówku, a układ reszty pakietu zależy od niego.
"""
import struct
from collections.abc import Mapping
from dataclasses import dataclass
from enum import IntEnum
from typing import TypeVar

SUPPORTED_FORMATS = (2025, 2026)
NUM_CARS: dict[int, int] = {2025: 22, 2026: 24}


class PacketId(IntEnum):
    MOTION = 0
    SESSION = 1
    LAP_DATA = 2
    EVENT = 3
    PARTICIPANTS = 4
    CAR_SETUPS = 5
    CAR_TELEMETRY = 6
    CAR_STATUS = 7
    FINAL_CLASSIFICATION = 8
    LOBBY_INFO = 9
    CAR_DAMAGE = 10
    SESSION_HISTORY = 11
    TYRE_SETS = 12
    MOTION_EX = 13
    TIME_TRIAL = 14
    LAP_POSITIONS = 15
    CAR_TELEMETRY_2 = 16  # tylko format 2026


_HEADER = struct.Struct("<HBBBBBQfIIBB")
HEADER_SIZE = _HEADER.size  # 29


@dataclass(frozen=True)
class PacketHeader:
    packet_format: int
    game_year: int
    game_major_version: int
    game_minor_version: int
    packet_version: int
    packet_id: int
    session_uid: int
    session_time: float
    frame_identifier: int
    overall_frame_identifier: int
    player_car_index: int
    secondary_player_car_index: int

    @property
    def kind(self) -> PacketId | None:
        """Rodzaj pakietu albo None dla nieznanego id."""
        try:
            return PacketId(self.packet_id)
        except ValueError:
            return None

    @property
    def num_cars(self) -> int:
        return NUM_CARS[self.packet_format]


def parse_header(data: bytes) -> PacketHeader:
    if len(data) < HEADER_SIZE:
        raise ValueError(f"pakiet za krótki: {len(data)} B, nagłówek ma {HEADER_SIZE} B")
    return PacketHeader(*_HEADER.unpack_from(data))


def pack_header(header: PacketHeader) -> bytes:
    """Odwrotność parse_header - do budowania pakietów w testach."""
    return _HEADER.pack(
        header.packet_format, header.game_year, header.game_major_version,
        header.game_minor_version, header.packet_version, header.packet_id,
        header.session_uid, header.session_time, header.frame_identifier,
        header.overall_frame_identifier, header.player_car_index,
        header.secondary_player_car_index,
    )


T = TypeVar("T")


def check_packet(data: bytes, expected: PacketId, sizes: Mapping[int, int]) -> PacketHeader:
    """Wspólna walidacja: rodzaj pakietu, obsługiwany format, długość."""
    header = parse_header(data)
    if header.kind is not expected:
        raise ValueError(f"to nie pakiet {expected.name} (id {header.packet_id})")
    if header.packet_format not in sizes:
        raise ValueError(f"nieobsługiwany format pakietu: {header.packet_format}")
    if len(data) != sizes[header.packet_format]:
        raise ValueError(
            f"zła długość pakietu: {len(data)} B, oczekiwano {sizes[header.packet_format]} B"
            f" (format {header.packet_format})"
        )
    return header
