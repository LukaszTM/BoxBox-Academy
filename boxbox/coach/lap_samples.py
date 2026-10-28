"""Dodatkowe próbki okrążenia poza prędkością i pedałami: DRS i opony (jak ErsSample dla baterii)."""
from dataclasses import dataclass

TYRE_SAMPLE_M = 25.0  # opony próbkowane co tyle metrów (temperatury zmieniają się wolno; ~230 próbek na okrążenie)
TYRE_ORDER = ("RL", "RR", "FL", "FR")  # kolejność kół w pakietach gry
TYRE_NAMES = {"RL": "lewy tył", "RR": "prawy tył", "FL": "lewy przód", "FR": "prawy przód"}


@dataclass(frozen=True)
class DrsSample:
    distance_m: float
    lap_time_ms: int
    allowed: bool  # gra pozwala włączyć (zielona lampka); gaśnie po włączeniu
    active: bool  # skrzydło otwarte


@dataclass(frozen=True)
class TyreSample:
    distance_m: float
    surface_c: tuple[int, int, int, int]  # RL, RR, FL, FR
    inner_c: tuple[int, int, int, int]
    wear_percent: tuple[float, float, float, float] | None  # z Car Damage; None, gdy pakiet nie przyszedł
