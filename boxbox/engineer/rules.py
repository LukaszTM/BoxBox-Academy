"""Inżynier na radiu (tryb wyścigowy): reguły na zdarzeniach i zmianach stanu telemetrii.

Czysty Python: dostaje kolejne stany (TelemetryState) i zwraca komunikaty (id klipu + tekst).
Nie poprawia techniki jazdy (od tego jest trener); reaguje na wyścig: flagi, SC, DRS, pit,
opony, paliwo, uszkodzenia, kolizje, kary, odstępy, ostatnie okrążenia.
Teksty klipów: boxbox/engineer/phrases.py (eng_*).
"""
from dataclasses import dataclass, field

from boxbox.engineer.phrases import ENGINEER_TEXTS, LAPS_TEXTS, SECONDS_TEXTS, seconds_key
from boxbox.engineer.start import StartAnalyzer, StartReport
from boxbox.telemetry.event import Collision, Penalty
from boxbox.telemetry.state import TelemetryState

RACE_SESSION_TYPES = {15, 16, 17}  # wyścig, wyścig 2, wyścig 3
FIA_FLAG = {1: "green", 2: "blue", 3: "yellow", 4: "red"}
FRONT_WEAR_WARN = 60.0  # % zużycia opon przednich (średnia FL/FR)
REAR_WEAR_WARN = 60.0
WEAR_CRITICAL = 85.0
WING_DAMAGE_WARN = 25
WING_DAMAGE_BIG = 60
FLOOR_DAMAGE_WARN = 30
ENGINE_WARN = 80
GAP_CLOSE_MS = 1000  # w zasięgu DRS
GAP_SAFE_MS = 4000
FUEL_SHORT_LAPS = -0.3  # ujemne = brakuje paliwa
TYRE_COLD_C = 70  # średnia temperatura powierzchni opon
TYRE_HOT_C = 118
TYRE_WINDOW_LOW_C, TYRE_WINDOW_HIGH_C = 85, 110
FUEL_SPARE_LAPS = 2.0


COLLISION_RULES: dict[str, str] = {  # zasada tłumaczona po sytuacji (raport po wyścigu), według tego, co robił gracz w chwili kontaktu
    "braking": "w strefie hamowania: kto jest obok, ma prawo do miejsca; hamuj po swojej stronie toru i nie skręcaj w auto obok",
    "straight": "na prostej: broń się jedną zmianą toru i nie zjeżdżaj na auto, które już jest obok",
    "cornering": "w zakręcie: gdy auto jest przy twoim boku na wejściu, zostaw szerokość auta aż do wyjścia",
}
SEVERITY_NAMES = {0: "lekki", 1: "średni", 2: "ciężki"}


@dataclass(frozen=True)
class CollisionNote:
    """Jeden kontakt gracza: gdzie, z kim, co robił (do raportu po wyścigu, bez nowych klipów)."""
    lap: int
    distance_m: float
    other: str  # nazwa drugiego auta (puste, gdy nieznana)
    context: str  # braking | straight | cornering
    severity: int | None = None  # tylko 2026

    @property
    def rule(self) -> str:
        return COLLISION_RULES.get(self.context, COLLISION_RULES["cornering"])

    def line(self, number: int) -> str:
        sev = f", {SEVERITY_NAMES[self.severity]}" if self.severity in SEVERITY_NAMES else ""
        who = f" z {self.other}" if self.other else ""
        return f"Kontakt {number}: okrążenie {self.lap}, {self.distance_m:.0f} m{who}{sev}; {self.rule}."


@dataclass(frozen=True)
class RadioMessage:
    key: str  # klucz w ENGINEER_TEXTS (bez prefiksu eng_)
    text: str
    ids: tuple[str, ...]  # klipy do odtworzenia
    priority: int = 1  # 2 = pilne (SC, czerwona flaga, box), 1 = zwykłe, 0 = informacja


