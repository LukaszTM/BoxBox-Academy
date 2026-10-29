"""Strata w sektorach i konkretne polecenie na następne okrążenie.

Po okrążeniu trener mówi, w którym sektorze gracz traci najwięcej do swoich najlepszych sektorów
z tej sesji (kubełki „około pół sekundy” zamiast dokładnych liczb, bo to klipy), a do najważniejszej
uwagi dokłada jedno wykonalne polecenie: „na następnym okrążeniu zacznij hamować wcześniej,
o jakieś dwadzieścia metrów” (połowa różnicy do referencji, 5–20 m, jak cel na nakładce).
"""
from collections.abc import Sequence
from dataclasses import dataclass

from boxbox.coach.rules import Message

MIN_SECTOR_LOSS_MS = 200  # poniżej nie ma o czym mówić
LOSS_BUCKETS: tuple[tuple[int, str], ...] = (  # górna granica ms -> klucz klipu misc_loss_<key>
    (250, "0_2"), (400, "0_3"), (650, "0_5"), (900, "0_8"), (1250, "1"), (1750, "1_5"), (2500, "2"), (10**9, "3"),
)
LOSS_TEXTS: dict[str, str] = {
    "0_2": "około dwie dziesiąte.", "0_3": "około trzy dziesiąte.", "0_5": "około pół sekundy.", "0_8": "około osiem dziesiątych.",
    "1": "około sekundę.", "1_5": "około półtorej sekundy.", "2": "około dwie sekundy.", "3": "ponad trzy sekundy.",
}
SECTOR_TEXTS: dict[int, str] = {
    1: "Najwięcej tracisz w pierwszym sektorze,", 2: "Najwięcej tracisz w drugim sektorze,", 3: "Najwięcej tracisz w trzecim sektorze,",
}
NEXT_TEXTS: dict[str, str] = {
    "brake_earlier": "Na następnym okrążeniu zacznij hamować wcześniej, o jakieś",
    "brake_later": "Na następnym okrążeniu zacznij hamować później, o jakieś",
    "throttle_earlier": "Na następnym okrążeniu pełny gaz wcześniej, o jakieś",
}


@dataclass(frozen=True)
class SectorLoss:
    sector: int  # 1..3
    loss_ms: int

    @property
    def bucket(self) -> str:
        return next(key for limit, key in LOSS_BUCKETS if self.loss_ms < limit)


def best_sectors(laps_sectors: Sequence[tuple[int | None, int | None, int | None]]) -> tuple[int | None, int | None, int | None]:
    """Najlepszy czas każdego sektora z podanych okrążeń (tylko komplety)."""
    out: list[int | None] = [None, None, None]
    for secs in laps_sectors:
        if None in secs:
            continue
        for i, v in enumerate(secs):
            if v and (out[i] is None or v < out[i]):  # type: ignore[operator]
                out[i] = v
    return (out[0], out[1], out[2])


def sector_losses(lap: tuple[int | None, int | None, int | None], best: tuple[int | None, int | None, int | None]) -> list[SectorLoss]:
    out = []
    for i, (v, b) in enumerate(zip(lap, best), start=1):
        if v and b and v > b:
            out.append(SectorLoss(i, v - b))
    return out


def worst_sector(lap: tuple[int | None, int | None, int | None], best: tuple[int | None, int | None, int | None]) -> SectorLoss | None:
    losses = sector_losses(lap, best)
    worst = max(losses, key=lambda s: s.loss_ms, default=None)
    return worst if worst is not None and worst.loss_ms >= MIN_SECTOR_LOSS_MS else None


def sector_utterance(loss: SectorLoss) -> tuple[list[str], str]:
    return [f"misc_sector_{loss.sector}", f"misc_loss_{loss.bucket}"], f"{SECTOR_TEXTS[loss.sector]} {LOSS_TEXTS[loss.bucket]}"


def next_lap_step_m(value_m: int) -> int:
    """Mały, osiągalny krok: połowa różnicy, 5–20 m, zaokrąglona do 5."""
    return int(min(20, max(5, round(value_m / 2 / 5) * 5)))


def next_lap_directive(m: Message) -> tuple[list[str], str] | None:
    """Polecenie z liczbą dla uwag o metrach; dla pozostałych wskazówka reguły mówi już, co zrobić."""
    if m.value_m is None:
        return None
    if m.rule in ("brake_late", "brake_late_big"):
        key = "brake_earlier"
    elif m.rule == "brake_early":
        key = "brake_later"
    elif m.rule == "throttle_late":
        key = "throttle_earlier"
    else:
        return None
    step = next_lap_step_m(m.value_m)
    num = max(10, min(300, round(step / 10) * 10))  # klipy liczb są co 10 m
    from boxbox.voice.phrases import meters_text  # lokalnie: phrases importuje stąd teksty klipów

    return [f"misc_next_{key}", f"num_{num}"], f"{NEXT_TEXTS[key]} {meters_text(num)}"


def format_sector_delta(ms: int) -> str:
    return f"{'+' if ms > 0 else '−'}{abs(ms) / 1000:.2f}".replace(".", ",")
