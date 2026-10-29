"""Strata w sektorach i polecenie na następne okrążenie (po okrążeniu)."""
from boxbox.coach.rules import Message
from boxbox.coach.sectors import (
    SectorLoss, best_sectors, format_sector_delta, next_lap_directive, next_lap_step_m, sector_losses, sector_utterance, worst_sector,
)
from boxbox.voice.phrases import catalog


def test_best_sectors_and_losses() -> None:
    best = best_sectors([(30_000, 31_000, 29_000), (29_500, 32_000, 28_900), (None, 20_000, 20_000)])  # niekomplet pominięty
    assert best == (29_500, 31_000, 28_900)
    losses = sector_losses((29_700, 31_600, 28_900), best)
    assert [(s.sector, s.loss_ms) for s in losses] == [(1, 200), (2, 600)]
    worst = worst_sector((29_700, 31_600, 28_900), best)
    assert worst == SectorLoss(2, 600) and worst.bucket == "0_5"
    assert worst_sector((29_600, 31_100, 28_950), best) is None  # straty poniżej 0,2 s: cicho
    assert worst_sector((None, 40_000, 40_000), best) is None or True  # brak S1 nie wywala
    assert worst_sector((29_500, 31_000, 28_900), (None, None, None)) is None  # pierwsze okrążenie: nie ma do czego porównać


def test_sector_utterance_and_buckets() -> None:
    ids, text = sector_utterance(SectorLoss(2, 600))
    assert ids == ["misc_sector_2", "misc_loss_0_5"] and text == "Najwięcej tracisz w drugim sektorze, około pół sekundy."
    assert SectorLoss(1, 200).bucket == "0_2" and SectorLoss(3, 1_100).bucket == "1" and SectorLoss(3, 5_000).bucket == "3"
    entries = catalog()
    for n in (1, 2, 3):
        assert f"misc_sector_{n}" in entries
    for key in ("0_2", "0_3", "0_5", "0_8", "1", "1_5", "2", "3"):
        assert f"misc_loss_{key}" in entries
    assert format_sector_delta(123) == "+0,12" and format_sector_delta(-1_050) == "−1,05"


def test_next_lap_directive() -> None:
    assert next_lap_step_m(50) == 20 and next_lap_step_m(12) == 5 and next_lap_step_m(28) == 15
    m = Message(4, 3, "T4", "brake_late", "p", "h", 1.2, value_m=50)
    ids, text = next_lap_directive(m)  # type: ignore[misc]
    assert ids == ["misc_next_brake_earlier", "num_20"] and text == "Na następnym okrążeniu zacznij hamować wcześniej, o jakieś dwadzieścia metrów."
    assert next_lap_directive(Message(4, 3, "T4", "brake_early", "p", "h", 0.5, value_m=12))[0] == ["misc_next_brake_later", "num_10"]  # 5 m -> klip 10 m
    assert next_lap_directive(Message(4, 3, "T4", "throttle_late", "p", "h", 0.5, value_m=30))[0] == ["misc_next_throttle_earlier", "num_20"]
    assert next_lap_directive(Message(4, 3, "T4", "brake_release", "p", "h", 0.5)) is None  # bez metrów: wskazówka reguły wystarcza
    entries = catalog()
    assert all(i in entries for i in ids)
