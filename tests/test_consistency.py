"""Spójność jazdy: rozrzut czasów, odsetek czystych, porównanie „wtedy vs dziś”."""
from datetime import date

from boxbox.coach.consistency import LapRecord, clean_share, consistency, format_share, then_vs_now


def test_consistency_labels_by_relative_spread() -> None:
    short = consistency([90_000, 90_100])
    assert short.spread_s is None and short.label == "za mało okrążeń"
    even = consistency([90_000, 90_200, 89_900, 90_100, 90_000])
    assert even.label == "bardzo równo" and even.laps == 5 and even.spread_s < 0.2
    rough = consistency([90_000, 94_000, 88_000, 93_500, 90_500])
    assert rough.label == "nierówno" and "powtarzalność" in rough.advice
    # okno: liczą się tylko ostatnie 10 okrążeń, zera (brak czasu) są pomijane
    windowed = consistency([120_000, 0] + [90_000] * 10)
    assert windowed.laps == 10 and windowed.spread_s == 0.0


def test_clean_share_ignores_laps_without_time() -> None:
    assert clean_share([]) is None
    recs = [LapRecord(date(2026, 10, 1), 90_000, True, True), LapRecord(date(2026, 10, 1), 91_000, True, False),
            LapRecord(date(2026, 10, 1), None, False, False)]
    assert clean_share(recs) == 0.5 and format_share(0.5) == "50 %" and format_share(None) == "—"


def _day(d: date, times: list[int], clean: bool = True) -> list[LapRecord]:
    return [LapRecord(d, t, True, clean) for t in times]


def test_then_vs_now_uses_month_old_sessions_when_available() -> None:
    recs = _day(date(2026, 9, 20), [92_000, 93_000], clean=False) + _day(date(2026, 10, 25), [90_500, 90_000]) + _day(date(2026, 10, 27), [89_800])
    r = then_vs_now(recs, today=date(2026, 10, 27))
    assert r is not None and r.then.label == "miesiąc temu" and r.then.laps == 2 and r.now.laps == 3
    assert r.best_delta_s == -2.2 and r.clean_delta == 1.0
    assert r.summary.startswith("Najlepszy czas o 2,20 s lepszy niż miesiąc temu")
    assert "czystych okrążeń więcej o 100 pkt proc." in r.summary


def test_then_vs_now_falls_back_to_first_day() -> None:
    assert then_vs_now([]) is None
    assert then_vs_now(_day(date(2026, 10, 27), [90_000, 91_000])) is None  # jeden dzień: nie ma czego porównać
    recs = _day(date(2026, 10, 20), [95_000, 96_000]) + _day(date(2026, 10, 27), [95_100])
    r = then_vs_now(recs)
    assert r is not None and r.then.label == "pierwszy dzień (20.10)" and r.now.label == "dziś" and r.now.laps == 1
    assert r.best_delta_s == 0.1 and r.mean_delta_s == -0.4
    assert r.summary == "Najlepszy czas o 0,10 s gorszy niż pierwszy dzień (20.10); średnie okrążenie szybsze o 0,40 s."


def test_then_vs_now_without_valid_times() -> None:
    recs = [LapRecord(date(2026, 10, 20), 95_000, False, False), LapRecord(date(2026, 10, 27), 94_000, False, False)]
    r = then_vs_now(recs)
    assert r is not None and r.best_delta_s is None and r.summary == "Za mało ważnych okrążeń w obu okresach, żeby porównać."
