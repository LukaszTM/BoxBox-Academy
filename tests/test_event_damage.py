import struct

import pytest

from boxbox.telemetry import car_damage as cd
from boxbox.telemetry import event as ev
from boxbox.telemetry.header import PacketHeader, PacketId, pack_header
from boxbox.telemetry.state import TelemetryState


def header(packet_id: PacketId, player: int = 3) -> bytes:
    return pack_header(PacketHeader(2025, 25, 1, 0, 1, int(packet_id), 1, 0.0, 0, 0, player, 255))


def event_packet(code: str, details: bytes = b"") -> bytes:
    body = code.encode("ascii") + details
    return header(PacketId.EVENT) + body.ljust(ev.PACKET_SIZE - 29, b"\x00")


def test_sizes_match_spec() -> None:
    assert (ev.PACKET_SIZE, cd.CAR_SIZE, cd.PACKET_SIZE) == (45, 46, 1041)


def test_event_without_details() -> None:
    e = ev.parse_event(event_packet("CHQF"))
    assert (e.code, e.name, e.details) == ("CHQF", "flaga w szachownicę", None)


def test_unknown_event_code_is_kept() -> None:
    e = ev.parse_event(event_packet("XYZW"))
    assert (e.code, e.details) == ("XYZW", None)
    assert e.name == "zdarzenie XYZW"


@pytest.mark.parametrize(
    "code,details,expected",
    [
        ("FTLP", struct.pack("<Bf", 3, 83.456), ev.FastestLap(3, pytest.approx(83.456))),
        ("RTMT", struct.pack("<B", 7), ev.VehicleEvent(7)),
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
        ("COLL", struct.pack("<BB", 3, 12), ev.Collision(3, 12)),
    ],
)
def test_event_details(code: str, details: bytes, expected: object) -> None:
    e = ev.parse_event(event_packet(code, details))
    assert e.code == code
    assert e.details == expected


def damage_packet() -> bytes:
    blank = bytes(cd.CAR_SIZE)
    player = struct.pack(
        "<4f4B4B4B" + "B" * 6 + "BB" + "B" * 8 + "BB",
        12.5, 13.0, 20.25, 21.0,  # zużycie opon
        0, 0, 5, 5,  # uszkodzenia opon
        1, 1, 2, 2,  # hamulce
        0, 0, 3, 0,  # pęcherze
        10, 0, 0, 4, 0, 0,  # skrzydła, podłoga, dyfuzor, sidepod
        0, 1,  # DRS, ERS
        2, 3, 11, 12, 13, 14, 15, 16,  # skrzynia, silnik, zużycie podzespołów
        0, 0,
    )
    assert len(player) == cd.CAR_SIZE
    cars = [blank] * 22
    cars[3] = player
    return header(PacketId.CAR_DAMAGE) + b"".join(cars)


def test_parse_car_damage() -> None:
    packet = cd.parse_car_damage(damage_packet())
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


@pytest.mark.parametrize(
    "parse,data",
    [(ev.parse_event, damage_packet()), (cd.parse_car_damage, event_packet("SSTA"))],
)
def test_wrong_packet_type_rejected(parse, data) -> None:
    with pytest.raises(ValueError, match="to nie pakiet"):
        parse(data)


@pytest.mark.parametrize(
    "parse,data",
    [(ev.parse_event, event_packet("SSTA")), (cd.parse_car_damage, damage_packet())],
)
def test_wrong_length_rejected(parse, data) -> None:
    with pytest.raises(ValueError, match="długość"):
        parse(data[:-1])


def test_state_collects_events_and_damage() -> None:
    state = TelemetryState()
    state.feed(event_packet("SSTA"))
    state.feed(event_packet("PENA", struct.pack("<BBBBBBB", 5, 7, 3, 255, 3, 4, 0)))
    state.feed(damage_packet())
    state.feed(event_packet("SSTA")[:-1])  # uszkodzone zdarzenie
    assert [e.code for e in state.events] == ["SSTA", "PENA"]
    assert state.damage is not None and state.damage.player.floor_damage_percent == 4
    assert state.packets["EVENT"] == 3 and state.errors["EVENT"] == 1
