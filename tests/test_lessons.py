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
    assert len(free_lessons()) == 4 and all(not item.premium for item in free_lessons())  # 3 startowe + trail-braking (makieta v4)
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


def test_data_goal_lessons_drs_ers_tyres() -> None:
    from boxbox.coach.ers_sample import ErsSample
    from boxbox.coach.lap_samples import DrsSample, TyreSample
    from tests.synthetic import track

    def drs_lap(n: int, reaction_ms: int | None, assist: bool = False) -> Lap:
        l = lap(n)
        l.drs_assist = assist
        for d in range(0, 5000, 10):  # strefa 2000–2600 m: lampka od 2000, skrzydło po `reaction_ms`
            t = d * 18  # ~90 s na 5000 m
            in_zone = 2000 <= d < 2600
            on = reaction_ms is not None and in_zone and t >= 2000 * 18 + reaction_ms
            l.drs.append(DrsSample(float(d), t, in_zone and not on, on))
        return l

    drs = lesson("drs_zones")
    laps = [drs_lap(1, 30), drs_lap(2, 900), drs_lap(3, 20), drs_lap(4, 40), drs_lap(5, 25)]
    assert evaluate(drs, laps, {}) == (True, 3, 3)  # okrążenie 2 spóźnione (0,9 s), potem trzy dobre
    assert evaluate(drs, [drs_lap(1, None), drs_lap(2, 20, assist=True)], {}) == (False, 0, 3)  # pominięta; z asystą nie liczy się

    def ers_lap(n: int, in_corners_j: float, end_j: float, assist: bool = False) -> Lap:
        l = lap(n)
        l.ers_assist = assist
        deployed = 0.0
        for d in range(0, 5000, 10):
            if 600 <= d < 720:  # zakręt 1 w tests.synthetic (600–720 m)
                deployed += in_corners_j / 12
            elif 1000 <= d < 1400:
                deployed += 1_000_000 / 40
            l.ers.append(ErsSample(float(d), 4_000_000 - deployed if d < 4990 else end_j, deployed, 0.0, 1))
        return l

    ers = lesson("ers_straights")
    good, wasted, full = ers_lap(1, 0.0, 1_500_000), ers_lap(2, 900_000, 1_500_000), ers_lap(3, 0.0, 3_900_000)
    assert evaluate(ers, [good, wasted, full, ers_lap(4, 0.0, 1e6), ers_lap(5, 0.0, 1e6), ers_lap(6, 0.0, 1e6)], {}, track=track()) == (True, 3, 3)
    assert evaluate(ers, [good, ers_lap(2, 0.0, 1e6, assist=True)], {}, track=track()) == (False, 1, 3)
    assert evaluate(ers, [good], {}) == (False, 0, 3)  # bez toru nie ma stref hamowania, więc i oceny

    def tyre_lap(n: int, rear: int, wear: float) -> Lap:
        l = lap(n)
        for d in range(0, 5000, 25):
            w = wear * d / 5000
            l.tyres.append(TyreSample(float(d), (rear, rear, 95, 95), (rear, rear, 95, 95), (10 + w, 10 + w, 10, 10)))
        return l

    tyres = lesson("tyres_window")
    assert evaluate(tyres, [tyre_lap(1, 120, 1.0), tyre_lap(2, 98, 1.0), tyre_lap(3, 97, 1.0), tyre_lap(4, 96, 6.0), tyre_lap(5, 98, 1.0)], {}) == (False, 2, 3)
    assert evaluate(tyres, [tyre_lap(1, 98, 1.0), tyre_lap(2, 97, 1.0), tyre_lap(3, 96, 1.0)], {}) == (True, 3, 3)
    assert evaluate(tyres, [lap(1)], {}) == (False, 0, 3)  # bez próbek opon okrążenie nie liczy się
    assert {item.id for item in LESSONS} >= {"drs_zones", "ers_straights", "tyres_window"} and len(free_lessons()) == 4


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
    corner_texts = [t for t in said if ("Zakręt" in t or "Zakręty" in t) and not t.endswith("Prowadzę.")]  # bez wstępu prowadzenia
    # prowadzenie w lekcji gazu: tylko komendy o gazie, bez hamowania
    assert any(t in ("Pół gazu.", "Pełny gaz.") for t in said) and not any(t.endswith("hamulec.") or t in ("Pół hamulca.", "Puść gaz.") for t in said)
    assert corner_texts and all(("gaz" in t.lower() or "przyczepno" in t.lower()) for t in corner_texts), corner_texts  # lekcja gazu: bez uwag o hamowaniu
    explained = [t for t in said if "Każdy metr bez gazu" in t or "a bez kontroli trakcji auto może się obrócić" in t]
    assert len(explained) >= 1  # wyjaśnienie przy pierwszej uwadze danego typu
    rules_explained = sum(1 for t in said if "Każdy metr bez gazu" in t)
    assert rules_explained <= 1  # tylko przy pierwszym wystąpieniu
