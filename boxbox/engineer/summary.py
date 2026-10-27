"""Podsumowanie wyścigu po sesji (tekst): pozycje, start, kontakty, kary, pit-stopy, opony."""
from dataclasses import dataclass, field

from boxbox.engineer.start import StartReport
from boxbox.telemetry.state import TelemetryState


@dataclass
class RaceSummary:
    lines: list[str] = field(default_factory=list)
    safety_rating: int = 100  # 100 = czysto; każdy kontakt i kara obniżają
    good: str = ""
    to_work: str = ""


def summarize_race(state: TelemetryState, start: StartReport | None, collisions: int, penalties: int, warnings: int, pit_stops: int) -> RaceSummary:
    s = RaceSummary()
    lap = state.lap.player if state.lap is not None else None
    if lap is not None and lap.grid_position and lap.car_position:
        diff = lap.grid_position - lap.car_position
        s.lines.append(f"Pozycja: start {lap.grid_position}, meta {lap.car_position}" + (f" ({'+' if diff > 0 else ''}{diff})" if diff else ""))
    if start is not None:
        s.lines.append(start.text)
    s.lines.append(f"Kontakty: {collisions}, kary: {penalties}, ostrzeżenia: {warnings}, pit-stopy: {pit_stops}")
    s.safety_rating = max(0, 100 - 20 * collisions - 15 * penalties - 5 * warnings)
    s.lines.append(f"Czystość jazdy: {s.safety_rating}/100")
    if collisions == 0 and penalties == 0:
        s.good = "Wyścig bez kontaktu i bez kar."
    elif start is not None and start.ok:
        s.good = "Dobry start: " + start.text.removeprefix("Start: ").split(";")[0] + "."
    else:
        s.good = "Dojechałeś do mety; teraz pracujemy nad czystością."
    if collisions > 0:
        s.to_work = f"{collisions} {'kontakt' if collisions == 1 else 'kontakty'}: zostaw miejsce w pierwszym zakręcie i broń się jedną zmianą toru."
    elif start is not None and not start.ok:
        s.to_work = start.text.removeprefix("Start: ")
    elif warnings > 0:
        s.to_work = "Ostrzeżenia za limity toru: zostaw sobie metr zapasu na wyjściach."
    else:
        s.to_work = "Nic pilnego; następnym razem popracujemy nad tempem na oponach."
    return s
