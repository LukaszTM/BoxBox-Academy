"""Nagłówek pakietu telemetrii F1 25 (29 bajtów, little endian).

Układ pól zapisany z pamięci - do potwierdzenia ze specyfikacją EA w docs/.
"""
import struct
from dataclasses import dataclass
from enum import IntEnum


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
