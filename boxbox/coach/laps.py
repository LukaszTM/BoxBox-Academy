"""Cięcie strumienia pakietów na okrążenia z próbkami jazdy auta gracza."""
from collections import Counter
from dataclasses import dataclass, field

from boxbox.coach.ers_sample import ErsSample
from boxbox.telemetry.car_status import VISUAL_TYRE_NAMES
from boxbox.coach.lap_samples import TYRE_SAMPLE_M, DrsSample, TyreSample
from boxbox.telemetry.header import PacketId
from boxbox.telemetry.state import TelemetryState


@dataclass(frozen=True)
class Sample:
    distance_m: float  # dystans od linii mety (lap_distance)
    lap_time_ms: int
    speed_kmh: int
    throttle: float
    brake: float
    gear: int
    steer: float


@dataclass
class Lap:
    number: int
    samples: list[Sample] = field(default_factory=list)
    lap_time_ms: int | None = None  # znany dopiero po przejechaniu linii mety
    invalid: bool = False  # gra oznaczyła okrążenie jako nieważne
    pitted: bool = False  # auto było w pit lane
    # Asysty w trakcie okrążenia (najczęstsza wartość; gracz może je zmieniać w garażu między okrążeniami).
    gearbox: int | None = None  # 1 ręczna, 2 ręczna + sugestie, 3 automat
    traction_control: int | None = None  # 0 wył., 1 średnia, 2 pełna
    abs_on: bool | None = None
    ers_assist: bool | None = None
    drs_assist: bool | None = None  # z pakietu Session (asysta DRS = gra włącza sama)
    ers: list["ErsSample"] = field(default_factory=list, repr=False, compare=False)  # próbki baterii (z Car Status)
    drs: list["DrsSample"] = field(default_factory=list, repr=False, compare=False)  # DRS dozwolony / włączony (Car Status + Car Telemetry)
    tyres: list["TyreSample"] = field(default_factory=list, repr=False, compare=False)  # temperatury i zużycie opon co TYRE_SAMPLE_M
    _assist_votes: Counter[tuple[int | None, int | None, bool | None]] = field(default_factory=Counter, repr=False, compare=False)

    def vote_assists(self, gearbox: int | None, traction_control: int | None, abs_on: bool | None, ers_assist: bool | None = None) -> None:
        self._assist_votes[(gearbox, traction_control, abs_on)] += 1
        self.gearbox, self.traction_control, self.abs_on = self._assist_votes.most_common(1)[0][0]
        if ers_assist is not None:
            self.ers_assist = ers_assist

    track_length_m: float | None = None  # z pakietu Session, gdy znana
    # Warunki okrążenia (do uczciwego porównania z mistrzem): paliwo na starcie, mieszanka, wiek opon, pogoda, uszkodzenia.
    fuel_kg: float | None = None
    compound: str = "unknown"
    tyre_age_laps: int | None = None
    damage_percent: int = 0  # największe uszkodzenie skrzydeł/podłogi/dyfuzora w trakcie okrążenia
    weather: int | None = None
    track_temp_c: int | None = None
    session_type: int | None = None
    sector1_ms: int | None = None  # z Lap Data w trakcie okrążenia (gra zeruje na mecie)
    sector2_ms: int | None = None
    sector3_ms: int | None = None  # czas okrążenia minus S1 i S2, liczony po mecie

    @property
    def sectors_ms(self) -> tuple[int | None, int | None, int | None]:
        return (self.sector1_ms, self.sector2_ms, self.sector3_ms)

    def close_sectors(self) -> None:
        """Po mecie: S3 z czasu okrążenia; bez kompletu S1 i S2 sektory zostają puste."""
        if self.lap_time_ms and self.sector1_ms and self.sector2_ms:
            s3 = self.lap_time_ms - self.sector1_ms - self.sector2_ms
            self.sector3_ms = s3 if s3 > 0 else None
        if self.sector3_ms is None:
            self.sector1_ms = self.sector2_ms = None

    def is_complete_hint(self) -> bool:
        """Pełność wg długości toru zapisanej w okrążeniu; bez niej zakładamy, że pełne."""
        return self.is_complete(self.track_length_m) if self.track_length_m else bool(self.samples)

    def is_complete(self, track_length_m: float, tolerance: float = 0.05) -> bool:
        """Czy próbki pokrywają całe okrążenie (od mety do mety)."""
        if not self.samples:
            return False
        return (
            self.samples[0].distance_m <= tolerance * track_length_m
            and self.samples[-1].distance_m >= (1 - tolerance) * track_length_m
        )


