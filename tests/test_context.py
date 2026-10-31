"""Warunki okrążenia i uczciwe porównanie z mistrzem: zbieranie z telemetrii, porównywalność, poprawki."""
from boxbox.coach.context import MASTER_CONTEXT, LapContext, adjust, comparable, lap_context
from boxbox.coach.lap_samples import TyreSample
from boxbox.coach.laps import Lap, LapRecorder
from boxbox.coach.master import master_utterance
from boxbox.coach.master import MasterGap
from boxbox.storage.db import Database, context_dict
from tests.builders import damage_packet, lap_packet, session_packet, status_packet, telemetry_packet
from tests.test_laps import synthetic_samples


def test_recorder_collects_lap_conditions() -> None:
    rec = LapRecorder()
    rec.feed(session_packet())
    rec.feed(status_packet())
    rec.feed(damage_packet())
    rec.feed(lap_packet(lap_distance=100.0, lap_num=1, lap_invalid=False))
    rec.feed(telemetry_packet())
    lap = rec.current
    assert lap is not None
    assert lap.fuel_kg == 42.5 and lap.compound == "medium" and lap.tyre_age_laps == 4  # z builderów: paliwo 42,5 kg, opona 17, wiek 4
    assert lap.weather is not None and lap.session_type is not None and lap.track_temp_c is not None
    assert lap.damage_percent >= 0
    ctx = lap_context(lap)
    assert ctx.fuel_kg == 42.5 and ctx.compound == "medium" and ctx.assists_label  # asysty z głosowania


def test_comparable_and_adjustment() -> None:
    assert comparable(LapContext()) == (True, "")
    assert comparable(LapContext(weather=4))[0] is False and "deszcz" in comparable(LapContext(weather=4))[1]
    assert comparable(LapContext(compound="wet"))[0] is False
    assert comparable(LapContext(damage_percent=25))[0] is False and comparable(LapContext(damage_percent=5))[0] is True
    assert comparable(LapContext(wear_percent=70))[0] is False and comparable(LapContext(wear_percent=40))[0] is True
    ctx = LapContext(fuel_kg=45.0, compound="medium", wear_percent=40.0, traction_control=2, abs_on=True, gearbox=3)
    adj = adjust(7_000, ctx)
    assert [i[0] for i in adj.items] == ["paliwo 45 kg", "opony średnie", "zużycie 40 %"]
    assert [i[1] for i in adj.items] == [1200, 600, 200]  # 40 kg * 0,03 s, +0,6 s mieszanka, 10 % * 0,02 s
    assert adj.conditions_ms == 2000 and adj.adjusted_ms == 5000
    assert adj.describe() == "paliwo 45 kg +1,2 s · opony średnie +0,6 s · zużycie 40 % +0,2 s · asysty: automat, TC pełna, ABS"
    tt = adjust(7_000, MASTER_CONTEXT)
    assert tt.items == () and tt.adjusted_ms == 7_000 and tt.describe() == "warunki jak w Time Trial"
    assert adjust(500, ctx).adjusted_ms == 0  # warunki wyjaśniają całą stratę: nie schodzimy poniżej zera
    ids, text = master_utterance(MasterGap(7_000, 3, 900, "none", 0), "T3", adjusted_ms=5_000)
    assert ids[:4] == ["misc_master_gap", "misc_loss_8", "misc_master_similar", "misc_loss_5"]  # 7 s -> „około osiem”, 5 s -> „około pięć”
    assert "W podobnych warunkach" in text


def test_context_round_trip_in_database(tmp_path) -> None:
    from boxbox.coach.corners import analyze_lap
    from boxbox.telemetry.session import parse_session
    from tests.synthetic import track

    db = Database(tmp_path / "c.sqlite")
    t = track()
    sid = db.save_session(parse_session(session_packet()), source="x")
    lap = Lap(2, synthetic_samples(), 90_000, fuel_kg=38.0, compound="hard", tyre_age_laps=6, damage_percent=3, weather=1, track_temp_c=31, session_type=1)
    lap.tyres.append(TyreSample(4990.0, (95, 95, 95, 95), (95, 95, 95, 95), (12.0, 15.5, 11.0, 10.0)))
    db.save_lap(sid, lap, analyze_lap(lap, t), t.length_m)
    stored = db.laps_for_track(3)[0]
    assert stored.context == context_dict(lap) == {"fuel_kg": 38.0, "compound": "hard", "tyre_age_laps": 6, "wear_percent": 15.5,
                                                   "damage_percent": 3, "weather": 1, "track_temp_c": 31, "session_type": 1}
    db.close()
