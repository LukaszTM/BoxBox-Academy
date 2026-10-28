"""Spójność jazdy na torze: rozrzut czasów, odsetek czystych okrążeń i porównanie „wtedy vs dziś”.

Czysty silnik na liczbach z bazy (czas, ważność, data okrążenia); bez UI.
Rozrzut liczony jako odchylenie standardowe ważnych czasów z ostatnich okrążeń,
a ocena w słowach zależy od rozrzutu względem czasu okrążenia (0,5 % to bardzo równo,
2 % to nierówno), żeby Monza i Monako były oceniane tą samą miarą.
"""
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from statistics import mean, pstdev

WINDOW = 10  # okrążeń do rozrzutu
MIN_LAPS = 3
THEN_DAYS = 28  # „wtedy” = sesje sprzed co najmniej 4 tygodni
NOW_DAYS = 7  # „dziś” = ostatni tydzień jazdy


@dataclass(frozen=True)
class LapRecord:
    day: date
    lap_time_ms: int | None
    valid: bool
    clean: bool  # ważne i bez poważnego błędu (waga >= 1 s)


@dataclass(frozen=True)
class Consistency:
    laps: int  # ważnych okrążeń w oknie
    spread_s: float | None  # odchylenie standardowe czasów
    ratio: float | None  # rozrzut / średni czas
    label: str
    advice: str


@dataclass(frozen=True)
class Period:
    label: str
    laps: int
    best_ms: int | None
    mean_ms: int | None
    clean_share: float | None  # 0..1


@dataclass(frozen=True)
class ThenNow:
    then: Period
    now: Period
    best_delta_s: float | None  # dziś − wtedy, ujemne = szybciej
    mean_delta_s: float | None
    clean_delta: float | None  # punkty procentowe / 100
    summary: str


def consistency(times_ms: Sequence[int], window: int = WINDOW) -> Consistency:
    times = [t for t in times_ms if t][-window:]
    if len(times) < MIN_LAPS:
        return Consistency(len(times), None, None, "za mało okrążeń", f"Potrzeba {MIN_LAPS} ważnych okrążeń, żeby ocenić równość jazdy.")
    avg = mean(times)
    spread = pstdev(times)
    ratio = spread / avg
    if ratio <= 0.005:
        label, advice = "bardzo równo", "Czasy prawie identyczne. Możesz spokojnie szukać tempa w zakrętach."
    elif ratio <= 0.01:
        label, advice = "równo", "Niewielki rozrzut. Pracuj nad powtarzalnością hamowania w najtrudniejszym zakręcie."
    elif ratio <= 0.02:
        label, advice = "zmiennie", "Spory rozrzut. Zanim przyspieszysz, zrób trzy okrążenia w tym samym tempie."
    else:
        label, advice = "nierówno", "Duży rozrzut czasów. Celem na następną sesję jest powtarzalność, nie rekord."
    return Consistency(len(times), round(spread / 1000, 3), round(ratio, 4), label, advice)


def clean_share(records: Sequence[LapRecord]) -> float | None:
    done = [r for r in records if r.lap_time_ms]
    if not done:
        return None
    return sum(1 for r in done if r.clean) / len(done)


def _period(label: str, records: Sequence[LapRecord]) -> Period:
    valid = [r.lap_time_ms for r in records if r.valid and r.lap_time_ms]
    return Period(label, len(records), min(valid) if valid else None, int(mean(valid)) if valid else None, clean_share(records))


def then_vs_now(records: Sequence[LapRecord], today: date | None = None) -> ThenNow | None:
    """Porównuje okres sprzed miesiąca z ostatnim tygodniem; bez starych danych: pierwszy dzień jazdy z ostatnim.

    Zwraca None, gdy wszystko było jednego dnia (nie ma czego porównywać).
    """
    if not records:
        return None
    days = sorted({r.day for r in records})
    if len(days) < 2:
        return None
    last = today or days[-1]
    now_from = last - timedelta(days=NOW_DAYS - 1)
    now_recs = [r for r in records if r.day >= now_from]
    old = [r for r in records if r.day <= last - timedelta(days=THEN_DAYS)]
    if old:
        then_recs, then_label = old, "miesiąc temu"
    else:
        first = days[0]
        then_recs, then_label = [r for r in records if r.day == first], f"pierwszy dzień ({first:%d.%m})"
        now_recs = [r for r in records if r.day > first and r.day >= now_from] or [r for r in records if r.day == days[-1]]
    then, now = _period(then_label, then_recs), _period("dziś", now_recs)
    best_delta = (now.best_ms - then.best_ms) / 1000 if now.best_ms and then.best_ms else None
    mean_delta = (now.mean_ms - then.mean_ms) / 1000 if now.mean_ms and then.mean_ms else None
    clean_delta = (now.clean_share - then.clean_share) if now.clean_share is not None and then.clean_share is not None else None
    return ThenNow(then, now, None if best_delta is None else round(best_delta, 3), None if mean_delta is None else round(mean_delta, 3),
                   None if clean_delta is None else round(clean_delta, 3), _summary(then_label, best_delta, mean_delta, clean_delta))


def _summary(then_label: str, best_delta: float | None, mean_delta: float | None, clean_delta: float | None) -> str:
    parts = []
    if best_delta is not None:
        if best_delta < -0.05:
            parts.append(f"najlepszy czas o {_s(abs(best_delta))} lepszy niż {then_label}")
        elif best_delta > 0.05:
            parts.append(f"najlepszy czas o {_s(best_delta)} gorszy niż {then_label}")
        else:
            parts.append(f"najlepszy czas bez zmian od: {then_label}")
    if mean_delta is not None and abs(mean_delta) > 0.05:
        parts.append(f"średnie okrążenie {'szybsze' if mean_delta < 0 else 'wolniejsze'} o {_s(abs(mean_delta))}")
    if clean_delta is not None and abs(clean_delta) >= 0.1:
        parts.append(f"czystych okrążeń {'więcej' if clean_delta > 0 else 'mniej'} o {abs(round(clean_delta * 100))} pkt proc.")
    if not parts:
        return "Za mało ważnych okrążeń w obu okresach, żeby porównać."
    text = "; ".join(parts)
    return text[0].upper() + text[1:] + "."


def _s(seconds: float) -> str:
    return f"{seconds:.2f} s".replace(".", ",")


def format_share(share: float | None) -> str:
    return "—" if share is None else f"{round(share * 100)} %"
