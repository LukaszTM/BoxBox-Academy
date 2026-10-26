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
    chars_v1 = sum(len(t) for k, t in entries.items() if not k.startswith("v2_"))
    assert chars_v1 < 5000, chars_v1  # część składana (v1) mieściła się w planie free
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


def test_corner_cases_and_v2_texts() -> None:
    from boxbox.voice.phrases import V2_TEXTS, bucket_m, corner_case, utterance, v2_id, v2_text
    assert corner_case("T4", "loc") == "zakręcie czwartym"
    assert corner_case("T4", "instr") == "zakrętem czwartym"
    assert corner_case("T4", "gen") == "zakrętu czwartego"
    assert corner_case("T1-T2", "loc") == "zakrętach pierwszym i drugim"
    assert corner_case("T1-T2", "gen") == "zakrętów pierwszego i drugiego"
    assert corner_case("T8-T10", "instr") == "zakrętami od ósmego do dziesiątego"
    assert corner_case("hamowanie 1", "loc") == "tym zakręcie"
    assert bucket_m(277) == 300 and bucket_m(60) == 50 and bucket_m(None) == 20 and bucket_m(130) == 150
    assert v2_text("brake_late", "T4", 55) == "Hamowanie za późno w zakręcie czwartym, o jakieś pięćdziesiąt metrów."
    assert v2_text("throttle_late", "T1-T2", 277) == "Pełny gaz za późno na wyjściu z zakrętów pierwszego i drugiego, o jakieś trzysta metrów."
    assert v2_text("brake_release", "T11") == "Hamulec puszczony naraz przed zakrętem jedenastym."
    assert v2_text("grip_lost_throttle", "T13-T14") == "Utrata przyczepności w zakrętach trzynastym i czternastym."
    assert v2_id("grip_lost_entry", "T13-T14") == v2_id("grip_lost_throttle", "T13-T14") == "v2_grip_lost_t13_14"
    assert v2_id("brake_late", "T4", 55) == "v2_brake_late_t4_50" and v2_id("brake_release", "T11") == "v2_brake_release_t11"
    entries = catalog(track_corner_names())
    v2 = {k: v for k, v in entries.items() if k.startswith("v2_")}
    names = len(track_corner_names()) + 1
    numbered = sum(1 for tpl in V2_TEXTS.values() if "{num}" in tpl)
    assert len(v2) == numbered * names * 6 + (len(V2_TEXTS) - numbered) * names
    total = sum(len(t) for t in entries.values())
    assert total < 50_000, total  # Creator: 100 000 znaków/miesiąc, zostaje zapas na inżyniera
    # utterance: v2 gdy klip jest, inaczej v1
    late = Message(2, 1, "T4", "brake_late", "p", "h", 1.0, value_m=50)
    ids, text = utterance(late, lambda i: i.startswith("v2_"))
    assert ids == ["v2_brake_late_t4_50", "rule_brake_late_b"] and text.startswith("Hamowanie za późno w zakręcie czwartym")
    ids, text = utterance(late, lambda i: i.startswith("v2_"), short=True)
    assert ids == ["v2_brake_late_t4_50"] and text.endswith("pięćdziesiąt metrów.")
    ids, text = utterance(late, None)
    assert ids == ["corner_t4", "rule_brake_late_a", "num_50", "rule_brake_late_b"] and text.startswith("Zakręt czwarty.")
    gear = Message(2, 3, "T6", "gear_low", "p", "h", 0.1, gear=4)
    ids, text = utterance(gear, lambda i: True)
    assert ids == ["v2_gear_low_t6", "gear_4"] and text == "Za niski bieg w zakręcie szóstym. W apeksie czwarty bieg."
    assert all(i in entries for i in ids)