@dataclass
class Cooldowns:
    """Nie powtarzaj tego samego komunikatu przed upływem `seconds`."""

    seconds: dict[str, float] = field(default_factory=dict)
    last: dict[str, float] = field(default_factory=dict)

    def ready(self, key: str, now: float, default_s: float) -> bool:
        gap = self.seconds.get(key, default_s)
        return now - self.last.get(key, -1e9) >= gap

    def mark(self, key: str, now: float) -> None:
        self.last[key] = now


def _msg(key: str, extra_ids: tuple[str, ...] = (), extra_text: str = "", priority: int = 1) -> RadioMessage:
    text = ENGINEER_TEXTS[key] + (" " + extra_text if extra_text else "")
    return RadioMessage(key, text, (f"eng_{key}", *extra_ids), priority)


def laps_clip(n: int) -> tuple[str, str]:
    """(id klipu, tekst) dla liczby okrążeń; nieznane liczby zaokrąglane do dostępnych."""
    if n in LAPS_TEXTS:
        return f"eng_laps_{n}", LAPS_TEXTS[n]
    nearest = min(LAPS_TEXTS, key=lambda k: abs(k - n))
    return f"eng_laps_{nearest}", LAPS_TEXTS[nearest]


def seconds_clip(gap_s: float) -> tuple[str, str]:
    key = seconds_key(gap_s)
    return f"eng_sec_{key}", SECONDS_TEXTS[key]


