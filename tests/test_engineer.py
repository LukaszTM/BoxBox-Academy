"""Inżynier na radiu: reguły na syntetycznych pakietach i na nagraniu (tryb race nie wywraca sesji)."""
import struct
from pathlib import Path

from boxbox.engineer.rules import Engineer, laps_clip, seconds_clip
from boxbox.telemetry import session as ss
from boxbox.telemetry.header import NUM_CARS, PacketId
from boxbox.telemetry.state import TelemetryState
from tests.builders import PLAYER, _cars_packet, event_packet, header_bytes, session_packet, telemetry_packet


def race_session(session_type: int = 15, total_laps: int = 10, sc: int = 0, weather: int = 0, pit_ideal: int = 5, pit_latest: int = 8) -> bytes:
    buf = bytearray(session_packet())
    ss.PREFIX.pack_into(buf, ss.PREFIX_OFFSET, weather, 38, 29, total_laps, 5412, session_type, 3, 0, 1799, 1800, 80, 0, 0, 255, 0, 21)
    ss.MIDDLE.pack_into(buf, ss.MIDDLE_OFFSET, sc, 0, 0)
    rest = list(ss.REST.unpack_from(buf, ss.REST_OFFSET))
    rest[5], rest[6] = pit_ideal, pit_latest
    ss.REST.pack_into(buf, ss.REST_OFFSET, *rest)
    return bytes(buf)


def lap_car(lap_num: int = 2, position: int = 5, gap_ahead_ms: int = 2500, warnings: int = 0, pits: int = 0, distance: float = 1000.0) -> bytes:
    return struct.pack(
        "<IIHBHBHBHBfffBBBBBBBBBBBBBBBHHBfB",
        83_123, 40_000, 1_234, 0, 20_000, 1, gap_ahead_ms % 60000, gap_ahead_ms // 60000, 1_500, 0,
        distance, 9999.0, 0.0,
        position, lap_num, 0, pits, 2, 0, 0, warnings, 0, 0, 0, 7, 4, 2, 0,
        0, 0, 0, 312.5, 2,
    )


def lap_packet_race(lap_num: int = 2, position: int = 5, gap_ahead_ms: int = 2500, warnings: int = 0, behind_gap_ms: int | None = None, pits: int = 0) -> bytes:
    others = {}
    if behind_gap_ms is not None:
        others[PLAYER + 1] = lap_car(lap_num, position + 1, behind_gap_ms)
    tail = struct.pack("<BB", 255, 255)
    return _cars_packet(PacketId.LAP_DATA, 2025, 57, lap_car(lap_num, position, gap_ahead_ms, warnings, pits), tail, others)


def status_race(fia_flag: int = 0, drs_allowed: int = 0, fuel_laps: float = 0.5, tyre_age: int = 3) -> bytes:
    common = [1, 1, 2, 56, 0, 42.5, 110.0, fuel_laps, 13000, 3500, 8, drs_allowed, 250, 18, 17, tyre_age, fia_flag,
              300000.0, 120000.0, 3_000_000.0, 1, 150000.0, 50000.0]
    player = struct.pack("<BBBBBfffHHBBHBBBbfffBfffB", *common, 900000.0, 0)
    return _cars_packet(PacketId.CAR_STATUS, 2025, len(player), player)


def damage_race(wear: tuple[float, float, float, float] = (10, 10, 10, 10), fl_wing: int = 0, floor: int = 0, engine: int = 0, tyre_dmg: tuple[int, int, int, int] = (0, 0, 0, 0)) -> bytes:
    player = struct.pack(
        "<4f4B4B4B" + "B" * 6 + "BB" + "B" * 8 + "BB",
        *wear, *tyre_dmg, 1, 1, 2, 2, 0, 0, 3, 0, fl_wing, 0, 0, floor, 0, 0, 0, 1, 2, engine, 11, 12, 13, 14, 15, 16, 0, 0,
    )
    return _cars_packet(PacketId.CAR_DAMAGE, 2025, 46, player)


def feed(eng: Engineer, state: TelemetryState, packets: list[bytes], now: float) -> list[str]:
    for p in packets:
        state.feed(p)
    return [m.key for m in eng.update(state, now)]


