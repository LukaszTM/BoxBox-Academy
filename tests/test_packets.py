import pytest

from boxbox.telemetry import car_telemetry as ct
from boxbox.telemetry import lap_data as ld
from boxbox.telemetry.car_telemetry import parse_car_telemetry
from boxbox.telemetry.header import NUM_CARS
from boxbox.telemetry.lap_data import parse_lap_data
from tests.builders import FORMATS, lap_packet, telemetry_packet


def test_sizes_match_spec() -> None:
    assert ct.PACKET_SIZE == {2025: 1352, 2026: 1448}
    assert ld.PACKET_SIZE == {2025: 1285, 2026: 1399}


@pytest.mark.parametrize("fmt", FORMATS)
def test_parse_car_telemetry(fmt: int) -> None:
    packet = parse_car_telemetry(telemetry_packet(fmt))
    assert len(packet.cars) == NUM_CARS[fmt]
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


@pytest.mark.parametrize("fmt", FORMATS)
def test_parse_lap_data(fmt: int) -> None:
    packet = parse_lap_data(lap_packet(fmt))
    assert len(packet.cars) == NUM_CARS[fmt]
    assert (packet.time_trial_pb_car_idx, packet.time_trial_rival_car_idx) == (255, 255)
    lap = packet.player
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


@pytest.mark.parametrize("fmt", FORMATS)
@pytest.mark.parametrize("parse,build", [(parse_car_telemetry, telemetry_packet), (parse_lap_data, lap_packet)])
def test_wrong_length_rejected(parse, build, fmt: int) -> None:
    with pytest.raises(ValueError, match="długość"):
        parse(build(fmt)[:-1])


def test_unknown_format_rejected() -> None:
    data = bytearray(telemetry_packet())
    data[0:2] = (2024).to_bytes(2, "little")
    with pytest.raises(ValueError, match="nieobsługiwany format"):
        parse_car_telemetry(bytes(data))
