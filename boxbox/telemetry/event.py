"""Pakiet Event (id 3): zdarzenia w sesji - flagi, kary, SC, kolizje, najszybsze okrążenie.

Po nagłówku są 4 bajty kodu zdarzenia (np. b"PENA"), a dalej szczegóły,
których układ zależy od kodu. Układ zapisany z pamięci - do potwierdzenia
ze specyfikacją EA w docs/.
"""
import struct
from dataclasses import dataclass

from boxbox.telemetry.header import HEADER_SIZE, PacketHeader, PacketId, parse_header

CODE_OFFSET = HEADER_SIZE
DETAILS_OFFSET = HEADER_SIZE + 4
PACKET_SIZE = 45  # nagłówek + kod + największa unia szczegółów (12 B)

EVENT_NAMES: dict[str, str] = {
    "SSTA": "start sesji", "SEND": "koniec sesji", "FTLP": "najszybsze okrążenie",
    "RTMT": "wycofanie", "DRSE": "DRS włączony", "DRSD": "DRS wyłączony",
    "TMPT": "partner w boksie", "CHQF": "flaga w szachownicę", "RCWN": "zwycięzca",
    "PENA": "kara", "SPTP": "fotoradar", "STLG": "światła startowe", "LGOT": "światła zgasły",
    "DTSV": "drive-through odbyty", "SGSV": "stop-go odbyty", "FLBK": "flashback",
    "BUTN": "przycisk", "RDFL": "czerwona flaga", "OVTK": "wyprzedzanie",
    "SCAR": "samochód bezpieczeństwa", "COLL": "kolizja",
}


@dataclass(frozen=True)
class VehicleEvent:
    """Zdarzenia dotyczące jednego auta: RTMT, TMPT, RCWN, DTSV, SGSV."""

    vehicle_index: int


@dataclass(frozen=True)
class FastestLap:
    vehicle_index: int
    lap_time_s: float


@dataclass(frozen=True)
class Penalty:
    penalty_type: int
    infringement_type: int
    vehicle_index: int
    other_vehicle_index: int
    time_s: int
    lap_num: int
    places_gained: int


@dataclass(frozen=True)
class SpeedTrap:
    vehicle_index: int
    speed_kmh: float
    is_overall_fastest_in_session: bool
    is_driver_fastest_in_session: bool
    fastest_vehicle_index_in_session: int
    fastest_speed_in_session_kmh: float


@dataclass(frozen=True)
class StartLights:
    num_lights: int


@dataclass(frozen=True)
class Flashback:
    frame_identifier: int
    session_time_s: float


@dataclass(frozen=True)
class Buttons:
    button_status: int  # maska bitowa wciśniętych przycisków


@dataclass(frozen=True)
class Overtake:
    overtaking_vehicle_index: int
    being_overtaken_vehicle_index: int


@dataclass(frozen=True)
class SafetyCar:
    safety_car_type: int  # 0 brak, 1 pełny, 2 wirtualny, 3 formation lap
    event_type: int  # 0 wyjazd, 1 powrót, 2 wezwany, 3 reset pozycji


@dataclass(frozen=True)
class Collision:
    vehicle1_index: int
    vehicle2_index: int


Details = (
    VehicleEvent | FastestLap | Penalty | SpeedTrap | StartLights | Flashback
    | Buttons | Overtake | SafetyCar | Collision | None
)

# kod -> (format struct, klasa szczegółów)
_DETAILS: dict[str, tuple[struct.Struct, type]] = {
    "FTLP": (struct.Struct("<Bf"), FastestLap),
    "RTMT": (struct.Struct("<B"), VehicleEvent),
    "TMPT": (struct.Struct("<B"), VehicleEvent),
    "RCWN": (struct.Struct("<B"), VehicleEvent),
    "DTSV": (struct.Struct("<B"), VehicleEvent),
    "SGSV": (struct.Struct("<B"), VehicleEvent),
    "PENA": (struct.Struct("<BBBBBBB"), Penalty),
    "SPTP": (struct.Struct("<BfBBBf"), SpeedTrap),
    "STLG": (struct.Struct("<B"), StartLights),
    "FLBK": (struct.Struct("<If"), Flashback),
    "BUTN": (struct.Struct("<I"), Buttons),
    "OVTK": (struct.Struct("<BB"), Overtake),
    "SCAR": (struct.Struct("<BB"), SafetyCar),
    "COLL": (struct.Struct("<BB"), Collision),
}


@dataclass(frozen=True)
class EventPacket:
    header: PacketHeader
    code: str
    details: Details

    @property
    def name(self) -> str:
        return EVENT_NAMES.get(self.code, f"zdarzenie {self.code}")


def parse_event(data: bytes) -> EventPacket:
    header = parse_header(data)
    if header.kind is not PacketId.EVENT:
        raise ValueError(f"to nie pakiet Event (id {header.packet_id})")
    if len(data) != PACKET_SIZE:
        raise ValueError(f"zła długość pakietu: {len(data)} B, oczekiwano {PACKET_SIZE} B")
    code = data[CODE_OFFSET:DETAILS_OFFSET].decode("ascii", errors="replace")
    spec = _DETAILS.get(code)
    if spec is None:
        return EventPacket(header, code, None)
    layout, cls = spec
    fields = layout.unpack_from(data, DETAILS_OFFSET)
    if cls is SpeedTrap:
        fields = (fields[0], fields[1], bool(fields[2]), bool(fields[3]), fields[4], fields[5])
    return EventPacket(header, code, cls(*fields))
