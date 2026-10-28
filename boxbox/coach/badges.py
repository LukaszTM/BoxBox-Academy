"""Odznaki i cele dnia: liczone z bazy, bez nowej tabeli (odznaka = warunek spełniony przez dane).

Każda odznaka ma cel liczbowy i postęp, więc okno może pokazać „7/10” i pasek. Cel dnia to 1–3
niezdobyte odznaki, do których jest najbliżej (w ułamku celu), żeby po każdej sesji było widać,
że coś się posunęło. Silnik nie dotyka UI: zwraca dane; `python -m boxbox.app --badges` drukuje.
"""
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

from boxbox.coach.progress import CLEAN_LAPS_TO_ADVANCE

BIG_ERROR_WEIGHT = 1.0  # jak w progress.py: okrążenie czyste = bez uwagi o tej wadze
MASTERED_STEP = 4
MAX_GOALS = 3


@dataclass(frozen=True)
class BadgeInput:
    """Liczby z bazy potrzebne do odznak (zbiera `collect`)."""
    sessions: int = 0
    complete_laps: int = 0
    clean_laps: int = 0
    laps_no_tc: int = 0
    laps_no_assists: int = 0
    tracks_driven: int = 0
    tracks_mastered: int = 0
    day_streak: int = 0  # dni z sesją z rzędu, licząc do ostatniej sesji
    improved_sessions: int = 0  # sesje, w których najlepszy czas na torze był lepszy niż wcześniej
    hours: float = 0.0


@dataclass(frozen=True)
class Badge:
    key: str
    name: str
    description: str
    target: int
    value: int
    unit: str = ""  # np. "okrążeń", "sesji", "dni"

    @property
    def earned(self) -> bool:
        return self.value >= self.target

    @property
    def fraction(self) -> float:
        return min(1.0, self.value / self.target) if self.target else 1.0

    @property
    def remaining(self) -> int:
        return max(0, self.target - self.value)

    def to_dict(self) -> dict[str, Any]:
        return {"key": self.key, "name": self.name, "description": self.description, "target": self.target,
                "value": self.value, "unit": self.unit, "earned": self.earned, "fraction": round(self.fraction, 3)}


# (klucz, nazwa, opis, cel, jednostka, pole BadgeInput)
BADGE_DEFS: tuple[tuple[str, str, str, int, str, str], ...] = (
    ("first_clean", "Pierwsze czyste okrążenie", "Ważne okrążenie bez poważnego błędu (żadna uwaga powyżej 1 s).", 1, "okrążeń", "clean_laps"),
    ("clean_10", "Dziesięć czystych", "10 czystych okrążeń łącznie, na dowolnych torach.", 10, "okrążeń", "clean_laps"),
    ("clean_50", "Pięćdziesiąt czystych", "50 czystych okrążeń łącznie.", 50, "okrążeń", "clean_laps"),
    ("no_tc", "Bez kontroli trakcji", "Ważne okrążenie z wyłączoną kontrolą trakcji.", 1, "okrążeń", "laps_no_tc"),
    ("no_assists", "Bez asyst", "Ważne okrążenie bez kontroli trakcji i bez ABS.", 1, "okrążeń", "laps_no_assists"),
    ("sessions_10", "Dziesięć sesji", "10 sesji z pełnym okrążeniem.", 10, "sesji", "sessions"),
    ("laps_100", "Sto okrążeń", "100 pełnych okrążeń.", 100, "okrążeń", "complete_laps"),
    ("tracks_3", "Trzy tory", "Pełne okrążenia na trzech różnych torach.", 3, "torów", "tracks_driven"),
    ("track_mastered", "Tor opanowany", f"Bez asyst i {CLEAN_LAPS_TO_ADVANCE} czyste okrążenia z rzędu na jednym torze.", 1, "torów", "tracks_mastered"),
    ("streak_7", "Tydzień z rzędu", "Sesja każdego dnia przez 7 dni.", 7, "dni", "day_streak"),
    ("faster", "Szybciej niż ostatnio", "Sesja z nowym najlepszym czasem na torze.", 1, "sesji", "improved_sessions"),
    ("hours_10", "Dziesięć godzin", "10 godzin jazdy liczonych z pełnych okrążeń.", 10, "godzin", "hours"),
)


def badges(data: BadgeInput) -> tuple[Badge, ...]:
    out = []
    for key, name, desc, target, unit, attr in BADGE_DEFS:
        out.append(Badge(key, name, desc, target, int(getattr(data, attr)), unit))
    return tuple(out)


