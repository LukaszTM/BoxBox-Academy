"""Analiza ERS na okrążeniu: gdzie deploy poszedł, ile zostało w baterii, czy się marnuje.

Z nagrań: z włączoną asystą ERS gra sama rozdziela deploy (prawie wszystko na
prostych, bateria 95-100%, odzysk ~4 MJ > deploy ~1 MJ na okrążenie), więc nie
ma czego poprawiać; trener mówi o ERS tylko przy wyłączonej asyście. W Time Trial
bateria jest zawsze pełna (tryb hotlap), analiza nie ma sensu.
"""
from dataclasses import dataclass

from boxbox.coach.ers_sample import ErsSample
from boxbox.coach.laps import Lap
from boxbox.tracks.model import Track, corner_at

ERS_MAX_J = 4_000_000.0
FULL_AT_FINISH_RATIO = 0.9  # bateria na mecie powyżej 90% = niewykorzystana energia
WASTED_IN_CORNERS_RATIO = 0.25  # ponad 25% deployu w strefach hamowania = marnowanie


@dataclass(frozen=True)
class ErsLapReport:
    lap: int
    store_start_j: float
    store_end_j: float
    deployed_j: float
    harvested_j: float
    deployed_in_corners_j: float
    deployed_on_straights_j: float
    modes: tuple[int, ...]

    @property
    def store_end_ratio(self) -> float:
        return self.store_end_j / ERS_MAX_J

    @property
    def wasted_ratio(self) -> float:
        total = self.deployed_in_corners_j + self.deployed_on_straights_j
        return self.deployed_in_corners_j / total if total > 0 else 0.0


@dataclass(frozen=True)
class ErsAdvice:
    kind: str  # "assist_on", "unused_battery", "wasted_in_corners", "ok", "no_data"
    text: str
    weight: float = 0.0


def analyze_ers(lap: Lap, samples: list[ErsSample], track: Track) -> ErsLapReport | None:
    """Rozkład deployu na strefy hamowania i proste; None, gdy brak próbek."""
    rows = [s for s in samples if s.distance_m >= 0]
    if len(rows) < 2:
        return None
    in_corners = on_straights = 0.0
    prev = rows[0]
    for s in rows[1:]:
        delta = max(0.0, s.deployed_j - prev.deployed_j)
        if corner_at(track, s.distance_m) is not None:
            in_corners += delta
        else:
            on_straights += delta
        prev = s
    return ErsLapReport(
        lap=lap.number, store_start_j=rows[0].store_j, store_end_j=rows[-1].store_j,
        deployed_j=rows[-1].deployed_j, harvested_j=rows[-1].harvested_j,
        deployed_in_corners_j=in_corners, deployed_on_straights_j=on_straights,
        modes=tuple(sorted({s.deploy_mode for s in rows})),
    )


def advise_ers(report: ErsLapReport | None, ers_assist: bool | None, last_lap: bool = False) -> ErsAdvice:
    if report is None:
        return ErsAdvice("no_data", "Brak danych o baterii.")
    if ers_assist:
        return ErsAdvice("assist_on", "Asysta ERS rozdziela baterię za ciebie; wyłącz ją, gdy zdejmiesz TC i ABS.")
    if report.wasted_ratio >= WASTED_IN_CORNERS_RATIO and report.deployed_j > 100_000:
        return ErsAdvice(
            "wasted_in_corners",
            f"Jedna czwarta deployu poszła w zakrętach. Używaj baterii na prostych, zaraz po wyjściu z zakrętu.",
            0.6,
        )
    if report.store_end_ratio >= FULL_AT_FINISH_RATIO:
        where = "Na ostatnim okrążeniu wciśnij wszystko, co zostało." if last_lap else "Masz zapas na wyjściach z wolnych zakrętów."
        return ErsAdvice("unused_battery", f"Bateria na mecie {report.store_end_ratio * 100:.0f} procent. {where}", 0.4)
    return ErsAdvice("ok", "Bateria użyta dobrze.")
