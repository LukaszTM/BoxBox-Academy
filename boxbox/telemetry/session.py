"""Pakiet Session (id 1): tor, typ sesji, pogoda, asysty, ustawienia gry.

Układ zgodny z docs/F1_25_Telemetry_Output_Structures.txt. Parsujemy tylko to,
co jest potrzebne trenerowi i inżynierowi; strefy marshali i prognozę pogody pomijamy.
"""
import struct
from dataclasses import dataclass

from boxbox.telemetry.header import HEADER_SIZE, PacketHeader, PacketId, parse_header

NUM_MARSHAL_ZONES = 21
NUM_WEATHER_SAMPLES = 64

# Segmenty pakietu po nagłówku: prefiks, strefy marshali, środek, prognoza, reszta.
PREFIX = struct.Struct("<BbbBHBbBHHBBBBBB")
MARSHAL_ZONE = struct.Struct("<fb")
MIDDLE = struct.Struct("<BBB")
WEATHER_SAMPLE = struct.Struct("<BBBbbbbB")
REST = struct.Struct(
    "<BB"  # forecastAccuracy, aiDifficulty
    + "III"  # season/weekend/session link id
    + "BBB"  # okno pit-stopu: idealne, ostatnie okrążenie, pozycja po zjeździe
    + "B" * 9  # asysty
    + "BB"  # gameMode, ruleSet
    + "I"  # timeOfDay (minuty)
    + "B" * 5  # sessionLength, jednostki
    + "BBB"  # liczba okresów SC, VSC, czerwonej flagi
    + "B" * 24  # ustawienia reguł (equalCarPerformance ... affectsLicenceLevelMP)
    + "B"  # numSessionsInWeekend
    + "B" * 12  # weekendStructure
    + "ff"  # początek sektora 2 i 3 (m)
)

PREFIX_OFFSET = HEADER_SIZE
MIDDLE_OFFSET = PREFIX_OFFSET + PREFIX.size + NUM_MARSHAL_ZONES * MARSHAL_ZONE.size
REST_OFFSET = MIDDLE_OFFSET + MIDDLE.size + NUM_WEATHER_SAMPLES * WEATHER_SAMPLE.size
PACKET_SIZE = REST_OFFSET + REST.size  # 753

TRACK_NAMES: dict[int, str] = {  # załącznik "Track IDs" w docs/Data_Output_from_F1_25_v3.pdf
    0: "Melbourne", 2: "Szanghaj", 3: "Bahrajn", 4: "Barcelona", 5: "Monako", 6: "Montreal",
    7: "Silverstone", 9: "Hungaroring", 10: "Spa", 11: "Monza", 12: "Singapur", 13: "Suzuka",
    14: "Abu Zabi", 15: "Austin", 16: "Interlagos", 17: "Spielberg", 19: "Meksyk", 20: "Baku",
    26: "Zandvoort", 27: "Imola", 29: "Dżudda", 30: "Miami", 31: "Las Vegas", 32: "Losail",
    39: "Silverstone (odwrotny)", 40: "Spielberg (odwrotny)", 41: "Zandvoort (odwrotny)",
}

SESSION_TYPE_NAMES: dict[int, str] = {
    0: "nieznana", 1: "trening 1", 2: "trening 2", 3: "trening 3", 4: "krótki trening",
    5: "Q1", 6: "Q2", 7: "Q3", 8: "krótkie kwalifikacje", 9: "kwalifikacje (1 sesja)",
    10: "sprint shootout 1", 11: "sprint shootout 2", 12: "sprint shootout 3",
    13: "krótki sprint shootout", 14: "sprint shootout (1 sesja)",
    15: "wyścig", 16: "wyścig 2", 17: "wyścig 3", 18: "time trial",
}

WEATHER_NAMES: dict[int, str] = {
    0: "słonecznie", 1: "lekkie zachmurzenie", 2: "pochmurno",
    3: "lekki deszcz", 4: "ulewa", 5: "burza",
}


@dataclass(frozen=True)
class Assists:
    """Asysty z ustawień gry. TC i ABS są w pakiecie Car Status, nie tutaj."""

    steering: bool
    braking: int  # 0 wył., 1 niska, 2 średnia, 3 wysoka
    gearbox: int  # 1 ręczna, 2 ręczna + sugestie, 3 automat
    pit: bool
    pit_release: bool
    ers: bool
    drs: bool
    dynamic_racing_line: int  # 0 wył., 1 tylko zakręty, 2 cała
    dynamic_racing_line_type: int  # 0 2D, 1 3D


@dataclass(frozen=True)
class SessionPacket:
    header: PacketHeader
    weather: int
    track_temperature: int
    air_temperature: int
    total_laps: int
    track_length_m: int
    session_type: int
    track_id: int
    formula: int
    session_time_left_s: int
    session_duration_s: int
    pit_speed_limit_kmh: int
    game_paused: bool
    is_spectating: bool
    safety_car_status: int  # 0 brak, 1 SC, 2 VSC, 3 formation lap
    network_game: bool
    pit_stop_window_ideal_lap: int
    pit_stop_window_latest_lap: int
    pit_stop_rejoin_position: int
    assists: Assists
    game_mode: int
    rule_set: int
    time_of_day_min: int
    session_length: int
    sector2_lap_distance_start: float
    sector3_lap_distance_start: float

    @property
    def track_name(self) -> str:
        return TRACK_NAMES.get(self.track_id, f"tor {self.track_id}")

    @property
    def session_type_name(self) -> str:
        return SESSION_TYPE_NAMES.get(self.session_type, f"sesja {self.session_type}")

    @property
    def weather_name(self) -> str:
        return WEATHER_NAMES.get(self.weather, f"pogoda {self.weather}")


def parse_session(data: bytes) -> SessionPacket:
    header = parse_header(data)
    if header.kind is not PacketId.SESSION:
        raise ValueError(f"to nie pakiet Session (id {header.packet_id})")
    if len(data) != PACKET_SIZE:
        raise ValueError(f"zła długość pakietu: {len(data)} B, oczekiwano {PACKET_SIZE} B")
    p = PREFIX.unpack_from(data, PREFIX_OFFSET)
    m = MIDDLE.unpack_from(data, MIDDLE_OFFSET)
    r = REST.unpack_from(data, REST_OFFSET)
    return SessionPacket(
        header=header,
        weather=p[0], track_temperature=p[1], air_temperature=p[2], total_laps=p[3],
        track_length_m=p[4], session_type=p[5], track_id=p[6], formula=p[7],
        session_time_left_s=p[8], session_duration_s=p[9], pit_speed_limit_kmh=p[10],
        game_paused=bool(p[11]), is_spectating=bool(p[12]),
        safety_car_status=m[0], network_game=bool(m[1]),
        pit_stop_window_ideal_lap=r[5], pit_stop_window_latest_lap=r[6],
        pit_stop_rejoin_position=r[7],
        assists=Assists(
            steering=bool(r[8]), braking=r[9], gearbox=r[10], pit=bool(r[11]),
            pit_release=bool(r[12]), ers=bool(r[13]), drs=bool(r[14]),
            dynamic_racing_line=r[15], dynamic_racing_line_type=r[16],
        ),
        game_mode=r[17], rule_set=r[18], time_of_day_min=r[19], session_length=r[20],
        sector2_lap_distance_start=r[-2], sector3_lap_distance_start=r[-1],
    )
