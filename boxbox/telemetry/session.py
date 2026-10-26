"""Pakiet Session (id 1): tor, typ sesji, pogoda, asysty, ustawienia gry.

Układ zgodny z docs/F1_25_Telemetry_Output_Structures.txt (2025, 753 B)
i docs/2026_Season_Pack_Telemetry_Output_Structures.txt (2026, 926 B).
Format 2026 dokłada na końcu strefy aktywnego aero i DRS, czas reakcji na starcie
oraz asysty TC/ABS. Parsujemy tylko to, co jest potrzebne trenerowi i inżynierowi;
strefy marshali, prognozę pogody i strefy aktywnego aero pomijamy.
"""
import struct
from dataclasses import dataclass

from boxbox.telemetry.header import HEADER_SIZE, PacketHeader, PacketId, check_packet

NUM_MARSHAL_ZONES = 21
NUM_WEATHER_SAMPLES = 64
NUM_ACTIVE_AERO_ZONES = 8  # tylko 2026
NUM_DRS_ZONES = 4  # tylko 2026

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
# Ogon tylko w formacie 2026.
EXTRA_2026 = struct.Struct(
    "<BB"  # activeAeroTrackStatus, numActiveAeroZonesFull
    + "ff" * NUM_ACTIVE_AERO_ZONES  # strefy aktywnego aero (pełne)
    + "B" + "ff" * NUM_ACTIVE_AERO_ZONES  # numActiveAeroZonesPartial + strefy częściowe
    + "B" + "ff" * NUM_DRS_ZONES  # numDRSZones + strefy DRS (ułamek okrążenia: start, koniec)
    + "f"  # startReactionTime
    + "BBBBB"  # ABS, TC, linia hi-vis, linia dla daltonistów, przypomnienie o rewind
)

PREFIX_OFFSET = HEADER_SIZE
MIDDLE_OFFSET = PREFIX_OFFSET + PREFIX.size + NUM_MARSHAL_ZONES * MARSHAL_ZONE.size
REST_OFFSET = MIDDLE_OFFSET + MIDDLE.size + NUM_WEATHER_SAMPLES * WEATHER_SAMPLE.size
EXTRA_OFFSET = REST_OFFSET + REST.size
PACKET_SIZE: dict[int, int] = {2025: EXTRA_OFFSET, 2026: EXTRA_OFFSET + EXTRA_2026.size}  # 753, 926

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
    """Asysty z ustawień gry. TC i ABS są zawsze w Car Status; w formacie 2026 także tutaj."""

    steering: bool
    braking: int  # 0 wył., 1 niska, 2 średnia, 3 wysoka
    gearbox: int  # 1 ręczna, 2 ręczna + sugestie, 3 automat
    pit: bool
    pit_release: bool
    ers: bool
    drs: bool
    dynamic_racing_line: int  # 0 wył., 1 tylko zakręty, 2 cała
    dynamic_racing_line_type: int  # 0 2D, 1 3D
    traction_control: int | None = None  # tylko 2026: 0 wył., 1 średnia, 2 pełna
    anti_lock_brakes: bool | None = None  # tylko 2026


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
    ai_difficulty: int  # 0-110
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
    drs_zones: tuple[tuple[float, float], ...] = ()  # tylko 2026: (start, koniec) jako ułamek okrążenia
    start_reaction_time_s: float | None = None  # tylko 2026

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
    header = check_packet(data, PacketId.SESSION, PACKET_SIZE)
    p = PREFIX.unpack_from(data, PREFIX_OFFSET)
    m = MIDDLE.unpack_from(data, MIDDLE_OFFSET)
    r = REST.unpack_from(data, REST_OFFSET)
    assists = Assists(
        steering=bool(r[8]), braking=r[9], gearbox=r[10], pit=bool(r[11]),
        pit_release=bool(r[12]), ers=bool(r[13]), drs=bool(r[14]),
        dynamic_racing_line=r[15], dynamic_racing_line_type=r[16],
    )
    drs_zones: tuple[tuple[float, float], ...] = ()
    start_reaction_time: float | None = None
    if header.packet_format == 2026:
        e = EXTRA_2026.unpack_from(data, EXTRA_OFFSET)
        drs_start = 2 + 2 * NUM_ACTIVE_AERO_ZONES + 1 + 2 * NUM_ACTIVE_AERO_ZONES + 1
        num_drs = e[drs_start - 1]
        drs_zones = tuple(
            (e[drs_start + 2 * i], e[drs_start + 2 * i + 1]) for i in range(num_drs)
        )
        tail = drs_start + 2 * NUM_DRS_ZONES
        start_reaction_time = e[tail]
        assists = Assists(
            **{k: v for k, v in assists.__dict__.items() if k not in ("traction_control", "anti_lock_brakes")},
            anti_lock_brakes=bool(e[tail + 1]), traction_control=e[tail + 2],
        )
    return SessionPacket(
        header=header,
        weather=p[0], track_temperature=p[1], air_temperature=p[2], total_laps=p[3],
        track_length_m=p[4], session_type=p[5], track_id=p[6], formula=p[7],
        session_time_left_s=p[8], session_duration_s=p[9], pit_speed_limit_kmh=p[10],
        game_paused=bool(p[11]), is_spectating=bool(p[12]),
        safety_car_status=m[0], network_game=bool(m[1]),
        ai_difficulty=r[1], pit_stop_window_ideal_lap=r[5], pit_stop_window_latest_lap=r[6],
        pit_stop_rejoin_position=r[7],
        assists=assists,
        game_mode=r[17], rule_set=r[18], time_of_day_min=r[19], session_length=r[20],
        sector2_lap_distance_start=r[-2], sector3_lap_distance_start=r[-1],
        drs_zones=drs_zones, start_reaction_time_s=start_reaction_time,
    )
