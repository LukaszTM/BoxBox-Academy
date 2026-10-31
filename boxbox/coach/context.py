"""Warunki okrążenia i uczciwe porównanie do mistrza.

Duch z rankingu jedzie w Time Trial: równe osiągi, miękkie opony, minimum paliwa, bez uszkodzeń.
Gracz w treningu ma więcej paliwa, inną mieszankę, zużyte opony, czasem uszkodzone skrzydło albo deszcz.
Ten moduł zbiera te warunki z telemetrii (kontekst okrążenia), mówi, czy porównanie w ogóle ma sens,
i rozbija stratę do mistrza na część z warunków i część z jazdy.

Współczynniki to reguły kciuka z F1, nie wartości z gry: oznaczone jako orientacyjne i zebrane
w jednym miejscu do strojenia. Asysty nie dostają sekund, tylko etykietę; model zakrętów i tak jest
liczony osobno na każdy krok asyst.
"""
from dataclasses import dataclass, field

from boxbox.coach.laps import Lap

FUEL_S_PER_KG = 0.03  # orientacyjnie: każdy kilogram paliwa to ok. 0,03 s na okrążeniu
COMPOUND_PENALTY_S: dict[str, float] = {"soft": 0.0, "medium": 0.6, "hard": 1.2}  # względem miękkiej, orientacyjnie
WEAR_FREE_PERCENT = 30.0  # do tego zużycia opona nie dostaje poprawki
WEAR_S_PER_PERCENT = 0.02  # powyżej: ok. 0,02 s na każdy procent zużycia
WEAR_LIMIT_PERCENT = 60.0  # powyżej: porównanie bez sensu
DAMAGE_LIMIT_PERCENT = 10  # skrzydło/podłoga uszkodzone powyżej: porównanie bez sensu
RAIN_WEATHER = 3  # 3 lekki deszcz, 4 ulewa, 5 burza
MASTER_FUEL_KG = 5.0  # Time Trial: minimalne paliwo
COMPOUND_PL = {"soft": "miękkie", "medium": "średnie", "hard": "twarde", "inter": "międzyopony", "wet": "deszczowe", "unknown": "nieznane"}


@dataclass(frozen=True)
class LapContext:
    fuel_kg: float | None = None  # paliwo na początku okrążenia
    compound: str = "unknown"  # soft | medium | hard | inter | wet | unknown
    tyre_age_laps: int | None = None
    wear_percent: float | None = None  # największe zużycie z czterech kół na końcu okrążenia
    damage_percent: int = 0  # największe uszkodzenie skrzydeł/podłogi
    weather: int | None = None
    track_temp_c: int | None = None
    session_type: int | None = None
    traction_control: int | None = None
    abs_on: bool | None = None
    gearbox: int | None = None

    @property
    def assists_label(self) -> str:
        parts = []
        if self.gearbox == 3:
            parts.append("automat")
        if self.traction_control:
            parts.append("TC " + ("pełna" if self.traction_control == 2 else "średnia"))
        if self.abs_on:
            parts.append("ABS")
        return ", ".join(parts) if parts else "bez asyst"


MASTER_CONTEXT = LapContext(fuel_kg=MASTER_FUEL_KG, compound="soft", tyre_age_laps=0, wear_percent=0.0, damage_percent=0, weather=0)


def lap_context(lap: Lap) -> LapContext:
    wear = None
    if lap.tyres and lap.tyres[-1].wear_percent is not None:
        wear = max(lap.tyres[-1].wear_percent)
    return LapContext(
        fuel_kg=lap.fuel_kg, compound=lap.compound or "unknown", tyre_age_laps=lap.tyre_age_laps, wear_percent=wear,
        damage_percent=lap.damage_percent, weather=lap.weather, track_temp_c=lap.track_temp_c, session_type=lap.session_type,
        traction_control=lap.traction_control, abs_on=lap.abs_on, gearbox=lap.gearbox,
    )


def comparable(ctx: LapContext) -> tuple[bool, str]:
    """Czy okrążenie da się uczciwie porównać z mistrzem; gdy nie, powód po polsku."""
    if ctx.weather is not None and ctx.weather >= RAIN_WEATHER:
        return False, "deszcz: porównanie z najlepszymi wstrzymane"
    if ctx.compound in ("inter", "wet"):
        return False, "opony deszczowe: porównanie z najlepszymi wstrzymane"
    if ctx.damage_percent > DAMAGE_LIMIT_PERCENT:
        return False, f"uszkodzenia {ctx.damage_percent} %: porównanie z najlepszymi wstrzymane"
    if ctx.wear_percent is not None and ctx.wear_percent > WEAR_LIMIT_PERCENT:
        return False, f"opony zużyte w {ctx.wear_percent:.0f} %: porównanie z najlepszymi wstrzymane"
    return True, ""


@dataclass(frozen=True)
class Adjustment:
    raw_ms: int  # strata zmierzona
    items: tuple[tuple[str, int], ...] = field(default_factory=tuple)  # (etykieta, ms wyjaśnione warunkami)
    labels: tuple[str, ...] = field(default_factory=tuple)  # etykiety bez sekund (asysty)

    @property
    def conditions_ms(self) -> int:
        return sum(ms for _, ms in self.items)

    @property
    def adjusted_ms(self) -> int:
        """Strata w podobnych warunkach: to, co zostaje po odjęciu paliwa, opon i zużycia (nie mniej niż 0)."""
        return max(0, self.raw_ms - self.conditions_ms)

    def describe(self) -> str:
        parts = [f"{label} +{ms / 1000:.1f} s".replace(".", ",") for label, ms in self.items if ms > 0]
        parts += list(self.labels)
        return " · ".join(parts) if parts else "warunki jak w Time Trial"


def adjust(raw_ms: int, ctx: LapContext, master: LapContext = MASTER_CONTEXT) -> Adjustment:
    items: list[tuple[str, int]] = []
    if ctx.fuel_kg is not None and master.fuel_kg is not None and ctx.fuel_kg > master.fuel_kg + 1.0:
        items.append((f"paliwo {ctx.fuel_kg:.0f} kg", int(round((ctx.fuel_kg - master.fuel_kg) * FUEL_S_PER_KG * 1000))))
    penalty = COMPOUND_PENALTY_S.get(ctx.compound, 0.0) - COMPOUND_PENALTY_S.get(master.compound, 0.0)
    if penalty > 0:
        items.append((f"opony {COMPOUND_PL.get(ctx.compound, ctx.compound)}", int(round(penalty * 1000))))
    if ctx.wear_percent is not None and ctx.wear_percent > WEAR_FREE_PERCENT:
        items.append((f"zużycie {ctx.wear_percent:.0f} %", int(round((ctx.wear_percent - WEAR_FREE_PERCENT) * WEAR_S_PER_PERCENT * 1000))))
    labels = []
    if ctx.assists_label != "bez asyst":
        labels.append(f"asysty: {ctx.assists_label}")
    return Adjustment(raw_ms, tuple(items), tuple(labels))
