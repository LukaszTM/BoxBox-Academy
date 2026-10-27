"""Ścieżka zdejmowania asyst i postęp gracza na torze.

Kroki (linia jazdy zostaje): 1 automat + TC pełna + ABS -> 2 TC średnia -> 3 TC wyłączona -> 4 ABS wyłączony.
Krok wynika z faktycznych asyst na okrążeniu (z telemetrii), cel na krok: 3 czyste okrążenia z rzędu.
Czyste okrążenie: ważne, pełne, bez pit lane, bez błędu o wadze >= 1 s (obrót, hamowanie dużo za późno).
"""
from dataclasses import dataclass

from boxbox.coach.laps import Lap
from boxbox.coach.rules import Message

CLEAN_LAPS_TO_ADVANCE = 3
BIG_ERROR_WEIGHT = 1.0

STEPS: dict[int, str] = {
    1: "automat, TC pełna, ABS",
    2: "TC średnia",
    3: "TC wyłączona",
    4: "ABS wyłączony",
}
NEXT_STEP_TEXT: dict[int, str] = {  # co powiedzieć po osiągnięciu celu kroku n
    1: "Trzy czyste okrążenia z rzędu. Jesteś gotowy na kolejny krok: kontrola trakcji na średnią.",
    2: "Trzy czyste okrążenia z rzędu. Kolejny krok: kontrola trakcji wyłączona. Gaz dawkuj łagodniej na wyjściach.",
    3: "Trzy czyste okrążenia z rzędu. Kolejny krok: ABS wyłączony. Hamuj mocno, ale nie do zablokowania kół.",
    4: "Jedziesz bez asyst i masz trzy czyste okrążenia. Od teraz pracujemy nad czasem.",
}
NEXT_STEP_CLIP: dict[int, str] = {1: "step_tc_medium", 2: "step_tc_off", 3: "step_abs_off", 4: "step_done"}


def step_for(traction_control: int | None, abs_on: bool | None) -> int:
    if traction_control == 0:
        return 4 if abs_on is False else 3
    if traction_control == 1:
        return 2
    return 1


def is_clean(lap: Lap, messages: list[Message]) -> bool:
    return (
        not lap.invalid and not lap.pitted and lap.lap_time_ms is not None
        and not any(m.weight >= BIG_ERROR_WEIGHT for m in messages)
    )


@dataclass
class TrackProgress:
    track_id: int
    step: int = 1
    streak: int = 0
    achieved_steps: set[int] | None = None  # kroki, których cel już ogłoszono

    def __post_init__(self) -> None:
        if self.achieved_steps is None:
            self.achieved_steps = set()

    def record(self, lap: Lap, messages: list[Message]) -> tuple[str | None, str | None]:
        """Aktualizuje postęp po okrążeniu. Zwraca (id klipu, tekst) do powiedzenia albo (None, None)."""
        step = step_for(lap.traction_control, lap.abs_on)
        if step != self.step:
            self.step, self.streak = step, 0
        if lap.pitted or not lap.is_complete_hint():
            return None, None
        if is_clean(lap, messages):
            self.streak += 1
        else:
            self.streak = 0
            return None, None
        if self.streak >= CLEAN_LAPS_TO_ADVANCE and step not in self.achieved_steps:
            self.achieved_steps.add(step)
            return NEXT_STEP_CLIP[step], NEXT_STEP_TEXT[step]
        if self.streak < CLEAN_LAPS_TO_ADVANCE and step not in self.achieved_steps:
            return f"streak_{self.streak}", f"Czyste okrążenie, {['pierwsze', 'drugie'][self.streak - 1]} z trzech."
        return None, None
