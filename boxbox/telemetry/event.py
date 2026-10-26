"""Pakiet Event (id 3): zdarzenia w sesji - flagi, kary, SC, kolizje, najszybsze okrążenie.

Po nagłówku są 4 bajty kodu zdarzenia (np. b"PENA"), a dalej szczegóły,
których układ zależy od kodu. Układ zgodny z docs/F1_25_Telemetry_Output_Structures.txt
(2025) i docs/2026_Season_Pack_Telemetry_Output_Structures.txt (2026: kolizja ma wagę).
"""
import struct
from dataclasses import dataclass

from boxbox.telemetry.header import HEADER_SIZE, PacketHeader, PacketId, check_packet

CODE_OFFSET = HEADER_SIZE
DETAILS_OFFSET = HEADER_SIZE + 4
PACKET_SIZE: dict[int, int] = {2025: 45, 2026: 45}  # nagłówek + kod + największa unia (12 B)

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
    """Zdarzenia dotyczące jednego auta: TMPT, RCWN, DTSV."""

    vehicle_index: int


@dataclass(frozen=True)
class Retirement:
    vehicle_index: int
    reason: int  # 1 wycofany, 3 uszkodzenia, 6 czarna flaga, 8 awaria mechaniczna (pełna lista w spec.)


@dataclass(frozen=True)
class DrsDisabled:
    reason: int  # 0 mokry tor, 1 SC, 2 czerwona flaga, 3 za wcześnie (min. okrążenie)


@dataclass(frozen=True)
class StopGoServed:
    vehicle_index: int
    stop_time_s: float


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
    severity: int | None = None  # tylko 2026: 0 lekka, 1 średnia, 2 ciężka


Details = (
    VehicleEvent | Retirement | DrsDisabled | StopGoServed | FastestLap | Penalty
    | SpeedTrap | StartLights | Flashback | Buttons | Overtake | SafetyCar | Collision | None
)

# kod -> (format struct, klasa szczegółów); wspólne dla obu formatów pakietu
_DETAILS: dict[str, tuple[struct.Struct, type]] = {
    "FTLP": (struct.Struct("<Bf"), FastestLap),
    "RTMT": (struct.Struct("<BB"), Retirement),
    "DRSD": (struct.Struct("<B"), DrsDisabled),
    "TMPT": (struct.Struct("<B"), VehicleEvent),
    "RCWN": (struct.Struct("<B"), VehicleEvent),
    "DTSV": (struct.Struct("<B"), VehicleEvent),
    "SGSV": (struct.Struct("<Bf"), StopGoServed),
    "PENA": (struct.Struct("<BBBBBBB"), Penalty),
    "SPTP": (struct.Struct("<BfBBBf"), SpeedTrap),
    "STLG": (struct.Struct("<B"), StartLights),
    "FLBK": (struct.Struct("<If"), Flashback),
    "BUTN": (struct.Struct("<I"), Buttons),
    "OVTK": (struct.Struct("<BB"), Overtake),
    "SCAR": (struct.Struct("<BB"), SafetyCar),
    "COLL": (struct.Struct("<BB"), Collision),
}
_DETAILS_2026: dict[str, tuple[struct.Struct, type]] = {
    "COLL": (struct.Struct("<BBB"), Collision),
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
    header = check_packet(data, PacketId.EVENT, PACKET_SIZE)
    code = data[CODE_OFFSET:DETAILS_OFFSET].decode("ascii", errors="replace")
    spec = _DETAILS.get(code)
    if header.packet_format == 2026:
        spec = _DETAILS_2026.get(code, spec)
    if spec is None:
        return EventPacket(header, code, None)
    layout, cls = spec
    fields = layout.unpack_from(data, DETAILS_OFFSET)
    if cls is SpeedTrap:
        fields = (fields[0], fields[1], bool(fields[2]), bool(fields[3]), fields[4], fields[5])
    return EventPacket(header, code, cls(*fields))
