from boxbox.coach.glossary import GLOSSARY, explain
from boxbox.coach.laps import Lap
from boxbox.coach.lessons import LESSONS, evaluate, filter_messages, free_lessons, lesson
from boxbox.coach.rules import Message
from boxbox.session import focus_line, next_lap_target
from tests.synthetic import LENGTH
from tests.test_laps import synthetic_samples


def lap(n: int, invalid: bool = False) -> Lap:
    return Lap(n, synthetic_samples(), 90_000, invalid=invalid, track_length_m=LENGTH)


def msg(n: int, corner: int, rule: str, w: float = 0.5, value_m: int | None = None) -> Message:
    return Message(n, corner, f"Z{corner}", rule, "p", "h", w, value_m=value_m)


def test_lessons_catalog_and_filter() -> None:
    assert len(free_lessons()) == 3 and all(not item.premium for item in free_lessons())
    item = lesson("braking_one_corner")
    msgs = [msg(1, 1, "brake_late"), msg(1, 2, "brake_late"), msg(1, 1, "throttle_early")]
    assert [m.corner for m in filter_messages(item, msgs, corner=1)] == [1]
    assert len(filter_messages(lesson("clean_lap"), msgs)) == 3  # bez filtra reguł
    assert len({item.id for item in LESSONS}) == len(LESSONS)


def test_lesson_evaluation_streaks() -> None:
    item = lesson("braking_one_corner")
    laps = [lap(1), lap(2), lap(3), lap(4), lap(5)]
    by_lap = {1: [msg(1, 1, "brake_late")], 2: [], 3: [msg(3, 2, "brake_late")], 4: [], 5: [msg(5, 1, "throttle_early")]}
    passed, best, needed = evaluate(item, laps, by_lap, corner=1)
    assert (passed, best, needed) == (True, 4, 3)  # od okrążenia 2: w Z1 brak uwag o hamowaniu
    passed, best, _ = evaluate(item, laps, by_lap, corner=2)
    assert not passed and best == 2
    clean = lesson("clean_lap")
    by_lap2 = {1: [msg(1, 1, "brake_late", 2.0)], 2: [msg(2, 1, "brake_late", 0.4)], 3: [], 4: []}
    assert evaluate(clean, laps[:4], by_lap2) == (True, 3, 3)
    assert evaluate(clean, [lap(1), lap(2, invalid=True), lap(3)], {}) == (False, 1, 3)


def test_next_lap_target_and_focus_line() -> None:
    assert next_lap_target(msg(1, 1, "brake_late", 1.0, 50)) == "hamuj 20 m wcześniej"  # połowa, max 20
    assert next_lap_target(msg(1, 1, "brake_early", 1.0, 12)) == "hamuj 5 m później"  # min 5
    assert next_lap_target(msg(1, 1, "throttle_late", 1.0, 30)) == "pełny gaz 15 m wcześniej"
    assert next_lap_target(msg(1, 1, "throttle_early", 1.0)) == ""
    assert focus_line([msg(2, 3, "brake_late", 1.2, 40), msg(2, 1, "throttle_early", 0.4)]) == "Na tym okrążeniu popraw: Z3, hamuj 20 m wcześniej"
    assert "gaz za wcześnie" in focus_line([Message(2, 1, "Z1", "throttle_early", "Gaz za wcześnie w Z1.", "h", 0.4)]).lower()


def test_glossary_and_explain() -> None:
    assert "apeks" in GLOSSARY and all(len(v[1]) > 40 for v in GLOSSARY.values())
    assert explain("brake_late_big") == explain("brake_late") and explain("grip_lost_throttle") and explain("xyz") == ""