def test_hello_flags_drs_and_cooldowns() -> None:
    eng, st = Engineer(), TelemetryState()
    assert feed(eng, st, [race_session(), lap_packet_race(1, 5), status_race(), telemetry_packet()], 0.0) == ["hello"]
    assert feed(eng, st, [status_race(fia_flag=3)], 1.0) == ["flag_yellow"]
    assert feed(eng, st, [status_race(fia_flag=3)], 2.0) == []  # bez zmiany: cisza
    assert feed(eng, st, [status_race(fia_flag=1)], 3.0) == ["flag_yellow_clear"]
    assert feed(eng, st, [status_race(fia_flag=2)], 4.0) == ["flag_blue"]
    assert feed(eng, st, [status_race(fia_flag=0, drs_allowed=1)], 5.0) == ["drs_enabled"]
    assert feed(eng, st, [event_packet("DRSD", b"\x00")], 6.0) == ["drs_disabled"]
    assert feed(eng, st, [event_packet("DRSE")], 7.0) == []  # cooldown 30 s po "drs_enabled"
    assert feed(eng, st, [event_packet("DRSE")], 70.0) == ["drs_enabled"]


def test_safety_car_lights_and_race_end() -> None:
    eng, st = Engineer(), TelemetryState()
    feed(eng, st, [race_session(), lap_packet_race(1, 5), status_race()], 0.0)
    assert feed(eng, st, [event_packet("STLG", b"\x03")], 1.0) == ["formation_lap"]
    assert feed(eng, st, [event_packet("LGOT")], 2.0) == ["lights_out"]
    assert feed(eng, st, [event_packet("SCAR", b"\x01\x00")], 10.0) == ["safety_car"]
    assert feed(eng, st, [race_session(sc=1)], 11.0) == []  # stan sesji potwierdza to samo: bez powtórki
    assert feed(eng, st, [event_packet("SCAR", b"\x01\x01")], 40.0) == ["safety_car_in"]
    assert feed(eng, st, [race_session(sc=2)], 80.0) == ["vsc"]
    assert feed(eng, st, [race_session(sc=0)], 120.0) == ["vsc_end"]
    assert feed(eng, st, [event_packet("RDFL")], 130.0) == ["flag_red"]
    assert feed(eng, st, [event_packet("CHQF")], 200.0) == ["race_end"]
    assert feed(eng, st, [event_packet("SEND")], 201.0) == []


def test_pit_window_last_laps_positions_and_gaps() -> None:
    eng, st = Engineer(), TelemetryState()
    feed(eng, st, [race_session(total_laps=10, pit_ideal=5, pit_latest=8), lap_packet_race(1, 5), status_race()], 0.0)
    assert feed(eng, st, [lap_packet_race(2, 5, gap_ahead_ms=800, behind_gap_ms=5000)], 10.0) == ["gap_ahead_close"]  # gap_safe dopiero od 3. okrążenia
    assert feed(eng, st, [lap_packet_race(3, 4, gap_ahead_ms=2500, behind_gap_ms=5000)], 20.0) == ["position_gained", "gap_ahead", "gap_safe"]
    assert feed(eng, st, [lap_packet_race(4, 6, gap_ahead_ms=2500, behind_gap_ms=600)], 40.0) == ["position_lost", "gap_behind_close"]
    assert feed(eng, st, [lap_packet_race(5, 6)], 200.0) == ["pit_window_open", "gap_ahead"]
    assert feed(eng, st, [lap_packet_race(8, 6)], 400.0) == ["final_laps", "pit_this_lap", "gap_ahead"]
    assert feed(eng, st, [lap_packet_race(10, 6)], 600.0) == ["last_lap", "gap_ahead"]
    assert feed(eng, st, [lap_packet_race(10, 6, warnings=1)], 601.0) == ["penalty_warning"]


def test_tyres_damage_fuel_and_weather() -> None:
    eng, st = Engineer(), TelemetryState()
    feed(eng, st, [race_session(), lap_packet_race(4, 5), status_race(fuel_laps=0.5)], 0.0)
    assert feed(eng, st, [damage_race(wear=(20, 20, 65, 62))], 1.0) == ["tyres_front_wear"]
    assert feed(eng, st, [damage_race(wear=(20, 20, 65, 62))], 2.0) == []  # raz na zestaw
    assert feed(eng, st, [damage_race(wear=(90, 88, 65, 62))], 3.0) == ["tyres_critical"]
    assert feed(eng, st, [status_race(tyre_age=0), damage_race(wear=(5, 5, 5, 5))], 4.0) == []  # nowe opony: flagi skasowane
    assert feed(eng, st, [damage_race(wear=(66, 66, 10, 10))], 5.0) == ["tyres_rear_wear"]
    assert feed(eng, st, [damage_race(fl_wing=30)], 6.0) == ["damage_front_wing"]
    assert feed(eng, st, [damage_race(fl_wing=70, floor=40)], 7.0) == ["damage_front_wing_big", "damage_floor"]
    assert feed(eng, st, [damage_race(engine=85, tyre_dmg=(0, 95, 0, 0))], 8.0) == ["puncture", "engine_warn"]
    assert feed(eng, st, [status_race(fuel_laps=-1.0)], 9.0) == ["fuel_save"]
    assert feed(eng, st, [status_race(fuel_laps=3.0)], 10.0) == ["fuel_push"]
    assert feed(eng, st, [race_session(weather=4)], 11.0) == ["rain_now"]
    assert feed(eng, st, [race_session(weather=1)], 12.0) == ["track_drying"]
    assert feed(eng, st, [event_packet("COLL", bytes([PLAYER, 7]))], 13.0) == ["collision"]
    assert feed(eng, st, [event_packet("PENA", bytes([2, 1, PLAYER, 255, 5, 4, 0]))], 14.0) == ["penalty_time"]
    assert feed(eng, st, [event_packet("PENA", bytes([2, 1, 9, 255, 5, 4, 0]))], 15.0) == []  # kara innego auta


