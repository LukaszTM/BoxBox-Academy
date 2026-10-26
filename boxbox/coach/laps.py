"""Cięcie strumienia pakietów na okrążenia z próbkami jazdy auta gracza."""
from dataclasses import dataclass, field

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
            if self.current is not None:
                self.current.lap_time_ms = lap.last_lap_time_ms or None
                self.laps.append(self.current)
                finished = self.current
            self.current = Lap(number=lap.current_lap_num)
        if lap.current_lap_invalid:
            self.current.invalid = True
        if lap.pit_status != 0:
            self.current.pitted = True
            return finished
        car = self.state.telemetry.player  # type: ignore[union-attr]
        self.current.samples.append(Sample(
            distance_m=lap.lap_distance, lap_time_ms=lap.current_lap_time_ms, speed_kmh=car.speed_kmh,
            throttle=car.throttle, brake=car.brake, gear=car.gear, steer=car.steer,
        ))
        return finished
