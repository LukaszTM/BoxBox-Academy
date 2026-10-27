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


def test_session_with_lesson_and_explain_on_recording(tmp_path) -> None:
    from pathlib import Path

    from boxbox.session import CoachSession, SessionConfig

    said: list[str] = []
    cfg = SessionConfig(replay=Path("recordings/monza-trening_2026-10-26_153411.bin.xz"),
                        speed=0, db=tmp_path / "l.sqlite", no_voice=True, lesson="throttle_exit", explain_mode=True)
    s = CoachSession(cfg, on_message=lambda ids, text: said.append(text))
    s.start()
    s.loop()
    result = s.finish()
    assert result.lesson_result is not None and result.lesson_result[2] == 3
    corner_texts = [t for t in said if "Zakręt" in t or "Zakręty" in t]
    assert corner_texts and all(("gaz" in t.lower() or "przyczepno" in t.lower()) for t in corner_texts), corner_texts  # lekcja gazu: bez uwag o hamowaniu
    explained = [t for t in said if "Każdy metr bez gazu" in t or "a bez kontroli trakcji auto może się obrócić" in t]
    assert len(explained) >= 1  # wyjaśnienie przy pierwszej uwadze danego typu
    rules_explained = sum(1 for t in said if "Każdy metr bez gazu" in t)
    assert rules_explained <= 1  # tylko przy pierwszym wystąpieniu
