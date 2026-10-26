"""Pakiet Car Status (id 7): TC, ABS, paliwo, opony, ERS.

Układ zgodny z docs/F1_25_Telemetry_Output_Structures.txt (2025)
i docs/2026_Season_Pack_Telemetry_Output_Structures.txt (2026).
Różnica w 2026: dodatkowe pole ersHarvestLimitPerLap (59 B zamiast 55 B na auto)
i 24 auta; tryb ERS 3 nazywa się tam "boost" zamiast "overtake".
"""
import struct
from dataclasses import dataclass

from boxbox.telemetry.header import HEADER_SIZE, NUM_CARS, PacketHeader, PacketId, check_packet

_CAR: dict[int, struct.Struct] = {
    2025: struct.Struct("<BBBBBfffHHBBHBBBbfffBfffB"),  # 55 B
    2026: struct.Struct("<BBBBBfffHHBBHBBBbfffBffffB"),  # 59 B
}
PACKET_SIZE: dict[int, int] = {
    fmt: HEADER_SIZE + NUM_CARS[fmt] * _CAR[fmt].size for fmt in _CAR
}  # 2025: 1239, 2026: 1445

ERS_MAX_STORE_J = 4_000_000.0  # pełna bateria wg specyfikacji EA

TYRE_COMPOUND_NAMES: dict[int, str] = {
    16: "C5", 17: "C4", 18: "C3", 19: "C2", 20: "C1", 21: "C0", 22: "C6",
    7: "inter", 8: "wet",
}
VISUAL_TYRE_NAMES: dict[int, str] = {16: "soft", 17: "medium", 18: "hard", 7: "inter", 8: "wet"}
ERS_DEPLOY_MODE_NAMES: dict[int, str] = {0: "brak", 1: "medium", 2: "hotlap", 3: "overtake"}


@dataclass(frozen=True)
class CarStatus:
    traction_control: int  # 0 wył., 1 średnia, 2 pełna
    anti_lock_brakes: bool
    fuel_mix: int  # 0 lean, 1 standard, 2 rich, 3 max
    front_brake_bias_percent: int
    pit_limiter_on: bool
    fuel_in_tank_kg: float
    fuel_capacity_kg: float
    fuel_remaining_laps: float
    max_rpm: int
    idle_rpm: int
    max_gears: int
    drs_allowed: bool
    drs_activation_distance_m: int  # 0 = DRS niedostępny
    actual_tyre_compound: int
    visual_tyre_compound: int
    tyres_age_laps: int
    vehicle_fia_flags: int  # -1 nieznana, 0 brak, 1 zielona, 2 niebieska, 3 żółta
    engine_power_ice_w: float
    engine_power_mguk_w: float
    ers_store_energy_j: float
    ers_deploy_mode: int
    ers_harvested_this_lap_mguk_j: float
    ers_harvested_this_lap_mguh_j: float
    ers_deployed_this_lap_j: float
    network_paused: bool
    ers_harvest_limit_per_lap_j: float | None = None  # tylko format 2026

    @property
    def ers_store_percent(self) -> float:
        return 100.0 * self.ers_store_energy_j / ERS_MAX_STORE_J

    @property
    def visual_tyre_name(self) -> str:
        return VISUAL_TYRE_NAMES.get(self.visual_tyre_compound, f"opona {self.visual_tyre_compound}")

    @property
    def ers_deploy_mode_name(self) -> str:
        return ERS_DEPLOY_MODE_NAMES.get(self.ers_deploy_mode, f"tryb {self.ers_deploy_mode}")


@dataclass(frozen=True)
class CarStatusPacket:
    header: PacketHeader
    cars: tuple[CarStatus, ...]

    @property
    def player(self) -> CarStatus:
        return self.cars[self.header.player_car_index]


def _parse_car(packet_format: int, data: bytes, offset: int) -> CarStatus:
    f = _CAR[packet_format].unpack_from(data, offset)
    if packet_format == 2026:
        harvest_limit, deployed, paused = f[23], f[24], f[25]
    else:
        harvest_limit, deployed, paused = None, f[23], f[24]
    return CarStatus(
        traction_control=f[0], anti_lock_brakes=bool(f[1]), fuel_mix=f[2],
        front_brake_bias_percent=f[3], pit_limiter_on=bool(f[4]), fuel_in_tank_kg=f[5],
        fuel_capacity_kg=f[6], fuel_remaining_laps=f[7], max_rpm=f[8], idle_rpm=f[9],
        max_gears=f[10], drs_allowed=bool(f[11]), drs_activation_distance_m=f[12],
        actual_tyre_compound=f[13], visual_tyre_compound=f[14], tyres_age_laps=f[15],
        vehicle_fia_flags=f[16], engine_power_ice_w=f[17], engine_power_mguk_w=f[18],
        ers_store_energy_j=f[19], ers_deploy_mode=f[20], ers_harvested_this_lap_mguk_j=f[21],
        ers_harvested_this_lap_mguh_j=f[22], ers_deployed_this_lap_j=deployed,
        network_paused=bool(paused), ers_harvest_limit_per_lap_j=harvest_limit,
    )


def parse_car_status(data: bytes) -> CarStatusPacket:
    header = check_packet(data, PacketId.CAR_STATUS, PACKET_SIZE)
    size = _CAR[header.packet_format].size
    cars = tuple(
        _parse_car(header.packet_format, data, HEADER_SIZE + i * size)
        for i in range(header.num_cars)
    )
    return CarStatusPacket(header, cars)
