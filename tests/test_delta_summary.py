from pathlib import Path

from boxbox.coach.corners import CornerMetrics, LapAnalysis, analyze_lap
from boxbox.coach.delta import biggest_losses, delta_trace, lap_csv
from boxbox.coach.laps import Lap, Sample
from boxbox.coach.rules import Message, evaluate_lap
from boxbox.coach.summary import rule_pl, summarize
from boxbox.tools.bugreport import build_bug_report
from tests.synthetic import LENGTH, track
from tests.test_laps import synthetic_samples


def slower_copy(samples: list[Sample], from_m: float, to_m: float, factor: float = 1.3) -> list[Sample]:
    """Ta sama jazda, ale między from_m i to_m czas płynie wolniej (strata czasu na tym odcinku)."""
    out: list[Sample] = []
    extra = 0.0
    prev_t = samples[0].lap_time_ms
    for s in samples:
        dt = s.lap_time_ms - prev_t
        prev_t = s.lap_time_ms
        if from_m <= s.distance_m <= to_m:
            extra += dt * (factor - 1)
        out.append(Sample(s.distance_m, int(s.lap_time_ms + extra), s.speed_kmh, s.throttle, s.brake, s.gear, s.steer))
    return out


def test_delta_trace_zero_for_identical_and_grows_where_slower() -> None:
    ref = synthetic_samples()
    same = delta_trace(ref, ref)
    assert same and all(abs(p.delta_s) < 1e-6 for p in same) and same[0].distance_m % 10 == 0
    slow = slower_copy(ref, 1400.0, 1700.0)
    trace = delta_trace(slow, ref)
    before = next(p for p in trace if p.distance_m == 1390.0)
    after = next(p for p in trace if p.distance_m == 1800.0)
    assert abs(before.delta_s) < 0.01 and after.delta_s > 0.3
    assert abs(trace[-1].delta_s - after.delta_s) < 0.01  # dalej strata się nie zmienia
    losses = biggest_losses(trace)
    assert losses and 1250 <= losses[0][0] <= 1700 and losses[0][1] > 0.2


def test_lap_csv_polish_format() -> None:
    ref = synthetic_samples()
    text = lap_csv(ref[:50], ref)
    lines = text.splitlines()
    assert lines[0] == "dystans_m;czas_s;predkosc_kmh;gaz;hamulec;bieg;kierownica;delta_s;predkosc_ref_kmh"
    assert len(lines) == 51 and "," in lines[1] and ";" in lines[1]


def test_summary_good_and_to_work() -> None:
    t = track()
    ref = synthetic_samples()
    lap_ref = Lap(1, ref, 90_000)
    lap_bad = Lap(2, slower_copy(ref, 500.0, 700.0, 1.5), 92_000)
    a_ref, a_bad = analyze_lap(lap_ref, t), analyze_lap(lap_bad, t)
    assert evaluate_lap(lap_bad, a_bad, a_ref, t) == []  # ta sama jazda, inny czas: reguły nic nie widzą
    msgs = [Message(2, 1, "Z1", "brake_late", "p", "h", 1.4), Message(2, 1, "Z1", "brake_late", "p", "h", 0.6),
            Message(2, 3, "Z3", "throttle_early", "p", "h", 0.5)]
    s = summarize([lap_ref, lap_bad], msgs, t, best_now=a_ref)
    assert s.laps == 2 and s.best_lap_ms == 90_000 and s.clean_laps == 1
    assert s.to_work.startswith("Z1: hamowanie za późno") and "1.4 s" in s.to_work
    assert s.good.startswith("1 czyste okrążenie")
    # poprawa względem poprzedniej sesji: hamowanie 15 m później w Z1
    before = [CornerMetrics(m.corner, m.min_speed_kmh, m.apex_m, m.gear_at_apex, m.entry_speed_kmh, m.exit_speed_kmh, m.time_ms,
                            (m.brake_point_m - 15) if m.brake_point_m else None, m.full_throttle_m) for m in a_ref.corners]
    s2 = summarize([lap_ref], [], t, best_now=a_ref, best_before=before, best_before_ms=91_000)
    assert "nowe najlepsze" in s2.good and "1.000 s" in s2.good
    s3 = summarize([lap_ref], [], t, best_now=a_ref, best_before=before, best_before_ms=89_000)
    assert "hamujesz 15 m później" in s3.good and s3.to_work.startswith("nic pilnego")
    assert rule_pl("throttle_early") == "gaz za wcześnie" and rule_pl("xyz_abc") == "xyz abc"
    empty = summarize([], [], t)
    assert "punkt odniesienia" in empty.good


def test_bug_report_zip(tmp_path: Path) -> None:
    data = tmp_path / "data"
    data.mkdir()
    (data / "boxbox.log").write_text("log", encoding="utf-8")
    (data / "settings.json").write_text("{}", encoding="utf-8")
    recs = tmp_path / "recordings"
    recs.mkdir()
    (recs / "a.bin.xz").write_bytes(b"x" * 10)
    files = build_bug_report("trener milczy", data, recs, tmp_path / "out")
    import zipfile
    names = zipfile.ZipFile(files[0]).namelist()
    assert "opis.json" in names and "data/boxbox.log" in names and "recordings/a.bin.xz" in names