class Engineer:
    """Trzyma poprzedni stan i mówi tylko o zmianach. `update(state, now)` -> lista komunikatów."""

    def __init__(self) -> None:
        self.cd = Cooldowns()
        self.said_hello = False
        self.prev_flag = 0
        self.prev_sc = 0
        self.prev_drs_allowed = False
        self.prev_position: int | None = None
        self.prev_lap: int | None = None
        self.prev_warnings = 0
        self.prev_penalties_s = 0.0
        self.prev_weather: int | None = None
        self.prev_tyre_age: int | None = None
        self.said_once: set[str] = set()
        self.events_seen = 0
        self.lights_out_at: float | None = None
        self.start = StartAnalyzer()
        self.start_report: StartReport | None = None
        self.collisions = 0
        self.collision_log: list[CollisionNote] = []
        self.penalties = 0
        self.prev_pits = 0

    def _once(self, key: str) -> bool:
        if key in self.said_once:
            return False
        self.said_once.add(key)
        return True

    def reset_tyre_flags(self) -> None:
        for k in ("tyres_front_wear", "tyres_rear_wear", "tyres_critical"):
            self.said_once.discard(k)

    @staticmethod
    def _collision_note(state: TelemetryState, coll: Collision, player_idx: int) -> CollisionNote:
        other_idx = coll.vehicle2_index if coll.vehicle1_index == player_idx else coll.vehicle1_index
        other = ""
        if state.participants is not None and 0 <= other_idx < len(state.participants.cars):
            other = state.participants.cars[other_idx].name
        lap = state.lap.player if state.lap is not None else None
        car = state.telemetry.player if state.telemetry is not None else None
        if car is not None and car.brake >= 0.1:
            context = "braking"
        elif car is not None and car.throttle >= 0.9 and abs(car.steer) < 0.1:
            context = "straight"
        else:
            context = "cornering"
        return CollisionNote(lap.current_lap_num if lap is not None else 0, max(0.0, lap.lap_distance) if lap is not None else 0.0, other, context, coll.severity)

    def update(self, state: TelemetryState, now: float) -> list[RadioMessage]:
        out: list[RadioMessage] = []
        lap = state.lap.player if state.lap is not None else None
        session = state.session
        status = state.status.player if state.status is not None else None
        damage = state.damage.player if getattr(state, "damage", None) is not None else None
        player_idx = state.lap.header.player_car_index if state.lap is not None else None

        if not self.said_hello and lap is not None:
            self.said_hello = True
            out.append(_msg("hello", priority=0))

        # zdarzenia (od ostatniego wywołania)
        for ev in state.events[self.events_seen:]:
            code = ev.code
            if code == "LGOT":
                self.lights_out_at = now
                self.start.lights_out(now, lap.grid_position if lap is not None else None)
                out.append(_msg("lights_out", priority=2))
            elif code == "STLG":
                if self._once("formation_lap"):
                    out.append(_msg("formation_lap", priority=0))
            elif code == "DRSE":
                if self.cd.ready("drs_enabled", now, 30):
                    self.cd.mark("drs_enabled", now)
                    out.append(_msg("drs_enabled"))
            elif code == "DRSD":
                if self.cd.ready("drs_disabled", now, 30):
                    self.cd.mark("drs_disabled", now)
                    out.append(_msg("drs_disabled"))
            elif code == "RDFL":
                out.append(_msg("flag_red", priority=2))
            elif code == "SCAR" and ev.details is not None:
                sc_type, ev_type = ev.details.safety_car_type, ev.details.event_type  # 0 none,1 SC,2 VSC,3 formation; 0 deployed,1 returning,2 returned,3 resume
                key = {(1, 0): "safety_car", (1, 1): "safety_car_in", (2, 0): "vsc", (2, 2): "vsc_end", (2, 3): "vsc_end", (1, 3): "flag_yellow_clear"}.get((sc_type, ev_type))
                if key and self.cd.ready(key, now, 20):
                    self.cd.mark(key, now)
                    out.append(_msg(key, priority=2))
            elif code == "COLL" and isinstance(ev.details, Collision) and player_idx is not None:
                if player_idx in (ev.details.vehicle1_index, ev.details.vehicle2_index) and self.cd.ready("collision", now, 10):
                    self.cd.mark("collision", now)
                    self.collisions += 1
                    self.collision_log.append(self._collision_note(state, ev.details, player_idx))
                    out.append(_msg("collision"))
            elif code == "PENA" and isinstance(ev.details, Penalty) and player_idx is not None and ev.details.vehicle_index == player_idx:
                if ev.details.time_s > 0 and self.cd.ready("penalty_time", now, 15):
                    self.cd.mark("penalty_time", now)
                    self.penalties += 1
                    out.append(_msg("penalty_time"))
            elif code in ("CHQF", "SEND"):
                if self._once("race_end"):
                    out.append(_msg("race_end", priority=0))
        self.events_seen = len(state.events)

        if session is None or lap is None:
            return out
        is_race = session.session_type in RACE_SESSION_TYPES
        # start: próbki gazu/prędkości/obrotów przez 5 s po światłach, raport po 1. okrążeniu
        if self.start.lights_out_s is not None and not self.start.done and state.telemetry is not None:
            car = state.telemetry.player
            if status is not None:
                self.start.max_rpm = status.max_rpm or self.start.max_rpm
            self.start.feed(now, car.throttle, car.speed_kmh, car.engine_rpm, lap.current_lap_num, lap.car_position)
            if self.start.done and self.start_report is None:
                self.start_report = self.start.report()
                if self.start_report is not None:
                    out.append(RadioMessage("start_report", self.start_report.text, (), 0))

        # flagi FIA dla gracza (z Car Status)
        if status is not None:
            flag = status.vehicle_fia_flags
            if flag != self.prev_flag:
                name = FIA_FLAG.get(flag)
                if name == "yellow" and self.cd.ready("flag_yellow", now, 15):
                    self.cd.mark("flag_yellow", now)
                    out.append(_msg("flag_yellow", priority=2))
                elif name == "blue" and self.cd.ready("flag_blue", now, 20):
                    self.cd.mark("flag_blue", now)
                    out.append(_msg("flag_blue"))
                elif name == "red":
                    out.append(_msg("flag_red", priority=2))
                elif self.prev_flag == 3 and flag in (0, 1) and self.cd.ready("flag_yellow_clear", now, 15):
                    self.cd.mark("flag_yellow_clear", now)
                    out.append(_msg("flag_yellow_clear"))
                self.prev_flag = flag
            # DRS dostępny (bez zdarzenia, np. po restarcie)
            if status.drs_allowed and not self.prev_drs_allowed and self.cd.ready("drs_enabled", now, 60):
                self.cd.mark("drs_enabled", now)
                out.append(_msg("drs_enabled"))
            self.prev_drs_allowed = bool(status.drs_allowed)
            # nowe opony po pit-stopie: kasuj ostrzeżenia
            if self.prev_tyre_age is not None and status.tyres_age_laps < self.prev_tyre_age:
                self.reset_tyre_flags()
            self.prev_tyre_age = status.tyres_age_laps
            # paliwo (tylko wyścig)
            if is_race and lap.current_lap_num > 1:
                if status.fuel_remaining_laps < FUEL_SHORT_LAPS and self.cd.ready("fuel_save", now, 120):
                    self.cd.mark("fuel_save", now)
                    out.append(_msg("fuel_save"))
                elif status.fuel_remaining_laps > FUEL_SPARE_LAPS and self._once("fuel_push") and lap.current_lap_num > 3:
                    out.append(_msg("fuel_push", priority=0))

        # safety car ze stanu sesji (gdy zdarzenie nie doszło)
        sc = session.safety_car_status
        if sc != self.prev_sc:
            key = {1: "safety_car", 2: "vsc"}.get(sc)
            if key and self.cd.ready(key, now, 20):
                self.cd.mark(key, now)
                out.append(_msg(key, priority=2))
            elif sc == 0 and self.prev_sc == 2 and self.cd.ready("vsc_end", now, 20):
                self.cd.mark("vsc_end", now)
                out.append(_msg("vsc_end", priority=2))
            self.prev_sc = sc

        # pogoda
        if self.prev_weather is not None and session.weather != self.prev_weather:
            if session.weather >= 3 and self.prev_weather < 3:
                out.append(_msg("rain_now", priority=2))
            elif session.weather < 3 and self.prev_weather >= 3:
                out.append(_msg("track_drying"))
        self.prev_weather = session.weather

        # okrążenia: okno pit-stopu, ostatnie okrążenia (wyścig)
        if lap.current_lap_num != self.prev_lap:
            n = lap.current_lap_num
            if is_race and session.total_laps > 0:
                left = session.total_laps - n + 1
                if left == 1 and self._once("last_lap"):
                    out.append(_msg("last_lap", priority=2))
                elif left == 3 and self._once("final_laps"):
                    out.append(_msg("final_laps"))
                if 0 < session.pit_stop_window_ideal_lap == n and self._once("pit_window_open"):
                    out.append(_msg("pit_window_open", priority=2))
                elif 0 < session.pit_stop_window_latest_lap == n and self._once("pit_this_lap") and lap.num_pit_stops == 0:
                    out.append(_msg("pit_this_lap", priority=2))
            self.prev_lap = n

        # pozycje (wyścig, nie na pierwszym okrążeniu)
        if is_race and lap.car_position:
            if self.prev_position is not None and lap.current_lap_num > 1 and lap.car_position != self.prev_position:
                key = "position_gained" if lap.car_position < self.prev_position else "position_lost"
                if self.cd.ready(key, now, 15):
                    self.cd.mark(key, now)
                    out.append(_msg(key, priority=0))
            self.prev_position = lap.car_position
            # odstępy
            if lap.car_position > 1 and 0 < lap.delta_to_car_in_front_ms < GAP_CLOSE_MS and self.cd.ready("gap_ahead_close", now, 60):
                self.cd.mark("gap_ahead_close", now)
                out.append(_msg("gap_ahead_close"))
            elif lap.car_position > 1 and lap.delta_to_car_in_front_ms >= GAP_CLOSE_MS and self.cd.ready("gap_ahead", now, 120) and lap.current_lap_num > 1:
                self.cd.mark("gap_ahead", now)
                clip, text = seconds_clip(lap.delta_to_car_in_front_ms / 1000)
                out.append(_msg("gap_ahead", (clip,), text, priority=0))
            behind = _car_behind(state, lap.car_position)
            if behind is not None and 0 < behind.delta_to_car_in_front_ms < GAP_CLOSE_MS and self.cd.ready("gap_behind_close", now, 60):
                self.cd.mark("gap_behind_close", now)
                out.append(_msg("gap_behind_close"))
            elif behind is not None and behind.delta_to_car_in_front_ms >= GAP_SAFE_MS and self.cd.ready("gap_safe", now, 180) and lap.current_lap_num > 2:
                self.cd.mark("gap_safe", now)
                out.append(_msg("gap_safe", priority=0))

        # temperatury opon (powierzchnia): poza pit lane, nie na 1. okrążeniu
        if state.telemetry is not None and not lap.pit_status and lap.current_lap_num > 1:
            temps = state.telemetry.player.tyres_surface_temperature
            avg = sum(temps) / 4
            if avg < TYRE_COLD_C and self.cd.ready("tyres_cold", now, 90):
                self.cd.mark("tyres_cold", now)
                out.append(_msg("tyres_cold"))
            elif avg > TYRE_HOT_C and self.cd.ready("tyres_hot", now, 90):
                self.cd.mark("tyres_hot", now)
                out.append(_msg("tyres_hot"))
            elif TYRE_WINDOW_LOW_C <= avg <= TYRE_WINDOW_HIGH_C and self._once("tyres_window"):
                out.append(_msg("tyres_window", priority=0))
        self.prev_pits = lap.num_pit_stops
        # kary i ostrzeżenia
        if lap.total_warnings > self.prev_warnings and self.cd.ready("penalty_warning", now, 30):
            self.cd.mark("penalty_warning", now)
            out.append(_msg("penalty_warning"))
        self.prev_warnings = lap.total_warnings

        # opony i uszkodzenia
        if damage is not None:
            rl, rr, fl, fr = damage.tyres_wear_percent
            front, rear = (fl + fr) / 2, (rl + rr) / 2
            if max(front, rear) >= WEAR_CRITICAL and self._once("tyres_critical"):
                out.append(_msg("tyres_critical", priority=2))
            elif front >= FRONT_WEAR_WARN and self._once("tyres_front_wear"):
                out.append(_msg("tyres_front_wear"))
            elif rear >= REAR_WEAR_WARN and self._once("tyres_rear_wear"):
                out.append(_msg("tyres_rear_wear"))
            wing = max(damage.front_left_wing_damage_percent, damage.front_right_wing_damage_percent)
            if wing >= WING_DAMAGE_BIG and self._once("damage_front_wing_big"):
                out.append(_msg("damage_front_wing_big", priority=2))
            elif wing >= WING_DAMAGE_WARN and self._once("damage_front_wing"):
                out.append(_msg("damage_front_wing"))
            if damage.rear_wing_damage_percent >= WING_DAMAGE_WARN and self._once("damage_rear_wing"):
                out.append(_msg("damage_rear_wing"))
            if damage.floor_damage_percent >= FLOOR_DAMAGE_WARN and self._once("damage_floor"):
                out.append(_msg("damage_floor"))
            if any(d >= 90 for d in damage.tyres_damage_percent) and self._once("puncture"):
                out.append(_msg("puncture", priority=2))
            if damage.engine_damage_percent >= ENGINE_WARN and self._once("engine_warn"):
                out.append(_msg("engine_warn", priority=2))
        return out


def _car_behind(state: TelemetryState, position: int):
    """Lap Data auta na pozycji o jeden niżej (jego delta do auta z przodu = odstęp do nas)."""
    if state.lap is None:
        return None
    for i, car in enumerate(state.lap.cars):
        if car.car_position == position + 1 and i != state.lap.header.player_car_index:
            return car
    return None
