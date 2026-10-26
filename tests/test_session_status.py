import struct

import pytest

from boxbox.telemetry import car_status as cs
from boxbox.telemetry import session as ss
from boxbox.telemetry.header import PacketHeader, PacketId, pack_header


def header(packet_id: PacketId, player: int = 3) -> bytes:
    return pack_header(PacketHeader(2025, 25, 1, 0, 1, int(packet_id), 1, 0.0, 0, 0, player, 255))


def test_sizes_match_spec() -> None:
    assert (ss.PACKET_SIZE, cs.CAR_SIZE, cs.PACKET_SIZE) == (753, 55, 1239)


def session_packet() -> bytes:
    buf = bytearray(ss.PACKET_SIZE)
    buf[: len(header(PacketId.SESSION))] = header(PacketId.SESSION)
    ss.PREFIX.pack_into(
        buf, ss.PREFIX_OFFSET,
        3, 38, 29, 57, 5412, 18, 3, 0, 1799, 1800, 80, 0, 0, 255, 0, 21,
    )
    ss.MIDDLE.pack_into(buf, ss.MIDDLE_OFFSET, 2, 0, 0)
    rest = [
        0, 90,  # forecastAccuracy, aiDifficulty
        1, 2, 3,  # link ids
        12, 20, 7,  # okno pit-stopu
        0, 2, 3, 1, 0, 1, 1, 2, 1,  # asysty
        3, 0,  # gameMode, ruleSet
        14 * 60 + 30,  # timeOfDay
        2, 0, 0, 0, 0,  # sessionLength, jednostki
        1, 0, 0,  # SC, VSC, red flag
        *([0] * 24),
        1, *([0] * 12),
        1800.5, 3900.25,
    ]
    ss.REST.pack_into(buf, ss.REST_OFFSET, *rest)
    return bytes(buf)


def test_parse_session() -> None:
    s = ss.parse_session(session_packet())
    assert (s.weather, s.track_temperature, s.air_temperature) == (3, 38, 29)
    assert (s.total_laps, s.track_length_m, s.pit_speed_limit_kmh) == (57, 5412, 80)
    assert (s.session_type, s.track_id) == (18, 3)
    assert (s.track_name, s.session_type_name, s.weather_name) == ("Bahrajn", "time trial", "lekki deszcz")
    assert (s.session_time_left_s, s.session_duration_s) == (1799, 1800)
    assert s.safety_car_status == 2
    assert (s.pit_stop_window_ideal_lap, s.pit_stop_window_latest_lap, s.pit_stop_rejoin_position) == (12, 20, 7)
    a = s.assists
    assert (a.steering, a.braking, a.gearbox, a.pit) == (False, 2, 3, True)
    assert (a.pit_release, a.ers, a.drs) == (False, True, True)
    assert (a.dynamic_racing_line, a.dynamic_racing_line_type) == (2, 1)
    assert (s.game_mode, s.time_of_day_min, s.session_length) == (3, 870, 2)
    assert s.sector2_lap_distance_start == pytest.approx(1800.5)
    assert s.sector3_lap_distance_start == pytest.approx(3900.25)


def test_reverse_track_name() -> None:
    buf = bytearray(session_packet())
    buf[ss.PREFIX_OFFSET + 7] = 41
    assert ss.parse_session(bytes(buf)).track_name == "Zandvoort (odwrotny)"


def test_unknown_track_has_fallback_name() -> None:
    buf = bytearray(session_packet())
    buf[ss.PREFIX_OFFSET + 7] = 99  # trackId: za weather, 2 temp., totalLaps i 2-bajtowym trackLength
    assert ss.parse_session(bytes(buf)).track_name == "tor 99"


def status_packet() -> bytes:
    blank = bytes(cs.CAR_SIZE)
    player = struct.pack(
        "<BBBBBfffHHBBHBBBbfffBfffB",
        1, 1, 2, 56, 0, 42.5, 110.0, 18.3, 13000, 3500, 8, 1, 250,
        18, 17, 4, 0, 300000.0, 120000.0, 3_000_000.0, 1,
        150000.0, 50000.0, 900000.0, 0,
    )
    assert len(player) == cs.CAR_SIZE
    cars = [blank] * 22
    cars[3] = player
    return header(PacketId.CAR_STATUS) + b"".join(cars)


def test_parse_car_status() -> None:
    packet = cs.parse_car_status(status_packet())
    c = packet.player
    assert (c.traction_control, c.anti_lock_brakes, c.fuel_mix, c.front_brake_bias_percent) == (1, True, 2, 56)
    assert c.pit_limiter_on is False
    assert (c.fuel_in_tank_kg, c.fuel_capacity_kg, c.fuel_remaining_laps) == (42.5, 110.0, pytest.approx(18.3))
    assert (c.max_rpm, c.idle_rpm, c.max_gears) == (13000, 3500, 8)
    assert (c.drs_allowed, c.drs_activation_distance_m) == (True, 250)
    assert (c.actual_tyre_compound, c.visual_tyre_compound, c.tyres_age_laps) == (18, 17, 4)
    assert c.visual_tyre_name == "medium"
    assert c.ers_store_energy_j == 3_000_000.0
    assert c.ers_store_percent == pytest.approx(75.0)
    assert (c.ers_deploy_mode, c.ers_deploy_mode_name) == (1, "medium")
    assert c.ers_deployed_this_lap_j == 900000.0
    assert packet.cars[0].max_rpm == 0


@pytest.mark.parametrize(
    "parse,data",
    [(ss.parse_session, status_packet()), (cs.parse_car_status, session_packet())],
)
def test_wrong_packet_type_rejected(parse, data) -> None:
    with pytest.raises(ValueError, match="to nie pakiet"):
        parse(data)


@pytest.mark.parametrize(
    "parse,data",
    [(ss.parse_session, session_packet()), (cs.parse_car_status, status_packet())],
)
def test_wrong_length_rejected(parse, data) -> None:
    with pytest.raises(ValueError, match="długość"):
        parse(data + b"\x00")
