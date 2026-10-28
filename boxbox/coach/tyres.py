"""Opony: temperatury i zużycie na okrążenie, prognoza żywotności zestawu, rada po okrążeniu.

Progi bezwzględne okna temperatur różnią się między mieszankami i w nagraniach Time Trial powierzchnia
bywa sztucznie stała, więc rady opierają się na różnicach: tył względem przodu, lewa względem prawej,
zużycie na okrążenie. Okno (TYRE_WINDOW) jest tylko w raporcie, do okna i PDF. Do weryfikacji na żywo.
"""
import statistics
from dataclasses import dataclass

from boxbox.coach.lap_samples import TYRE_NAMES, TYRE_ORDER, TyreSample

TYRE_WINDOW = (85, 110)  # °C powierzchni; orientacyjnie, do raportu
REAR_HOT_DELTA_C = 12  # tył cieplejszy od przodu o tyle = przegrzewasz tył na wyjściach
FRONT_HOT_DELTA_C = 12  # przód cieplejszy od tyłu = za dużo kierownicy / wjeżdżasz za szybko
SIDE_DELTA_C = 15  # jedna strona dużo cieplejsza (normalne na torach z zakrętami w jedną stronę; rada tylko gdy duża)
WEAR_FAST_PERCENT = 4.0  # zużycie powyżej tylu % na okrążenie = szybko
WEAR_UNEVEN_PERCENT = 8.0  # różnica zużycia między kołami
WEAR_LIMIT_PERCENT = 70.0  # od tego zużycia opona wyraźnie traci przyczepność (prognoza "ile okrążeń")


@dataclass(frozen=True)
class TyreLapReport:
    avg_surface_c: tuple[float, float, float, float]  # RL, RR, FL, FR
    avg_inner_c: tuple[float, float, float, float]
    wear_start: tuple[float, float, float, float] | None
    wear_end: tuple[float, float, float, float] | None
    samples: int

    @property
    def wear_lap(self) -> tuple[float, float, float, float] | None:
        if self.wear_start is None or self.wear_end is None:
            return None
        return tuple(max(0.0, e - s) for s, e in zip(self.wear_start, self.wear_end))  # type: ignore[return-value]

    @property
    def rear_c(self) -> float:
        return (self.avg_surface_c[0] + self.avg_surface_c[1]) / 2

    @property
    def front_c(self) -> float:
        return (self.avg_surface_c[2] + self.avg_surface_c[3]) / 2

    @property
    def left_c(self) -> float:
        return (self.avg_surface_c[0] + self.avg_surface_c[2]) / 2

    @property
    def right_c(self) -> float:
        return (self.avg_surface_c[1] + self.avg_surface_c[3]) / 2

    @property
    def hottest(self) -> str:
        return TYRE_ORDER[max(range(4), key=lambda i: self.avg_surface_c[i])]

    @property
    def in_window(self) -> bool:
        avg = statistics.fmean(self.avg_surface_c)
        return TYRE_WINDOW[0] <= avg <= TYRE_WINDOW[1]


@dataclass(frozen=True)
class TyreAdvice:
    kind: str  # none | rear_hot | front_hot | side_hot | wear_fast | wear_uneven
    detail: str = ""  # np. nazwa koła

    @property
    def clip(self) -> str | None:
        return f"misc_tyres_{self.kind}" if self.kind != "none" else None


def analyze_tyres(samples: list[TyreSample]) -> TyreLapReport | None:
    if len(samples) < 2:
        return None
    surface = tuple(statistics.fmean(s.surface_c[i] for s in samples) for i in range(4))
    inner = tuple(statistics.fmean(s.inner_c[i] for s in samples) for i in range(4))
    with_wear = [s for s in samples if s.wear_percent is not None]
    start = with_wear[0].wear_percent if with_wear else None
    end = with_wear[-1].wear_percent if with_wear else None
    return TyreLapReport(surface, inner, start, end, len(samples))  # type: ignore[arg-type]


def forecast_laps(report: TyreLapReport, limit: float = WEAR_LIMIT_PERCENT) -> int | None:
    """Ile pełnych okrążeń zostało, zanim najbardziej zużyte koło dojdzie do limitu, przy tym tempie zużycia."""
    wear = report.wear_lap
    if wear is None or report.wear_end is None:
        return None
    worst = max(range(4), key=lambda i: report.wear_end[i])  # type: ignore[index]
    rate = wear[worst]
    if rate <= 0:
        return None
    return int(max(0.0, limit - report.wear_end[worst]) // rate)


def advise_tyres(report: TyreLapReport | None) -> TyreAdvice:
    """Jedna rada po okrążeniu, od najdroższej: zużycie, potem temperatury."""
    if report is None:
        return TyreAdvice("none")
    wear = report.wear_lap
    if wear is not None:
        if max(wear) >= WEAR_FAST_PERCENT:
            return TyreAdvice("wear_fast", TYRE_NAMES[TYRE_ORDER[max(range(4), key=lambda i: wear[i])]])
        if report.wear_end is not None and max(report.wear_end) - min(report.wear_end) >= WEAR_UNEVEN_PERCENT:
            return TyreAdvice("wear_uneven", TYRE_NAMES[TYRE_ORDER[max(range(4), key=lambda i: report.wear_end[i])]])  # type: ignore[index]
    if report.rear_c - report.front_c >= REAR_HOT_DELTA_C:
        return TyreAdvice("rear_hot")
    if report.front_c - report.rear_c >= FRONT_HOT_DELTA_C:
        return TyreAdvice("front_hot")
    if abs(report.left_c - report.right_c) >= SIDE_DELTA_C:
        return TyreAdvice("side_hot", "lewa" if report.left_c > report.right_c else "prawa")
    return TyreAdvice("none")
