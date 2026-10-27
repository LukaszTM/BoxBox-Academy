"""Budowanie pakietów testowych w formacie 2025 i 2026 (wartości dla auta gracza nr 3)."""
import struct

from boxbox.telemetry import car_damage as cd
from boxbox.telemetry import car_status as cs
from boxbox.telemetry import car_telemetry as ct
from boxbox.telemetry import car_telemetry2 as ct2
from boxbox.telemetry import event as ev
from boxbox.telemetry import lap_data as ld
from boxbox.telemetry import participants as pp
from boxbox.telemetry import session as ss
from boxbox.telemetry.header import NUM_CARS, PacketHeader, PacketId, pack_header

FORMATS = (2025, 2026)
PLAYER = 3


def header_bytes(packet_id: PacketId, fmt: int = 2025, player: int = PLAYER) -> bytes:
    year = fmt - 2000
    return pack_header(PacketHeader(fmt, year, 1, 0, 1, int(packet_id), 1, 0.0, 0, 0, player, 255))


RIVAL = 5


def _cars_packet(
    packet_id: PacketId, fmt: int, car_size: int, player_car: bytes, tail: bytes = b"",
    others: dict[int, bytes] | None = None,
) -> bytes:
    assert len(player_car) == car_size
    cars = [bytes(car_size)] * NUM_CARS[fmt]
    cars[PLAYER] = player_car
    for idx, car in (others or {}).items():
        assert len(car) == car_size
        cars[idx] = car
    return header_bytes(packet_id, fmt) + b"".join(cars) + tail


def _telemetry_car(fmt: int, speed: int, throttle: float, brake: float, gear: int) -> bytes:
    engine_temp = "H" if fmt == 2025 else "B"
    return struct.pack(
        "<HfffBbHBBH4H4B4B" + engine_temp + "4f4B",
        speed, throttle, -0.5, brake, 10, gear, 11500, 1, 80, 0x7FFF,
        400, 410, 420, 430, 90, 91, 92, 93, 100, 101, 102, 103, 105,
        23.5, 23.6, 22.0, 22.1, 0, 0, 1, 1,
    )


def telemetry_packet(
    fmt: int = 2025, speed: int = 287, throttle: float = 0.75, brake: float = 0.25, gear: int = 6,
    rival: tuple[int, float, float, int] | None = None,
) -> bytes:
    """rival = (prędkość, gaz, hamulec, bieg) dla auta RIVAL."""
    player = _telemetry_car(fmt, speed, throttle, brake, gear)
    others = {RIVAL: _telemetry_car(fmt, *rival)} if rival else None
    return _cars_packet(PacketId.CAR_TELEMETRY, fmt, len(player), player, struct.pack("<BBb", 0, 255, 7), others)


def _lap_car(
    lap_distance: float, lap_num: int, pit_status: int, lap_invalid: bool, current_lap_time_ms: int,
    last_lap_time_ms: int = 83_123,
) -> bytes:
    return struct.pack(
        "<IIHBHBHBHBfffBBBBBBBBBBBBBBBHHBfB",
        last_lap_time_ms, current_lap_time_ms, 1_234, 0, 20_000, 1, 300, 0, 1_500, 0,
        lap_distance, 9999.0, 0.0,
        5, lap_num, pit_status, 1, 2, int(lap_invalid), 0, 0, 0, 0, 0, 7, 4, 2, 0,
        0, 0, 0, 312.5, 2,
    )


def lap_packet(
    fmt: int = 2025, lap_distance: float = 1234.5, lap_num: int = 3, pit_status: int = 0,
    lap_invalid: bool = True, current_lap_time_ms: int = 45_678,
    rival: tuple[float, int, int] | None = None,
) -> bytes:
    """rival = (dystans, czas okrążenia ms, czas ostatniego okrążenia ms) ducha pod indeksem RIVAL."""
    player = _lap_car(lap_distance, lap_num, pit_status, lap_invalid, current_lap_time_ms)
    others = {RIVAL: _lap_car(rival[0], 2, 0, False, rival[1], rival[2])} if rival else None
    tail = struct.pack("<BB", 255, RIVAL if rival else 255)
    return _cars_packet(PacketId.LAP_DATA, fmt, ld.CAR_SIZE, player, tail, others)


