"""Pakiet Lap Data (id 2): czasy, dystans okrążenia, pozycja, pit, kary.

Układ zgodny z docs/F1_25_Telemetry_Output_Structures.txt (2025)
i docs/2026_Season_Pack_Telemetry_Output_Structures.txt (2026).
W 2026 zmienia się tylko liczba aut (24).
"""
import struct
from dataclasses import dataclass

from boxbox.telemetry.header import HEADER_SIZE, NUM_CARS, PacketHeader, PacketId, check_packet

_CAR = struct.Struct("<IIHBHBHBHBfffBBBBBBBBBBBBBBBHHBfB")
CAR_SIZE = _CAR.size  # 57
_TAIL = struct.Struct("<BB")  # indeksy aut: rekord osobisty i rywal w Time Trial
PACKET_SIZE: dict[int, int] = {
    fmt: HEADER_SIZE + n * CAR_SIZE + _TAIL.size for fmt, n in NUM_CARS.items()
}  # 2025: 1285, 2026: 1399


@dataclass(frozen=True)
class LapData:
    last_lap_time_ms: int
    current_lap_time_ms: int
    sector1_time_ms: int
    sector2_time_ms: int
    delta_to_car_in_front_ms: int
    delta_to_race_leader_ms: int
    lap_distance: float  # m od linii startu/mety; ujemny przed pierwszym przejazdem
    total_distance: float
    safety_car_delta: float
    car_position: int
    current_lap_num: int
    pit_status: int  # 0 brak, 1 pit lane, 2 w boksie
    num_pit_stops: int
    sector: int  # 0-2
    current_lap_invalid: bool
    penalties_s: int
    total_warnings: int
    corner_cutting_warnings: int
    num_unserved_drive_through_pens: int
    num_unserved_stop_go_pens: int
    grid_position: int
    driver_status: int  # 0 garaż, 1 flying lap, 2 in lap, 3 out lap, 4 na torze
    result_status: int
    pit_lane_timer_active: bool
    pit_lane_time_in_lane_ms: int
    pit_stop_timer_ms: int
    pit_stop_should_serve_pen: bool
    speed_trap_fastest_speed: float
    speed_trap_fastest_lap: int


@dataclass(frozen=True)
class LapDataPacket:
    header: PacketHeader
    cars: tuple[LapData, ...]
    time_trial_pb_car_idx: int  # 255 = brak
    time_trial_rival_car_idx: int  # 255 = brak

    @property
    def player(self) -> LapData:
        return self.cars[self.header.player_car_index]


def _with_minutes(ms_part: int, minutes_part: int) -> int:
    return minutes_part * 60_000 + ms_part


def _parse_car(data: bytes, offset: int) -> LapData:
    f = _CAR.unpack_from(data, offset)
    return LapData(
        last_lap_time_ms=f[0],
        current_lap_time_ms=f[1],
        sector1_time_ms=_with_minutes(f[2], f[3]),
        sector2_time_ms=_with_minutes(f[4], f[5]),
        delta_to_car_in_front_ms=_with_minutes(f[6], f[7]),
        delta_to_race_leader_ms=_with_minutes(f[8], f[9]),
        lap_distance=f[10], total_distance=f[11], safety_car_delta=f[12],
        car_position=f[13], current_lap_num=f[14], pit_status=f[15],
        num_pit_stops=f[16], sector=f[17], current_lap_invalid=bool(f[18]),
        penalties_s=f[19], total_warnings=f[20], corner_cutting_warnings=f[21],
        num_unserved_drive_through_pens=f[22], num_unserved_stop_go_pens=f[23],
        grid_position=f[24], driver_status=f[25], result_status=f[26],
        pit_lane_timer_active=bool(f[27]), pit_lane_time_in_lane_ms=f[28],
        pit_stop_timer_ms=f[29], pit_stop_should_serve_pen=bool(f[30]),
        speed_trap_fastest_speed=f[31], speed_trap_fastest_lap=f[32],
    )


def parse_lap_data(data: bytes) -> LapDataPacket:
    header = check_packet(data, PacketId.LAP_DATA, PACKET_SIZE)
    cars = tuple(_parse_car(data, HEADER_SIZE + i * CAR_SIZE) for i in range(header.num_cars))
    pb, rival = _TAIL.unpack_from(data, HEADER_SIZE + header.num_cars * CAR_SIZE)
    return LapDataPacket(header, cars, pb, rival)