class LapRecorder:
    """Karmiony surowymi pakietami; zwraca okrążenie, gdy auto minie linię mety.

    Próbka powstaje na każdy pakiet Car Telemetry, pod warunkiem że od poprzedniej
    przyszedł nowy pakiet Lap Data (inaczej dystans byłby powtórzony).
    """

    def __init__(self, state: TelemetryState | None = None) -> None:
        self.state = state or TelemetryState()
        self.laps: list[Lap] = []
        self.current: Lap | None = None
        self._lap_data_seen = False

    def feed(self, data: bytes) -> Lap | None:
        kind = self.state.feed(data)
        if kind is PacketId.LAP_DATA:
            self._lap_data_seen = True
            return None
        if kind is not PacketId.CAR_TELEMETRY or not self._lap_data_seen or self.state.lap is None:
            return None
        self._lap_data_seen = False
        lap = self.state.lap.player
        if lap.lap_distance < 0:
            return None  # przed pierwszym przejazdem linii mety
        finished: Lap | None = None
        if self.current is None or lap.current_lap_num != self.current.number:
            if self.current is not None and self.current.samples:
                self.current.lap_time_ms = lap.last_lap_time_ms or None
                self.current.close_sectors()
                self.laps.append(self.current)
                finished = self.current
            # okrążenie bez próbek (np. numer z poprzedniej sesji jeszcze w garażu) jest pomijane
            self.current = Lap(
                number=lap.current_lap_num,
                track_length_m=float(self.state.session.track_length_m) if self.state.session else None,
            )
        if lap.current_lap_invalid:
            self.current.invalid = True
        if lap.sector1_time_ms:
            self.current.sector1_ms = lap.sector1_time_ms
        if lap.sector2_time_ms:
            self.current.sector2_ms = lap.sector2_time_ms
        if lap.pit_status != 0:
            self.current.pitted = True
            return finished
        car = self.state.telemetry.player  # type: ignore[union-attr]
        status = self.state.status.player if self.state.status else None
        self.current.vote_assists(
            self.state.session.assists.gearbox if self.state.session else None,
            status.traction_control if status else None,
            status.anti_lock_brakes if status else None,
            self.state.session.assists.ers if self.state.session else None,
        )
        if status is not None:
            if self.current.fuel_kg is None:  # warunki z pierwszego pakietu stanu w okrążeniu
                self.current.fuel_kg = status.fuel_in_tank_kg
                self.current.compound = VISUAL_TYRE_NAMES.get(status.visual_tyre_compound, "unknown")
                self.current.tyre_age_laps = status.tyres_age_laps
        if self.state.session is not None and self.current.weather is None:
            self.current.weather = self.state.session.weather
            self.current.track_temp_c = self.state.session.track_temperature
            self.current.session_type = self.state.session.session_type
        if self.state.damage is not None:
            d = self.state.damage.player
            self.current.damage_percent = max(
                self.current.damage_percent, d.front_left_wing_damage_percent, d.front_right_wing_damage_percent,
                d.rear_wing_damage_percent, d.floor_damage_percent, d.diffuser_damage_percent,
            )
        if status is not None:
            self.current.ers.append(ErsSample(
                lap.lap_distance, status.ers_store_energy_j, status.ers_deployed_this_lap_j,
                status.ers_harvested_this_lap_mguk_j + status.ers_harvested_this_lap_mguh_j, status.ers_deploy_mode,
            ))
            self.current.drs.append(DrsSample(lap.lap_distance, lap.current_lap_time_ms, status.drs_allowed, car.drs))
        if self.state.session is not None:
            self.current.drs_assist = self.state.session.assists.drs
        tyres = self.current.tyres
        if not tyres or lap.lap_distance - tyres[-1].distance_m >= TYRE_SAMPLE_M:
            damage = self.state.damage.player if self.state.damage else None
            tyres.append(TyreSample(
                lap.lap_distance, tuple(car.tyres_surface_temperature), tuple(car.tyres_inner_temperature),
                tuple(damage.tyres_wear_percent) if damage else None,
            ))
        self.current.samples.append(Sample(
            distance_m=lap.lap_distance, lap_time_ms=lap.current_lap_time_ms, speed_kmh=car.speed_kmh,
            throttle=car.throttle, brake=car.brake, gear=car.gear, steer=car.steer,
        ))
        return finished
