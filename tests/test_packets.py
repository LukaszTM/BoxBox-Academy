import struct

import pytest

from boxbox.telemetry.car_telemetry import CAR_SIZE as TEL_CAR, PACKET_SIZE as TEL_SIZE, parse_car_telemetry
from boxbox.telemetry.header import PacketHeader, PacketId, pack_header
from boxbox.telemetry.lap_data import CAR_SIZE as LAP_CAR, PACKET_SIZE as LAP_SIZE, parse_lap_data


def header(packet_id: PacketId, player: int = 3) -> bytes:
    return pack_header(PacketHeader(2025, 25, 1, 0, 1, int(packet_id), 1, 0.0, 0, 0, player, 255))


def test_sizes_match_spec() -> None:
    assert (TEL_CAR, TEL_SIZE, LAP_CAR, LAP_SIZE) == (60, 1352, 57, 1285)


def telemetry_packet() -> bytes:
    blank = bytes(TEL_CAR)
    player = struct.pack(
        "<HfffBbHBBH4H4B4BH4f4B",
        287, 0.75, -0.5, 0.25, 10, 6, 11500, 1, 80, 0x7FFF,
        400, 410, 420, 430, 90, 91, 92, 93, 100, 101, 102, 103, 105,
        23.5, 23.6, 22.0, 22.1, 0, 0, 1, 1,
    )
    assert len(player) == TEL_CAR
    cars = [blank] * 22
    cars[3] = player
    return header(PacketId.CAR_TELEMETRY) + b"".join(cars) + struct.pack("<BBb", 0, 255, 7)


def test_parse_car_telemetry() -> None:
    packet = parse_car_telemetry(telemetry_packet())
    car = packet.player
    assert (car.speed_kmh, car.gear, car.engine_rpm, car.drs) == (287, 6, 11500, True)
    assert (car.throttle, car.steer, car.brake) == (0.75, -0.5, 0.25)
    assert car.brakes_temperature == (400, 410, 420, 430)
    assert car.tyres_surface_temperature == (90, 91, 92, 93)
    assert car.tyres_inner_temperature == (100, 101, 102, 103)
    assert car.engine_temperature == 105
    assert car.tyres_pressure[0] == pytest.approx(23.5)
    assert car.surface_type == (0, 0, 1, 1)
    assert packet.suggested_gear == 7
    assert packet.cars[0].speed_kmh == 0


def lap_packet() -> bytes:
    blank = bytes(LAP_CAR)
    player = struct.pack(
        "<IIHBHBHBHBfffBBBBBBBBBBBBBBBHHBfB",
        83_123, 45_678, 1_234, 0, 20_000, 1, 300, 0, 1_500, 0,
        1234.5, 9999.0, 0.0,
        5, 3, 0, 1, 2, 1, 0, 0, 0, 0, 0, 7, 4, 2, 0,
        0, 0, 0, 312.5, 2,
    )
    assert len(player) == LAP_CAR
    cars = [blank] * 22
    cars[3] = player
    return header(PacketId.LAP_DATA) + b"".join(cars) + struct.pack("<BB", 255, 255)


def test_parse_lap_data() -> None:
    lap = parse_lap_data(lap_packet()).player
    assert (lap.last_lap_time_ms, lap.current_lap_time_ms) == (83_123, 45_678)
    assert lap.sector1_time_ms == 1_234
    assert lap.sector2_time_ms == 80_000  # 1 min + 20000 ms
    assert lap.delta_to_car_in_front_ms == 300
    assert lap.lap_distance == pytest.approx(1234.5)
    assert (lap.car_position, lap.current_lap_num, lap.sector) == (5, 3, 2)
    assert lap.current_lap_invalid is True
    assert (lap.grid_position, lap.driver_status, lap.result_status) == (7, 4, 2)
    assert lap.speed_trap_fastest_speed == pytest.approx(312.5)


@pytest.mark.parametrize("parse,data", [(parse_car_telemetry, lap_packet()), (parse_lap_data, telemetry_packet())])
def test_wrong_packet_type_rejected(parse, data) -> None:
    with pytest.raises(ValueError, match="to nie pakiet"):
        parse(data)


@pytest.mark.parametrize("parse,data", [(parse_car_telemetry, telemetry_packet()), (parse_lap_data, lap_packet())])
def test_wrong_length_rejected(parse, data) -> None:
    with pytest.raises(ValueError, match="długość"):
        parse(data[:-1])
