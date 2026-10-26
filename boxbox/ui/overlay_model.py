"""Treść nakładki do nagrań: cel na okrążenie, zbliżający się zakręt i zadanie na nim.

Przewodnik toru (`boxbox/tracks/guide/<track_id>.json`) to lista zakrętów z nazwą
(numer T jak w grze) i dystansem apeksu; plan sesji (`plany/<sesja>.json`) mówi,
co robić na którym okrążeniu i w którym zakręcie.
"""
import json
from dataclasses import dataclass, field
from pathlib import Path

from boxbox.telemetry.state import TelemetryState
from boxbox.tracks.model import Corner

GUIDE_DIR = Path(__file__).parent.parent / "tracks" / "guide"
APEX_HOLD_M = 40.0  # tak długo po apeksie pokazujemy jeszcze ten sam zakręt
CALIBRATION_RADIUS_M = 250.0  # jak daleko może leżeć zakręt z przewodnika od wykrytej strefy hamowania


@dataclass(frozen=True)
class GuideCorner:
    name: str
    apex_m: float
    note: str = ""
    flat: bool = False  # zakręt bez hamowania: kalibracja go nie przesuwa i nie dopasowuje do stref


@dataclass(frozen=True)
class TrackGuide:
    track_id: int
    name: str
    length_m: float
    accuracy: str
    corners: tuple[GuideCorner, ...]

    def next_corner(self, lap_distance_m: float) -> tuple[GuideCorner, float]:
        """(zakręt, metry do apeksu; ujemne = tuż za apeksem). Za ostatnim zakrętem wraca do pierwszego."""
        for c in self.corners:
            if c.apex_m + APEX_HOLD_M >= lap_distance_m:
                return c, c.apex_m - lap_distance_m
        first = self.corners[0]
        return first, self.length_m - lap_distance_m + first.apex_m


@dataclass(frozen=True)
class SessionPlan:
    title: str
    laps: dict[int, str]
    error_laps: tuple[int, ...]
    tasks: dict[str, str] = field(default_factory=dict)  # nazwa zakrętu -> zadanie

    def goal_for_lap(self, lap: int) -> str:
        if lap in self.laps:
            return self.laps[lap]
        last = max(self.laps) if self.laps else 0
        return self.laps.get(last, "") if lap > last else ""

    def task_for(self, lap: int, corner: GuideCorner) -> str | None:
        if lap not in self.error_laps:
            return None
        return self.tasks.get(corner.name)


def calibrate_guide(guide: TrackGuide, zones: tuple[Corner, ...]) -> TrackGuide:
    """Przesuwa apeksy z przewodnika na wykryte strefy hamowania z pierwszego okrążenia.

    Każda strefa dostaje najbliższy zakręt z przewodnika (w promieniu CALIBRATION_RADIUS_M);
    zakręty bez strefy (np. szybkie, bez hamowania) zostają jak były, strefy bez zakrętu
    dochodzą jako "hamowanie N". Nazwy zostają, więc plan sesji nadal pasuje.
    """
    remaining = [c for c in guide.corners if not c.flat]
    out: list[GuideCorner] = [c for c in guide.corners if c.flat]
    extra = 0
    for zone in zones:
        if not remaining:
            match = None
        else:
            match = min(remaining, key=lambda c: abs(c.apex_m - zone.apex_m))
            if abs(match.apex_m - zone.apex_m) > CALIBRATION_RADIUS_M:
                match = None
        if match is None:
            extra += 1
            out.append(GuideCorner(f"hamowanie {extra}", zone.apex_m, "strefa spoza przewodnika"))
        else:
            remaining.remove(match)
            out.append(GuideCorner(match.name, zone.apex_m, match.note))
    out.extend(remaining)
    return TrackGuide(
        guide.track_id, guide.name, guide.length_m, "skalibrowane z okrążenia (strefy hamowania)",
        tuple(sorted(out, key=lambda c: c.apex_m)),
    )


def save_guide(guide: TrackGuide, path: Path) -> None:
    data = {
        "track_id": guide.track_id, "name": guide.name, "length_m": guide.length_m, "accuracy": guide.accuracy,
        "corners": [
            {"name": c.name, "apex_m": round(c.apex_m, 1), "note": c.note, **({"flat": True} if c.flat else {})}
            for c in guide.corners
        ],
    }
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_guide(path: Path) -> TrackGuide:
    data = json.loads(path.read_text(encoding="utf-8"))
    corners = tuple(
        sorted(
            (GuideCorner(c["name"], float(c["apex_m"]), c.get("note", ""), bool(c.get("flat", False))) for c in data["corners"]),
            key=lambda c: c.apex_m,
        )
    )
    return TrackGuide(int(data["track_id"]), data["name"], float(data["length_m"]), data.get("accuracy", ""), corners)


