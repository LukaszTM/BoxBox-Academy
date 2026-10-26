from pathlib import Path

from boxbox.coach.rules import Message
from boxbox.voice.phrases import (
    RULE_TEXTS, catalog, compose, corner_key, corner_text, gear_text, meters_text, track_corner_names,
)


def test_corner_texts() -> None:
    assert corner_text("T4") == "Zakręt czwarty."
    assert corner_text("T9-T10") == "Zakręty dziewiąty i dziesiąty."
    assert corner_text("T1-T3") == "Zakręty od pierwszego do trzeciego."
    assert corner_text("T16-T18") == "Zakręty od szesnastego do osiemnastego."
    assert corner_text("Z3") == "Ten zakręt."
    assert corner_key("T9-T10") == "t9_10" and corner_key("T4") == "t4" and corner_key("hamowanie 1") == "zone"


def test_numbers_and_gears() -> None:
    assert meters_text(10) == "dziesięć metrów."
    assert meters_text(50) == "pięćdziesiąt metrów."
    assert meters_text(100) == "sto metrów."
    assert meters_text(210) == "dwieście dziesięć metrów."
    assert meters_text(300) == "trzysta metrów."
    assert gear_text(2) == "W apeksie drugi bieg."


def test_catalog_covers_rules_tracks_and_fits_free_plan() -> None:
    names = track_corner_names()
    assert {"T1-T2", "T9-T10", "T16-T18", "T1-T3", "T8-T10"} <= set(names)
    entries = catalog(names)
    for name in names:
        assert f"corner_{corner_key(name)}" in entries
    for rule in RULE_TEXTS:
        assert f"rule_{rule}_a" in entries
    chars = sum(len(t) for t in entries.values())
    assert chars < 5000, chars  # plan free ElevenLabs: 10 000 znaków miesięcznie, zostaje zapas na inżyniera
    texts = list(entries.values())
    assert len(texts) - len(set(texts)) <= 1  # jedyny powtórzony tekst: "Utrata przyczepności." w dwóch wariantach


def test_compose_messages() -> None:
    late = Message(2, 1, "T1-T2", "brake_late", "p", "h", 1.0, value_m=50)
    assert compose(late) == ["corner_t1_2", "rule_brake_late_a", "num_50", "rule_brake_late_b"]
    big = Message(2, 6, "T11", "brake_late", "p", "h", 5.0, value_m=210, variant="big")
    assert compose(big) == ["corner_t11", "rule_brake_late_big_a", "num_210", "rule_brake_late_big_b"]
    grip = Message(2, 4, "T13-T14", "grip_lost", "p", "h", 3.0, variant="throttle")
    assert compose(grip) == ["corner_t13_14", "rule_grip_lost_throttle_a", "rule_grip_lost_throttle_b"]
    gear = Message(2, 3, "T6", "gear_low", "p", "h", 0.1, gear=4)
    assert compose(gear) == ["corner_t6", "rule_gear_low_a", "gear_4"]
    release = Message(2, 1, "T1-T3", "brake_release", "p", "h", 1.0)
    assert compose(release) == ["corner_t1_3", "rule_brake_release_a", "rule_brake_release_b"]
    entries = catalog(track_corner_names())
    for m in (late, big, grip, gear, release):
        assert all(clip in entries for clip in compose(m))


def test_rules_fill_value_fields(monza) -> None:
    from boxbox.coach.corners import analyze_lap
    from boxbox.coach.rules import evaluate_lap, pick_top
    lap, ref = monza.lap(4), monza.lap(6)
    top = pick_top(evaluate_lap(lap, analyze_lap(lap, monza.track), analyze_lap(ref, monza.track), monza.track))
    first = top[0]
    assert first.rule == "brake_late" and first.variant == "big" and first.value_m == 290
    entries = catalog(track_corner_names())
    assert all(clip in entries for m in top for clip in compose(m))


def test_spoken_text_matches_clips() -> None:
    from boxbox.voice.phrases import spoken_text
    late = Message(2, 1, "T1-T2", "brake_late", "Hamowanie za późno w T1-T2, o 277 m.", "h", 1.0, value_m=280)
    assert spoken_text(late) == (
        "Zakręty pierwszy i drugi. Hamowanie za późno, o jakieś dwieście osiemdziesiąt metrów. "
        "Zacznij hamować wcześniej i puszczaj pedał stopniowo."
    )
    assert spoken_text(late, short=True) == "Zakręty pierwszy i drugi. Hamowanie za późno, o jakieś dwieście osiemdziesiąt metrów."
    gear = Message(2, 3, "T6", "gear_low", "p", "h", 0.1, gear=4)
    assert spoken_text(gear) == "Zakręt szósty. Za niski bieg. W apeksie czwarty bieg."
