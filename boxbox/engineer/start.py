"""Analiza startu wyścigu: czas reakcji od zgaszenia świateł, uślizg kół, pozycje do końca 1. okrążenia.

Dane: zdarzenie LGOT (światła zgasły) + próbki Car Telemetry (gaz, prędkość, obroty) + Lap Data
(pozycja startowa i po 1. okrążeniu). Zero UI: zwraca raport z tekstem po polsku.
"""
from dataclasses import dataclass, field

GOOD_REACTION_S = 0.30
SLOW_REACTION_S = 0.60
WHEELSPIN_RPM_RATIO = 0.85  # obroty blisko maksimum przy małej prędkości = koła w uślizgu
WHEELSPIN_SPEED_KMH = 40


@dataclass
class StartSample:
    t_s: float  # sekundy od zgaszenia świateł
    throttle: float
    speed_kmh: int
    rpm: int


@dataclass
class StartReport:
    reaction_s: float | None
    wheelspin_s: float  # łączny czas uślizgu w pierwszych 3 s
    speed_after_3s: int | None
    grid_position: int | None
    position_after_lap1: int | None
    text: str = ""
    ok: bool = True


@dataclass
class StartAnalyzer:
    max_rpm: int = 13000
    lights_out_s: float | None = None
    samples: list[StartSample] = field(default_factory=list)
    grid_position: int | None = None
    position_after_lap1: int | None = None
    done: bool = False

    def lights_out(self, now_s: float, grid_position: int | None) -> None:
        self.lights_out_s = now_s
        self.grid_position = grid_position
        self.samples = []
        self.done = False

    def feed(self, now_s: float, throttle: float, speed_kmh: int, rpm: int, lap_num: int, position: int | None) -> None:
        if self.lights_out_s is None or self.done:
            return
        t = now_s - self.lights_out_s
        if t <= 5.0:
            self.samples.append(StartSample(t, throttle, speed_kmh, rpm))
        if lap_num >= 2 and self.position_after_lap1 is None:
            self.position_after_lap1 = position
            self.done = True

    def report(self) -> StartReport | None:
        if self.lights_out_s is None or not self.samples:
            return None
        reaction = next((s.t_s for s in self.samples if s.throttle >= 0.2), None)
        spin = 0.0
        prev_t = self.samples[0].t_s
        for s in self.samples:
            if s.t_s <= 3.0 and s.rpm >= WHEELSPIN_RPM_RATIO * self.max_rpm and s.speed_kmh < WHEELSPIN_SPEED_KMH and s.throttle > 0.8:
                spin += max(0.0, s.t_s - prev_t)
            prev_t = s.t_s
        after3 = next((s.speed_kmh for s in self.samples if s.t_s >= 3.0), None)
        parts = []
        ok = True
        if reaction is None:
            parts.append("nie ruszyłeś z gazem w pierwszych 5 sekundach")
            ok = False
        elif reaction <= GOOD_REACTION_S:
            parts.append(f"reakcja {reaction:.2f} s, bardzo dobrze")
        elif reaction <= SLOW_REACTION_S:
            parts.append(f"reakcja {reaction:.2f} s, w porządku; patrz na światła, nie na auta obok")
        else:
            parts.append(f"reakcja {reaction:.2f} s, za wolno; gaz w momencie zgaśnięcia świateł")
            ok = False
        if spin >= 0.5:
            parts.append(f"uślizg kół przez {spin:.1f} s, mniej gazu w pierwszej sekundzie")
            ok = False
        elif spin > 0:
            parts.append("lekki uślizg, dawkuj gaz do około 70% na pierwsze metry")
        if self.grid_position and self.position_after_lap1:
            diff = self.grid_position - self.position_after_lap1
            if diff > 0:
                parts.append(f"po pierwszym okrążeniu {diff} {'pozycja' if diff == 1 else 'pozycje'} do przodu")
            elif diff < 0:
                parts.append(f"po pierwszym okrążeniu {-diff} {'pozycja' if diff == -1 else 'pozycje'} do tyłu; zostaw miejsce w pierwszym zakręcie")
                ok = False
            else:
                parts.append("pozycja po pierwszym okrążeniu utrzymana")
        return StartReport(reaction, spin, after3, self.grid_position, self.position_after_lap1, "Start: " + "; ".join(parts) + ".", ok)
