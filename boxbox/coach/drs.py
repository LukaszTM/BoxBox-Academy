"""DRS: strefy z telemetrii, czas reakcji na zieloną lampkę, strefy bez włączenia.

Z pakietów: Car Status `drsAllowed` zapala się na początku strefy (i gaśnie po włączeniu albo na końcu
strefy), Car Telemetry `drs` mówi, czy skrzydło jest otwarte. Strefa w okrążeniu = od zapalenia lampki
do zamknięcia skrzydła (albo zgaśnięcia lampki bez włączenia). Strefa zaczęta przed linią mety (auto
wjeżdża na okrążenie z otwartym DRS) nie jest liczona. Z nagrań Time Trial: gracz włącza DRS 17–36 ms
po lampce (2–3 m), więc próg "za późno" jest wyraźnie wyżej.
"""
from dataclasses import dataclass

from boxbox.coach.lap_samples import DrsSample

LATE_MS = 500  # reakcja ponad pół sekundy = za późno (zwykła reakcja z nagrań: 20–40 ms)
MIN_ZONE_M = 30.0  # krótsze "strefy" to szum przy linii mety


@dataclass(frozen=True)
class DrsZone:
    number: int
    allowed_m: float
    allowed_ms: int
    activated_m: float | None  # None = nie włączył
    activated_ms: int | None
    end_m: float

    @property
    def reaction_ms(self) -> int | None:
        return None if self.activated_ms is None else max(0, self.activated_ms - self.allowed_ms)

    @property
    def lost_m(self) -> float | None:
        return None if self.activated_m is None else max(0.0, self.activated_m - self.allowed_m)


@dataclass(frozen=True)
class DrsLapReport:
    zones: tuple[DrsZone, ...]

    @property
    def missed(self) -> tuple[DrsZone, ...]:
        return tuple(z for z in self.zones if z.activated_ms is None)

    @property
    def late(self) -> tuple[DrsZone, ...]:
        return tuple(z for z in self.zones if z.reaction_ms is not None and z.reaction_ms > LATE_MS)

    @property
    def worst(self) -> DrsZone | None:
        """Strefa z największą stratą: pominięta przed spóźnioną."""
        if self.missed:
            return self.missed[0]
        return max(self.late, key=lambda z: z.reaction_ms or 0, default=None)


@dataclass(frozen=True)
class DrsAdvice:
    kind: str  # none | assist_on | no_zones | missed | late
    zone: DrsZone | None = None

    @property
    def clip(self) -> str | None:
        return f"misc_drs_{self.kind}" if self.kind in ("missed", "late") else None


def analyze_drs(samples: list[DrsSample]) -> DrsLapReport | None:
    if not samples:
        return None
    zones: list[DrsZone] = []
    inside = samples[0].allowed or samples[0].active  # strefa z poprzedniego okrążenia: pomijamy
    skip = inside
    allowed_at: DrsSample | None = None
    activated_at: DrsSample | None = None
    for s in samples:
        on = s.allowed or s.active
        if not inside and on:
            inside, skip = True, False
            allowed_at, activated_at = s, None
        if inside and not skip and s.active and activated_at is None:
            activated_at = s
        if inside and not on:
            inside = False
            if not skip and allowed_at is not None and s.distance_m - allowed_at.distance_m >= MIN_ZONE_M:
                zones.append(DrsZone(
                    len(zones) + 1, allowed_at.distance_m, allowed_at.lap_time_ms,
                    activated_at.distance_m if activated_at else None, activated_at.lap_time_ms if activated_at else None,
                    s.distance_m,
                ))
            skip = False
    # strefa otwarta na linii mety (np. Bahrajn: lampka 5300 m, skrzydło zamyka się na następnym okrążeniu):
    # liczy się, gdy włączenie już znamy; bez włączenia nie wiemy, czy je pominął
    if inside and not skip and allowed_at is not None and activated_at is not None:
        zones.append(DrsZone(len(zones) + 1, allowed_at.distance_m, allowed_at.lap_time_ms,
                             activated_at.distance_m, activated_at.lap_time_ms, samples[-1].distance_m))
    return DrsLapReport(tuple(zones))


def advise_drs(report: DrsLapReport | None, drs_assist: bool | None) -> DrsAdvice:
    """Jedna rada po okrążeniu: pominięta strefa przed spóźnionym włączeniem; z asystą DRS gra włącza sama."""
    if drs_assist:
        return DrsAdvice("assist_on")
    if report is None or not report.zones:
        return DrsAdvice("no_zones")
    worst = report.worst
    if worst is None:
        return DrsAdvice("none")
    return DrsAdvice("missed" if worst.activated_ms is None else "late", worst)