def goals_of_the_day(all_badges: Sequence[Badge], limit: int = MAX_GOALS) -> tuple[Badge, ...]:
    """Niezdobyte odznaki, do których najbliżej; przy remisie te z mniejszym celem (szybciej cieszy)."""
    todo = [b for b in all_badges if not b.earned]
    todo.sort(key=lambda b: (-b.fraction, b.remaining, b.target))
    return tuple(todo[:limit])


def goal_text(badge: Badge) -> str:
    """Jedno zdanie do okna: „Dziesięć czystych: jeszcze 3 okrążenia”."""
    n = badge.remaining
    unit = badge.unit
    if unit == "okrążeń":
        unit = "okrążenie" if n == 1 else ("okrążenia" if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14 else "okrążeń")
    elif unit == "sesji":
        unit = "sesja" if n == 1 else ("sesje" if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14 else "sesji")
    elif unit == "dni":
        unit = "dzień" if n == 1 else "dni"
    elif unit == "torów":
        unit = "tor" if n == 1 else ("tory" if 2 <= n <= 4 else "torów")
    elif unit == "godzin":
        unit = "godzina" if n == 1 else ("godziny" if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14 else "godzin")
    return f"{badge.name}: jeszcze {n} {unit}"


def day_streak(dates: Sequence[str]) -> int:
    """Dni z sesją z rzędu, licząc wstecz od ostatniej daty (ISO 'RRRR-MM-DD')."""
    days = sorted({date.fromisoformat(d[:10]) for d in dates if d})
    if not days:
        return 0
    streak, cur = 1, days[-1]
    for d in reversed(days[:-1]):
        if cur - d == timedelta(days=1):
            streak, cur = streak + 1, d
        else:
            break
    return streak


def collect(db: Any) -> BadgeInput:
    """Zbiera liczby z `boxbox.storage.db.Database`."""
    one = lambda sql, *args: db.conn.execute(sql, args).fetchone()[0]  # noqa: E731
    usable = "valid = 1 AND complete = 1 AND pitted = 0 AND lap_time_ms IS NOT NULL"
    clean = one(
        f"SELECT COUNT(*) FROM laps l WHERE {usable} AND NOT EXISTS"
        " (SELECT 1 FROM lap_messages m WHERE m.lap_id = l.id AND m.weight >= ?)", BIG_ERROR_WEIGHT,
    )
    improved = 0
    best: dict[int, int] = {}
    for row in db.conn.execute(
        "SELECT s.id, s.track_id, MIN(CASE WHEN l.valid = 1 AND l.pitted = 0 AND l.complete = 1 THEN l.lap_time_ms END) AS best"
        " FROM sessions s JOIN laps l ON l.session_id = s.id WHERE s.track_id IS NOT NULL GROUP BY s.id ORDER BY s.id"
    ).fetchall():
        if row["best"] is None:
            continue
        prev = best.get(row["track_id"])
        if prev is not None and row["best"] < prev:
            improved += 1
        best[row["track_id"]] = min(prev, row["best"]) if prev is not None else row["best"]
    return BadgeInput(
        sessions=one("SELECT COUNT(DISTINCT session_id) FROM laps WHERE complete = 1"),
        complete_laps=one("SELECT COUNT(*) FROM laps WHERE complete = 1"),
        clean_laps=clean,
        laps_no_tc=one(f"SELECT COUNT(*) FROM laps WHERE {usable} AND traction_control = 0"),
        laps_no_assists=one(f"SELECT COUNT(*) FROM laps WHERE {usable} AND traction_control = 0 AND abs_on = 0"),
        tracks_driven=one("SELECT COUNT(DISTINCT track_id) FROM laps WHERE complete = 1 AND track_id IS NOT NULL"),
        tracks_mastered=one("SELECT COUNT(*) FROM progress WHERE step >= ? AND streak >= ?", MASTERED_STEP, CLEAN_LAPS_TO_ADVANCE),
        day_streak=day_streak(db.session_dates()),
        improved_sessions=improved,
        hours=db.track_hours(),
    )


def render(all_badges: Sequence[Badge], goals: Sequence[Badge]) -> str:
    lines = ["Odznaki:"]
    for b in all_badges:
        mark = "[x]" if b.earned else "[ ]"
        lines.append(f"  {mark} {b.name:<28} {min(b.value, b.target)}/{b.target} {b.unit}")
    if goals:
        lines.append("Cele dnia:")
        lines += [f"  - {goal_text(g)}" for g in goals]
    return "\n".join(lines)