def participants_packet(fmt: int = 2025, names: dict[int, str] | None = None) -> bytes:
    layout = "<BBBBBBB32sBBHBB" + "BBB" * 4 if fmt == 2025 else "<BHHHBBB32sBBHBB" + "BBB" * 4
    names = names or {PLAYER: "Gracz", RIVAL: "Jarno Opmeer"}
    cars = []
    for i in range(NUM_CARS[fmt]):
        name = names.get(i, "").encode("utf-8")
        cars.append(struct.pack(layout, 0 if i in names else 1, 7, 0, 2, 0, 44, 63, name, 1, 1, 0, 1, 2, 255, 0, 0, 0, 0, 255, 0, 0, 0, 0, 0, 0))
    return header_bytes(PacketId.PARTICIPANTS, fmt) + struct.pack("<B", len(names)) + b"".join(cars)


def status_packet(fmt: int = 2025) -> bytes:
    common = [
        1, 1, 2, 56, 0, 42.5, 110.0, 18.3, 13000, 3500, 8, 1, 250,
        18, 17, 4, 0, 300000.0, 120000.0, 3_000_000.0, 1, 150000.0, 50000.0,
    ]
    if fmt == 2025:
        player = struct.pack("<BBBBBfffHHBBHBBBbfffBfffB", *common, 900000.0, 0)
    else:
        player = struct.pack("<BBBBBfffHHBBHBBBbfffBffffB", *common, 2_000_000.0, 900000.0, 0)
    return _cars_packet(PacketId.CAR_STATUS, fmt, len(player), player)


def damage_packet(fmt: int = 2025) -> bytes:
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
    return _cars_packet(PacketId.CAR_DAMAGE, fmt, cd.CAR_SIZE, player)


def telemetry2_packet() -> bytes:
    player = struct.pack("<BBHBBHBB", 1, 1, 0, 1, 0, 120, 1, 0)
    return _cars_packet(PacketId.CAR_TELEMETRY_2, 2026, ct2.CAR_SIZE, player)


def session_packet(fmt: int = 2025) -> bytes:
    buf = bytearray(ss.PACKET_SIZE[fmt])
    h = header_bytes(PacketId.SESSION, fmt)
    buf[: len(h)] = h
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
    if fmt == 2026:
        extra = [
            0, 0, *([0.0] * 16),  # aktywne aero (pełne): brak stref
            0, *([0.0] * 16),  # aktywne aero (częściowe): brak
            2, 0.10, 0.25, 0.60, 0.72, 0.0, 0.0, 0.0, 0.0,  # 2 strefy DRS
            0.213,  # czas reakcji na starcie
            1, 2, 0, 0, 1,  # ABS wł., TC pełna, hi-vis, daltonizm, rewind
        ]
        ss.EXTRA_2026.pack_into(buf, ss.EXTRA_OFFSET, *extra)
    return bytes(buf)


def event_packet(code: str, details: bytes = b"", fmt: int = 2025) -> bytes:
    body = code.encode("ascii") + details
    return header_bytes(PacketId.EVENT, fmt) + body.ljust(ev.PACKET_SIZE[fmt] - 29, b"\x00")


def motion_packet(fmt: int = 2025, x: float = 0.0, z: float = 0.0, yaw: float = 0.0, y: float = 1.0) -> bytes:
    if fmt == 2025:
        player = struct.pack("<6f6h6f", x, y, z, 0.0, 0.0, 0.0, 0, 0, 0, 0, 0, 0, 0.1, 0.2, 0.3, yaw, 0.0, 0.0)
    else:
        player = struct.pack("<6f9h3f", x, y, z, 0.0, 0.0, 0.0, 0, 0, 0, 0, 0, 0, 1, 2, 3, yaw, 0.0, 0.0)
    return _cars_packet(PacketId.MOTION, fmt, len(player), player)
