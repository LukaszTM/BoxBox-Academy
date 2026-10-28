"""Pakiet Participants (id 4): kto siedzi w którym aucie (AI, gracz, duch), nazwy, zespoły.

Układ zgodny z docs/F1_25_Telemetry_Output_Structures.txt (2025, 57 B na auto)
i docs/2026_Season_Pack_Telemetry_Output_Structures.txt (2026: driverId, networkId
i teamId to uint16, 60 B na auto).
"""
import re
import struct
from dataclasses import dataclass

from boxbox.telemetry.header import HEADER_SIZE, NUM_CARS, PacketHeader, PacketId, check_packet

_CAR: dict[int, struct.Struct] = {
    2025: struct.Struct("<BBBBBBB32sBBHBB" + "BBB" * 4),  # 57 B
    2026: struct.Struct("<BHHHBBB32sBBHBB" + "BBB" * 4),  # 60 B
}
_HEAD = struct.Struct("<B")  # numActiveCars
PACKET_SIZE: dict[int, int] = {
    fmt: HEADER_SIZE + _HEAD.size + NUM_CARS[fmt] * _CAR[fmt].size for fmt in _CAR
}  # 2025: 1284, 2026: 1470


@dataclass(frozen=True)
class Participant:
    ai_controlled: bool
    driver_id: int
    network_id: int
    team_id: int
    my_team: bool
    race_number: int
    nationality: int
    name: str
    telemetry_public: bool
    show_online_name: bool
    tech_level: int
    platform: int
    colours: tuple[tuple[int, int, int], ...]


@dataclass(frozen=True)
class ParticipantsPacket:
    header: PacketHeader
    num_active_cars: int
    cars: tuple[Participant, ...]

    @property
    def player(self) -> Participant:
        return self.cars[self.header.player_car_index]


def _parse_car(layout: struct.Struct, data: bytes, offset: int) -> Participant:
    f = layout.unpack_from(data, offset)
    raw_name: bytes = f[7]
    name = raw_name.split(b"\x00", 1)[0].decode("utf-8", errors="replace")
    num_colours = f[12]
    colours = tuple((f[13 + 3 * i], f[14 + 3 * i], f[15 + 3 * i]) for i in range(min(num_colours, 4)))
    return Participant(
        ai_controlled=bool(f[0]), driver_id=f[1], network_id=f[2], team_id=f[3], my_team=bool(f[4]),
        race_number=f[5], nationality=f[6], name=name, telemetry_public=bool(f[8]),
        show_online_name=bool(f[9]), tech_level=f[10], platform=f[11], colours=colours,
    )


def parse_participants(data: bytes) -> ParticipantsPacket:
    header = check_packet(data, PacketId.PARTICIPANTS, PACKET_SIZE)
    layout = _CAR[header.packet_format]
    num_active = _HEAD.unpack_from(data, HEADER_SIZE)[0]
    base = HEADER_SIZE + _HEAD.size
    cars = tuple(_parse_car(layout, data, base + i * layout.size) for i in range(header.num_cars))
    return ParticipantsPacket(header, num_active, cars)


ANON_PREFIX = "GRACZ-"
_AI_NAME = re.compile(r"^[A-Z][A-Z .'\-]{1,30}$")  # nazwiska kierowców AI z gry (HAMILTON, DE VRIES); gamertagi mają cyfry/małe litery


def is_ai_name(name: str) -> bool:
    return bool(_AI_NAME.match(name))


def anonymize_participants(data: bytes) -> bytes:
    """Zwraca kopię pakietu Participants z nazwami ludzi (gracz i inni online) zamienionymi na GRACZ-NN.

    Zostają tylko nazwiska kierowców AI z gry (same wielkie litery); gracz, duchy i rywale online dostają GRACZ-NN. Pakiet innego typu albo o złym rozmiarze wraca bez zmian, żeby nagrywanie
    nigdy nie padło przez anonimizację.
    """
    if len(data) < HEADER_SIZE or data[6] != PacketId.PARTICIPANTS:
        return data
    try:
        header = check_packet(data, PacketId.PARTICIPANTS, PACKET_SIZE)
    except ValueError:
        return data
    layout = _CAR[header.packet_format]
    base = HEADER_SIZE + _HEAD.size
    name_offset = struct.calcsize("<BBBBBBB") if header.packet_format == 2025 else struct.calcsize("<BHHHBBB")
    out = bytearray(data)
    for i in range(header.num_cars):
        car = base + i * layout.size
        raw = bytes(out[car + name_offset:car + name_offset + 32]).split(b"\x00", 1)[0]
        if not raw:
            continue
        current = raw.decode("utf-8", errors="replace")
        if out[car] != 0 and is_ai_name(current):  # kierowca AI z gry: nazwisko zostaje
            continue
        if current.startswith(ANON_PREFIX):
            continue
        name = f"{ANON_PREFIX}{i:02d}".encode("ascii")
        out[car + name_offset:car + name_offset + 32] = name.ljust(32, b"\x00")
    return bytes(out)
