import struct

import pytest

from boxbox.telemetry import car_damage as cd
from boxbox.telemetry import car_telemetry2 as ct2
from boxbox.telemetry import event as ev
from boxbox.telemetry.header import NUM_CARS, PacketId
from boxbox.telemetry.state import TelemetryState
from tests.builders import FORMATS, damage_packet, event_packet, telemetry2_packet


def test_sizes_match_spec() -> None:
    assert ev.PACKET_SIZE == {2025: 45, 2026: 45}
    assert cd.PACKET_SIZE == {2025: 1041, 2026: 1133}
    assert ct2.PACKET_SIZE == {2026: 269}


@pytest.mark.parametrize("fmt", FORMATS)
def test_event_without_details(fmt: int) -> None:
    e = ev.parse_event(event_packet("CHQF", fmt=fmt))
    assert (e.code, e.name, e.details) == ("CHQF", "flaga w szachownicę", None)


def test_unknown_event_code_is_kept() -> None:
    e = ev.parse_event(event_packet("XYZW"))
    assert (e.code, e.details) == ("XYZW", None)
    assert e.name == "zdarzenie XYZW"


@pytest.mark.parametrize(
    "code,details,expected",
    [
        ("FTLP", struct.pack("<Bf", 3, 83.456), ev.FastestLap(3, pytest.approx(83.456))),
        ("RTMT", struct.pack("<BB", 7, 8), ev.Retirement(7, 8)),
        ("DRSD", struct.pack("<B", 1), ev.DrsDisabled(1)),
        ("TMPT", struct.pack("<B", 7), ev.VehicleEvent(7)),
        ("SGSV", struct.pack("<Bf", 3, 10.0), ev.StopGoServed(3, 10.0)),
        ("PENA", struct.pack("<BBBBBBB", 5, 7, 3, 255, 3, 4, 0), ev.Penalty(5, 7, 3, 255, 3, 4, 0)),
        (
            "SPTP",
            struct.pack("<BfBBBf", 3, 321.5, 1, 1, 3, 321.5),
            ev.SpeedTrap(3, pytest.approx(321.5), True, True, 3, pytest.approx(321.5)),
        ),
        ("STLG", struct.pack("<B", 4), ev.StartLights(4)),
        ("FLBK", struct.pack("<If", 12345, 67.5), ev.Flashback(12345, 67.5)),
        ("BUTN", struct.pack("<I", 0x0001), ev.Buttons(1)),
        ("OVTK", struct.pack("<BB", 3, 9), ev.Overtake(3, 9)),
        ("SCAR", struct.pack("<BB", 2, 0), ev.SafetyCar(2, 0)),
        ("COLL", struct.pack("<BB", 3, 12), ev.Collision(3, 12, None)),
    ],
)
def test_event_details(code: str, details: bytes, expected: object) -> None:
    e = ev.parse_event(event_packet(code, details))
    assert e.code == code
    assert e.details == expected


def test_collision_2026_has_severity() -> None:
    e = ev.parse_event(event_packet("COLL", struct.pack("<BBB", 3, 12, 2), fmt=2026))
    assert e.details == ev.Collision(3, 12, 2)


@pytest.mark.parametrize("fmt", FORMATS)
def test_parse_car_damage(fmt: int) -> None:
    packet = cd.parse_car_damage(damage_packet(fmt))
    assert len(packet.cars) == NUM_CARS[fmt]
    c = packet.player
    assert c.tyres_wear_percent == pytest.approx((12.5, 13.0, 20.25, 21.0))
    assert c.tyres_damage_percent == (0, 0, 5, 5)
    assert c.brakes_damage_percent == (1, 1, 2, 2)
    assert c.tyre_blisters_percent == (0, 0, 3, 0)
    assert (c.front_left_wing_damage_percent, c.floor_damage_percent) == (10, 4)
    assert (c.drs_fault, c.ers_fault) == (False, True)
    assert (c.gearbox_damage_percent, c.engine_damage_percent) == (2, 3)
    assert (c.engine_mguh_wear_percent, c.engine_tc_wear_percent) == (11, 16)
    assert (c.engine_blown, c.engine_seized) == (False, False)
    assert c.has_aero_damage is True
    assert packet.cars[0].has_aero_damage is False


def test_parse_car_telemetry2() -> None:
    packet = ct2.parse_car_telemetry2(telemetry2_packet())
    assert len(packet.cars) == 24
    c = packet.player
    assert (c.active_aero_mode, c.active_aero_available, c.active_aero_activation_distance_m) == (1, True, 0)
    assert (c.overtake_available, c.overtake_active, c.overtake_activation_distance_m) == (True, False, 120)
    assert (c.regulations_2026, c.driving_wrong_way) == (True, False)


def test_car_telemetry2_only_in_2026() -> None:
    data = bytearray(telemetry2_packet())
    data[0:2] = (2025).to_bytes(2, "little")
    with pytest.raises(ValueError, match="nieobsługiwany format"):
        ct2.parse_car_telemetry2(bytes(data))


@pytest.mark.parametrize(
    "parse,data",
    [(ev.parse_event, damage_packet()), (cd.parse_car_damage, event_packet("SSTA"))],
)
def test_wrong_packet_type_rejected(parse, data) -> None:
    with pytest.raises(ValueError, match="to nie pakiet"):
        parse(data)


@pytest.mark.parametrize("fmt", FORMATS)
def test_wrong_length_rejected(fmt: int) -> None:
    with pytest.raises(ValueError, match="długość"):
        ev.parse_event(event_packet("SSTA", fmt=fmt)[:-1])
    with pytest.raises(ValueError, match="długość"):
        cd.parse_car_damage(damage_packet(fmt)[:-1])


def test_state_counts_formats_and_rejects_unknown() -> None:
    state = TelemetryState()
    state.feed(damage_packet(2025))
    state.feed(damage_packet(2026))
    old = bytearray(damage_packet())
    old[0:2] = (2024).to_bytes(2, "little")
    state.feed(bytes(old))
    assert state.formats == {2025: 1, 2026: 1, 2024: 1}
    assert state.unsupported_formats == {2024: 1}
    assert state.packets["CAR_DAMAGE"] == 3 and not state.errors
    assert state.damage is not None and state.damage.header.packet_format == 2026


def test_state_collects_events_damage_and_telemetry2() -> None:
    state = TelemetryState()
    state.feed(event_packet("SSTA"))
    state.feed(event_packet("PENA", struct.pack("<BBBBBBB", 5, 7, 3, 255, 3, 4, 0)))
    state.feed(damage_packet())
    state.feed(telemetry2_packet())
    state.feed(event_packet("SSTA")[:-1])  # uszkodzone zdarzenie
    assert [e.code for e in state.events] == ["SSTA", "PENA"]
    assert state.damage is not None and state.damage.player.floor_damage_percent == 4
    assert state.telemetry2 is not None and state.telemetry2.player.overtake_available
    assert state.packets["EVENT"] == 3 and state.errors["EVENT"] == 1
    assert state.packets[PacketId.CAR_TELEMETRY_2.name] == 1