def test_clips_and_race_mode_on_recording(tmp_path: Path) -> None:
    assert laps_clip(3) == ("eng_laps_3", "trzy okrążenia") and laps_clip(12)[0] == "eng_laps_10"
    assert seconds_clip(2.4) == ("eng_sec_2", "dwie sekundy")
    from boxbox.session import CoachSession, SessionConfig

    said: list[str] = []
    s = CoachSession(SessionConfig(mode="race", replay=Path("recordings/monza-trening_2026-10-26_153411.bin.xz"), speed=0,
                                   db=tmp_path / "r.sqlite", no_voice=True), on_message=lambda ids, text: said.append(text))
    s.start()
    s.loop()
    result = s.finish()
    assert said and said[0].startswith("Inżynier na radiu") and not result.coach_started
    assert all("Hamowanie" not in t for t in said)  # inżynier nie poprawia techniki


def test_start_analysis_reaction_wheelspin_positions() -> None:
    from boxbox.engineer.start import StartAnalyzer

    a = StartAnalyzer(max_rpm=13000)
    a.lights_out(10.0, grid_position=8)
    # 0,35 s reakcji, uślizg przez ~1 s, potem jazda
    for i in range(0, 60):
        t = 10.0 + i * 0.1
        thr = 0.0 if i < 4 else 1.0
        rpm = 12500 if 4 <= i < 14 else 9000
        speed = 0 if i < 4 else min(250, (i - 4) * 9)
        a.feed(t, thr, speed, rpm, 1, 8)
    a.feed(100.0, 0.5, 200, 9000, 2, 6)
    r = a.report()
    assert r is not None and abs(r.reaction_s - 0.4) < 0.11 and r.wheelspin_s >= 0.5 and r.position_after_lap1 == 6
    assert "reakcja" in r.text and "uślizg" in r.text and "2 pozycje do przodu" in r.text and not r.ok
    b = StartAnalyzer()
    assert b.report() is None


def test_engineer_reports_start_after_first_lap() -> None:
    eng, st = Engineer(), TelemetryState()
    feed(eng, st, [race_session(), lap_packet_race(1, 8), status_race(), telemetry_packet(speed=0, throttle=0.0)], 0.0)
    assert feed(eng, st, [event_packet("LGOT")], 5.0) == ["lights_out"]
    for i in range(1, 30):
        feed(eng, st, [telemetry_packet(speed=min(200, i * 8), throttle=1.0)], 5.0 + i * 0.1)
    keys = feed(eng, st, [lap_packet_race(2, 7)], 120.0)
    assert "start_report" in keys and eng.start_report is not None and eng.start_report.grid_position == 7


def test_tyre_temperatures_and_race_summary() -> None:
    from boxbox.engineer.summary import summarize_race

    eng, st = Engineer(), TelemetryState()
    feed(eng, st, [race_session(), lap_packet_race(2, 5), status_race()], 0.0)
    assert feed(eng, st, [telemetry_packet()], 1.0) == ["tyres_window"]  # builder: 90-93 °C = okno pracy
    assert feed(eng, st, [telemetry_packet()], 2.0) == []  # raz na sesję
    eng.collisions, eng.penalties = 1, 0
    s = summarize_race(st, None, 1, 0, 0, 0)
    assert s.safety_rating == 80 and "Kontakty: 1" in s.lines[-2] and s.to_work.startswith("1 kontakt")
    s2 = summarize_race(st, None, 0, 0, 0, 1)
    assert s2.safety_rating == 100 and s2.good.startswith("Wyścig bez kontaktu")
