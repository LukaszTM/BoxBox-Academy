import pytest

from boxbox.telemetry import car_status as cs
from boxbox.telemetry import session as ss
from boxbox.telemetry.header import NUM_CARS
from tests.builders import FORMATS, session_packet, status_packet


def test_sizes_match_spec() -> None:
    assert ss.PACKET_SIZE == {2025: 753, 2026: 926}
    assert cs.PACKET_SIZE == {2025: 1239, 2026: 1445}


@pytest.mark.parametrize("fmt", FORMATS)
def test_parse_session(fmt: int) -> None:
    s = ss.parse_session(session_packet(fmt))
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


def test_session_2025_has_no_extra_fields() -> None:
    s = ss.parse_session(session_packet(2025))
    assert (s.assists.traction_control, s.assists.anti_lock_brakes) == (None, None)
    assert s.drs_zones == () and s.start_reaction_time_s is None


def test_session_2026_extra_fields() -> None:
    s = ss.parse_session(session_packet(2026))
    assert (s.assists.traction_control, s.assists.anti_lock_brakes) == (2, True)
    assert s.assists.gearbox == 3  # pola wspólne bez zmian
    assert s.drs_zones == (
        (pytest.approx(0.10), pytest.approx(0.25)),
        (pytest.approx(0.60), pytest.approx(0.72)),
    )
    assert s.start_reaction_time_s == pytest.approx(0.213)


def test_reverse_track_name() -> None:
    buf = bytearray(session_packet())
    buf[ss.PREFIX_OFFSET + 7] = 41
    assert ss.parse_session(bytes(buf)).track_name == "Zandvoort (odwrotny)"


def test_unknown_track_has_fallback_name() -> None:
    buf = bytearray(session_packet())
    buf[ss.PREFIX_OFFSET + 7] = 99  # trackId: za weather, 2 temp., totalLaps i 2-bajtowym trackLength
    assert ss.parse_session(bytes(buf)).track_name == "tor 99"


@pytest.mark.parametrize("fmt", FORMATS)
def test_parse_car_status(fmt: int) -> None:
    packet = cs.parse_car_status(status_packet(fmt))
    assert len(packet.cars) == NUM_CARS[fmt]
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
    assert c.ers_harvested_this_lap_mguh_j == 50000.0
    assert c.ers_deployed_this_lap_j == 900000.0
    assert c.network_paused is False
    assert c.ers_harvest_limit_per_lap_j == (None if fmt == 2025 else 2_000_000.0)
    assert packet.cars[0].max_rpm == 0


@pytest.mark.parametrize(
    "parse,data",
    [(ss.parse_session, status_packet()), (cs.parse_car_status, session_packet())],
)
def test_wrong_packet_type_rejected(parse, data) -> None:
    with pytest.raises(ValueError, match="to nie pakiet"):
        parse(data)


@pytest.mark.parametrize("fmt", FORMATS)
@pytest.mark.parametrize("parse,build", [(ss.parse_session, session_packet), (cs.parse_car_status, status_packet)])
def test_wrong_length_rejected(parse, build, fmt: int) -> None:
    with pytest.raises(ValueError, match="długość"):
        parse(build(fmt) + b"\x00")