def load_guide_for(track_id: int, guide_dir: Path = GUIDE_DIR) -> TrackGuide | None:
    path = guide_dir / f"{track_id}.json"
    return load_guide(path) if path.exists() else None


def load_plan(path: Path) -> SessionPlan:
    data = json.loads(path.read_text(encoding="utf-8"))
    return SessionPlan(
        title=data.get("title", path.stem),
        laps={int(k): v for k, v in data.get("laps", {}).items()},
        error_laps=tuple(int(x) for x in data.get("error_laps", [])),
        tasks=dict(data.get("tasks", {})),
    )


@dataclass(frozen=True)
class ChecklistItem:
    key: str  # "lap:4" albo "task:4:T1"
    label: str
    done: bool


def checklist(plan: SessionPlan, guide: TrackGuide | None, done: set[str]) -> tuple[ChecklistItem, ...]:
    """Lista zadań sesji: cel każdego okrążenia, a na okrążeniach z błędami zadania per zakręt."""
    items: list[ChecklistItem] = []
    corner_names = [c.name for c in guide.corners] if guide else list(plan.tasks)
    for lap in sorted(plan.laps):
        items.append(ChecklistItem(f"lap:{lap}", f"Okr. {lap}: {plan.laps[lap]}", f"lap:{lap}" in done))
        if lap in plan.error_laps:
            for name in corner_names:
                task = plan.tasks.get(name)
                if task:
                    key = f"task:{lap}:{name}"
                    items.append(ChecklistItem(key, f"    {name}: {task}", key in done))
    return tuple(items)


def update_progress(done: set[str], state: TelemetryState, plan: SessionPlan, guide: TrackGuide | None) -> None:
    """Dopisuje do `done` to, co telemetria już potwierdziła."""
    if state.lap is None:
        return
    lap = state.lap.player
    lap_num = lap.current_lap_num
    last = max(plan.laps) if plan.laps else 0
    for n in plan.laps:
        if n < lap_num or (n == last and lap_num >= n and lap.pit_status != 0):
            done.add(f"lap:{n}")
    if guide is None or lap_num not in plan.error_laps or lap.lap_distance < 0:
        return
    for c in guide.corners:
        if c.name in plan.tasks and lap.lap_distance > c.apex_m + APEX_HOLD_M:
            done.add(f"task:{lap_num}:{c.name}")


@dataclass(frozen=True)
class OverlayView:
    title: str
    lap_line: str
    goal_line: str
    corner_line: str
    task_line: str  # pusta = nic do zrobienia w tym zakręcie
    note_line: str
    status_line: str
    items: tuple[ChecklistItem, ...] = ()


def build_view(
    state: TelemetryState,
    plan: SessionPlan,
    guide: TrackGuide | None,
    packets: int,
    recording_name: str | None,
    done: set[str] | None = None,
) -> OverlayView:
    rec = f"nagrywam: {recording_name}" if recording_name else "bez nagrywania"
    items = checklist(plan, guide, done or set())
    if state.lap is None or state.telemetry is None:
        waiting = "czekam na telemetrię z gry..." if packets == 0 else f"pakietów: {packets}"
        return OverlayView(plan.title, "", "", "", "", "", f"{waiting} | {rec}", items)
    lap = state.lap.player
    car = state.telemetry.player
    lap_num = lap.current_lap_num
    lap_line = f"OKRĄŻENIE {lap_num}"
    if lap.pit_status:
        lap_line += " (pit lane)"
    elif lap.current_lap_invalid:
        lap_line += " (nieważne)"
    goal = plan.goal_for_lap(lap_num)
    corner_line = task_line = note_line = ""
    if guide is None:
        corner_line = "brak przewodnika toru dla tego toru" if state.session else ""
    elif lap.lap_distance >= 0:
        corner, dist = guide.next_corner(lap.lap_distance)
        where = f"za {dist:.0f} m" if dist > 15 else ("TERAZ" if dist > -APEX_HOLD_M else "")
        corner_line = f"{corner.name}  {where}".strip()
        task = plan.task_for(lap_num, corner)
        task_line = task or ""
        note_line = corner.note
    status = f"{car.speed_kmh} km/h, bieg {car.gear} | {lap.lap_distance:.0f} m | {rec}"
    if guide is not None and guide.accuracy.startswith("orient"):
        status += " | pozycje zakrętów orientacyjne (do 1. pełnego okrążenia)"
    elif guide is not None and guide.accuracy.startswith("skalibrowane"):
        status += " | zakręty skalibrowane z okrążenia"
    return OverlayView(plan.title, lap_line, goal, corner_line, task_line, note_line, status, items)
