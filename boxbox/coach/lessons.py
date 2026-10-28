"""Lekcje: krótkie ćwiczenia z jednym mierzalnym celem. Dane i ocena, bez UI i bez głosu.

Lekcja mówi trenerowi, o czym mówić (tylko o jednym zakręcie / jednej regule), a po sesji
sprawdza, czy cel został osiągnięty. Trzy lekcje startowe są darmowe; reszta w premium (etap 8).
"""
from collections.abc import Sequence
from dataclasses import dataclass

from boxbox.coach.laps import Lap
from boxbox.coach.rules import Message


@dataclass(frozen=True)
class Lesson:
    id: str
    title: str
    goal: str  # jedno zdanie celu dla gracza
    laps: int  # ile okrążeń trwa
    rules: tuple[str, ...]  # reguły, o których trener mówi w tej lekcji (reszta milczy)
    corner_only: bool  # True = gracz wybiera jeden zakręt, trener pilnuje tylko jego
    pass_rule: str  # "clean_streak:3" | "no_rule:brake_late:3" | "laps:N"
    premium: bool = False
    explain: str = ""  # dłuższe wyjaśnienie, do trybu "wytłumacz mi" i słownika


LESSONS: tuple[Lesson, ...] = (
    Lesson(
        "braking_one_corner", "Hamowanie w jednym zakręcie",
        "Wybierz jeden zakręt. Przez 5 okrążeń hamuj w nim tak, żeby trener nie miał uwag o hamowaniu 3 razy z rzędu.",
        5, ("brake_late", "brake_late_big", "brake_early", "brake_release", "trail_missing"), True, "no_rule:brake:3",
        explain="Punkt hamowania to miejsce, gdzie zaczynasz hamować. Za późno: nie wyrabiasz się do apeksu i tracisz "
                "wyjście. Za wcześnie: dojeżdżasz do apeksu z zapasem i tracisz czas na wejściu. Szukamy miejsca, w którym "
                "auto zwalnia dokładnie tyle, ile trzeba, a hamulec puszczasz stopniowo aż do apeksu.",
    ),
    Lesson(
        "throttle_exit", "Gaz na wyjściu",
        "Przez 5 okrążeń na wyjściach z zakrętów dodawaj gaz, gdy kierownica się prostuje. Cel: 3 okrążenia bez uwag o gazie.",
        5, ("throttle_early", "throttle_late", "grip_lost"), False, "no_rule:throttle:3",
        explain="Pełny gaz za wcześnie przeciąża tylne koła i auto się ślizga, zwłaszcza bez kontroli trakcji. Za późno "
                "to stracone metry na prostej. Dodawaj gaz tak, jak prostujesz kierownicę: im mniej skrętu, tym więcej gazu.",
    ),
    Lesson(
        "clean_lap", "Czyste okrążenie",
        "Przejedź 3 okrążenia z rzędu bez poważnego błędu (żadna uwaga trenera nie przekracza 1 s).",
        6, (), False, "clean_streak:3",
        explain="Czyste okrążenie to nie najszybsze, tylko takie bez dużych strat. Z takich okrążeń buduje się tempo; "
                "najpierw powtarzalność, potem czas.",
    ),
    Lesson(
        "trail_braking", "Trail-braking",
        "Trzymaj lekki hamulec do apeksu w wolnych zakrętach. Cel: 3 okrążenia bez uwagi o zbyt wczesnym puszczeniu hamulca.",
        5, ("trail_missing", "brake_release"), True, "no_rule:trail_missing:3",  # od makiety v4 lekcja startowa (wejście z karty „Praca hamulcem”)
        explain="Trail-braking to stopniowe zwalnianie hamulca już po skręceniu. Przód auta zostaje dociążony i lepiej "
                "skręca; auto wchodzi w zakręt zamiast pchać przodem.",
    ),
    Lesson(
        "ers_straights", "Bateria na prostych",
        "Używaj baterii po wyjściu z zakrętu na prostych. Cel: 3 okrążenia bez uwagi o marnowaniu baterii w zakrętach.",
        5, (), False, "laps:3", premium=True,
        explain="Energia z baterii daje najwięcej, gdy auto już przyspiesza na prostej. W zakręcie i w hamowaniu idzie na marne.",
    ),
)

RULE_GROUPS = {"brake": ("brake_late", "brake_late_big", "brake_early", "brake_release", "trail_missing"),
               "throttle": ("throttle_early", "throttle_late", "grip_lost")}


def lesson(lesson_id: str) -> Lesson:
    for item in LESSONS:
        if item.id == lesson_id:
            return item
    raise KeyError(lesson_id)


def free_lessons() -> list[Lesson]:
    return [item for item in LESSONS if not item.premium]


def filter_messages(item: Lesson, messages: Sequence[Message], corner: int | None = None) -> list[Message]:
    """Uwagi, o których trener mówi w tej lekcji: tylko jej reguły (i tylko wybrany zakręt, jeśli trzeba)."""
    out = []
    for m in messages:
        if item.rules and m.rule not in item.rules:
            continue
        if item.corner_only and corner is not None and m.corner != corner:
            continue
        out.append(m)
    return out


def evaluate(item: Lesson, laps: Sequence[Lap], messages_by_lap: dict[int, Sequence[Message]], corner: int | None = None) -> tuple[bool, int, int]:
    """(zaliczona?, najdłuższa seria okrążeń spełniających warunek, wymagana seria)."""
    kind, _, rest = item.pass_rule.partition(":")
    needed = int(rest.rsplit(":", 1)[-1]) if ":" in rest else int(rest)
    group = rest.split(":")[0] if kind == "no_rule" else ""
    rules = RULE_GROUPS.get(group, (group,))
    best = streak = 0
    for lap in laps:
        if lap.pitted or not lap.lap_time_ms:
            continue
        msgs = list(messages_by_lap.get(lap.number, ()))
        if corner is not None and item.corner_only:
            msgs = [m for m in msgs if m.corner == corner]
        if kind == "laps":
            ok = not lap.invalid
        elif kind == "clean_streak":
            ok = not lap.invalid and all(m.weight < 1.0 for m in msgs)
        else:  # no_rule
            ok = not lap.invalid and not any(m.rule in rules for m in msgs)
        streak = streak + 1 if ok else 0
        best = max(best, streak)
    return best >= needed, best, needed
