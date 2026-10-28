"""Profil umiejętności gracza: sześć wymiarów w skali 0–100 z danych, które już są w bazie.

Wymiary i względem czego liczone (szczegóły: docs/ANALIZA_UMIEJETNOSCI.md):
- hamowanie: odchylenie punktu hamowania od referencji (0 m = 100, >= 80 m = 0), zakręt z obrotem = 0;
- praca hamulcem: siła hamowania względem referencji i stopniowe puszczanie tam, gdzie referencja puszcza stopniowo;
- gaz na wyjściu: odchylenie pełnego gazu od referencji (0 m = 100, >= 120 m = 0), zakręt z utratą przyczepności = 0;
- powtarzalność: rozrzut czasów (średnia do najlepszego: 0,5 % = 100, 3 % = 0) i odsetek czystych okrążeń, po połowie;
- tempo: strata średniej z ostatnich czystych okrążeń do referencji (0 % = 100, 5 % = 0);
- samodzielność: krok asyst (1–4 = 25–100) plus seria czystych okrążeń na kroku.

Referencja techniki to najlepsze własne okrążenie (albo duch z Time Trial, gdy podany), więc wynik mówi
"jak blisko swojego najlepszego jesteś", a nie "jak blisko zawodowca": to jest napisane w opisie wymiaru.
Liczymy z ostatnich WINDOW ważnych, pełnych okrążeń bez pit lane; poniżej MIN_LAPS wynik to "za mało danych".
Trend: różnica względem profilu z poprzednich WINDOW okrążeń. Silnik nie dotyka UI: zwraca dane.
"""
import argparse
import statistics
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from boxbox.coach.corners import CornerMetrics
from boxbox.coach.progress import CLEAN_LAPS_TO_ADVANCE, STEPS, step_for

WINDOW = 10  # tyle ostatnich okrążeń liczy się do wyniku
MIN_LAPS = 5  # poniżej: "za mało danych"
BIG_ERROR_WEIGHT = 1.0  # uwaga o tej wadze = okrążenie nieczyste (jak w progress.py)
BRAKE_ZERO_M = 80.0  # odchylenie punktu hamowania, przy którym zakręt ma 0
THROTTLE_ZERO_M = 120.0
SPREAD_FULL = 0.005  # rozrzut czasów 0,5 % = 100
SPREAD_ZERO = 0.03
PACE_ZERO = 0.05  # strata 5 % do referencji = 0
RELEASE_GRADUAL_S = 0.4  # referencja puszcza stopniowo od tego czasu (jak REFERENCE_RELEASE_S w rules)

DIMENSIONS: tuple[tuple[str, str, str], ...] = (
    ("braking", "Hamowanie", "punkt hamowania względem twojego najlepszego okrążenia"),
    ("brake_control", "Praca hamulcem", "siła hamowania i stopniowe puszczanie względem najlepszego okrążenia"),
    ("throttle", "Gaz na wyjściu", "moment pełnego gazu i przyczepność względem najlepszego okrążenia"),
    ("consistency", "Powtarzalność", "rozrzut czasów i odsetek czystych okrążeń (progi stałe)"),
    ("pace", "Tempo", "strata ostatnich czystych okrążeń do referencji"),
    ("independence", "Samodzielność", "krok zdejmowania asyst i seria czystych okrążeń"),
)


@dataclass(frozen=True)
class LapRecord:
    """Jedno okrążenie z bazy (albo z nagrania w testach) w postaci potrzebnej do profilu."""
    lap_time_ms: int | None
    valid: bool
    complete: bool
    pitted: bool
    corners: tuple[CornerMetrics, ...]
    messages: tuple[tuple[int, str, float], ...] = ()  # (zakręt, reguła, waga)
    traction_control: int | None = None
    abs_on: bool | None = None

    @property
    def usable(self) -> bool:
        return self.valid and self.complete and not self.pitted and bool(self.lap_time_ms)

    @property
    def clean(self) -> bool:
        return self.usable and not any(w >= BIG_ERROR_WEIGHT for _, _, w in self.messages)


@dataclass(frozen=True)
class Skill:
    key: str
    name: str
    basis: str  # względem czego liczone, jedno zdanie
    score: int | None  # None = za mało danych
    trend: int | None  # punkty względem poprzedniego okna; None = brak poprzedniego okna
    hint: str  # co podnosi wynik, jedno zdanie
    laps: int  # ile okrążeń weszło do wyniku

    def to_dict(self) -> dict[str, Any]:
        return {"key": self.key, "name": self.name, "basis": self.basis, "score": self.score, "trend": self.trend, "hint": self.hint, "laps": self.laps}


@dataclass(frozen=True)
class SkillProfile:
    track_id: int | None
    track_name: str
    skills: tuple[Skill, ...]
    laps_used: int
    note: str = ""  # np. "za mało danych: 3 z 5 okrążeń"

    def by_key(self, key: str) -> Skill:
        return next(s for s in self.skills if s.key == key)

    def to_dict(self) -> dict[str, Any]:
        return {"trackId": self.track_id, "track": self.track_name, "lapsUsed": self.laps_used, "note": self.note,
                "skills": [s.to_dict() for s in self.skills]}


def _clip(value: float) -> int:
    return int(round(min(100.0, max(0.0, value))))


def _linear(value: float, full: float, zero: float) -> float:
    """100 przy `full`, 0 przy `zero`, liniowo pomiędzy."""
    if value <= full:
        return 100.0
    if value >= zero:
        return 0.0
    return 100.0 * (zero - value) / (zero - full)


def _label(corner: int, names: dict[int, str] | None) -> str:
    return (names or {}).get(corner) or f"zakręt {corner}"


def _round_m(value: float) -> int:
    return int(max(5, round(value / 5) * 5))


# --- wymiary -----------------------------------------------------------------

def _braking(laps: Sequence[LapRecord], ref: dict[int, CornerMetrics], names: dict[int, str] | None) -> tuple[float | None, str]:
    per_corner: dict[int, list[float]] = {}
    scores: list[float] = []
    for lap in laps:
        spun = {c for c, r, _ in lap.messages if r == "grip_lost"}
        for m in lap.corners:
            r = ref.get(m.corner)
            if r is None or r.brake_point_m is None:
                continue
            if m.corner in spun or m.brake_point_m is None:
                scores.append(0.0)
                continue
            delta = m.brake_point_m - r.brake_point_m
            per_corner.setdefault(m.corner, []).append(delta)
            scores.append(_linear(abs(delta), 0.0, BRAKE_ZERO_M))
    if not scores:
        return None, ""
    worst = max(per_corner.items(), key=lambda kv: abs(statistics.fmean(kv[1])), default=None)
    hint = ""
    if worst is not None:
        mean = statistics.fmean(worst[1])
        if abs(mean) >= 10:
            hint = f"hamuj ok. {_round_m(abs(mean))} m {'wcześniej' if mean > 0 else 'później'} w {_label(worst[0], names)}"
    return statistics.fmean(scores), hint


def _brake_control(laps: Sequence[LapRecord], ref: dict[int, CornerMetrics], names: dict[int, str] | None) -> tuple[float | None, str]:
    scores: list[float] = []
    release_issues: dict[int, int] = {}
    strength_issues: dict[int, list[float]] = {}
    for lap in laps:
        for m in lap.corners:
            r = ref.get(m.corner)
            if r is None or r.brake_point_m is None or r.max_brake <= 0:
                continue
            strength = _linear(abs(m.max_brake - r.max_brake), 0.1, 0.6)
            strength_issues.setdefault(m.corner, []).append(m.max_brake - r.max_brake)
            if r.brake_release_s is not None and r.brake_release_s >= RELEASE_GRADUAL_S and m.brake_release_s is not None:
                release = 100.0 * min(1.0, m.brake_release_s / r.brake_release_s)
                if release < 50:
                    release_issues[m.corner] = release_issues.get(m.corner, 0) + 1
                scores.append((strength + release) / 2)
            else:
                scores.append(strength)
    if not scores:
        return None, ""
    hint = ""
    if release_issues:
        corner = max(release_issues, key=release_issues.get)  # type: ignore[arg-type]
        hint = f"zwalniaj hamulec stopniowo aż do apeksu w {_label(corner, names)}"
    else:
        worst = max(strength_issues.items(), key=lambda kv: abs(statistics.fmean(kv[1])), default=None)
        if worst is not None and abs(statistics.fmean(worst[1])) >= 0.2:
            mean = statistics.fmean(worst[1])
            hint = f"{'hamuj mocniej' if mean < 0 else 'nie dociskaj hamulca tak mocno'} w {_label(worst[0], names)}"
    return statistics.fmean(scores), hint


def _throttle(laps: Sequence[LapRecord], ref: dict[int, CornerMetrics], names: dict[int, str] | None) -> tuple[float | None, str]:
    per_corner: dict[int, list[float]] = {}
    grip: dict[int, int] = {}
    scores: list[float] = []
    for lap in laps:
        spun = {c for c, r, _ in lap.messages if r == "grip_lost"}
        for m in lap.corners:
            r = ref.get(m.corner)
            if r is None or r.full_throttle_m is None:
                continue
            if m.corner in spun:
                grip[m.corner] = grip.get(m.corner, 0) + 1
                scores.append(0.0)
                continue
            if m.full_throttle_m is None:
                scores.append(0.0)
                per_corner.setdefault(m.corner, []).append(THROTTLE_ZERO_M)
                continue
            delta = m.full_throttle_m - r.full_throttle_m
            per_corner.setdefault(m.corner, []).append(delta)
            scores.append(_linear(abs(delta), 0.0, THROTTLE_ZERO_M))
    if not scores:
        return None, ""
    hint = ""
    if grip:
        corner = max(grip, key=grip.get)  # type: ignore[arg-type]
        hint = f"łagodniej z gazem na wyjściu z {_label(corner, names)}, tam tracisz przyczepność"
    else:
        worst = max(per_corner.items(), key=lambda kv: abs(statistics.fmean(kv[1])), default=None)
        if worst is not None and abs(statistics.fmean(worst[1])) >= 15:
            mean = statistics.fmean(worst[1])
            hint = (f"pełny gaz ok. {_round_m(abs(mean))} m wcześniej na wyjściu z {_label(worst[0], names)}" if mean > 0
                    else f"z pełnym gazem na wyjściu z {_label(worst[0], names)} poczekaj ok. {_round_m(abs(mean))} m dłużej")
    return statistics.fmean(scores), hint


def _consistency(laps: Sequence[LapRecord], names: dict[int, str] | None) -> tuple[float | None, str]:
    times = [lap.lap_time_ms for lap in laps if lap.usable]
    if len(times) < 2:
        return None, ""
    best = min(times)  # type: ignore[type-var]
    spread = (statistics.fmean(times) - best) / best  # type: ignore[operator]
    spread_score = _linear(spread, SPREAD_FULL, SPREAD_ZERO)
    clean = sum(1 for lap in laps if lap.clean)
    clean_score = 100.0 * clean / len(laps)
    big: dict[int, int] = {}
    for lap in laps:
        for c, _, w in lap.messages:
            if w >= BIG_ERROR_WEIGHT:
                big[c] = big.get(c, 0) + 1
    if big:
        corner = max(big, key=big.get)  # type: ignore[arg-type]
        hint = f"{clean} z {len(laps)} okrążeń czystych; największe błędy w {_label(corner, names)}"
    else:
        hint = f"rozrzut czasów {100 * spread:.1f} %; jedź to samo okrążenie, nie szybsze" if spread > SPREAD_FULL else "równo jak w zegarku; teraz czas na tempo"
    return (spread_score + clean_score) / 2, hint


def _pace(laps: Sequence[LapRecord], reference_ms: int | None, ref: dict[int, CornerMetrics], names: dict[int, str] | None) -> tuple[float | None, str]:
    times = [lap.lap_time_ms for lap in laps if lap.clean]
    if not times or not reference_ms:
        return None, ""
    gap = (statistics.fmean(times) - reference_ms) / reference_ms  # type: ignore[operator]
    score = _linear(max(0.0, gap), 0.0, PACE_ZERO)
    # gdzie ucieka najwięcej czasu: zakręt z największą średnią stratą do referencji
    loss: dict[int, list[float]] = {}
    for lap in laps:
        if not lap.clean:
            continue
        for m in lap.corners:
            r = ref.get(m.corner)
            if r is not None:
                loss.setdefault(m.corner, []).append((m.time_ms - r.time_ms) / 1000)
    worst = max(loss.items(), key=lambda kv: statistics.fmean(kv[1]), default=None)
    hint = ""
    if worst is not None and statistics.fmean(worst[1]) >= 0.1:
        hint = f"najwięcej czasu tracisz w {_label(worst[0], names)}: {statistics.fmean(worst[1]):.1f} s na okrążenie".replace(".", ",")
    elif gap > 0:
        hint = f"średnio {100 * gap:.1f} % wolniej niż referencja".replace(".", ",")
    return score, hint


def _independence(laps: Sequence[LapRecord], step: int | None, streak: int) -> tuple[float | None, str]:
    if step is None:
        recent = [step_for(lap.traction_control, lap.abs_on) for lap in laps if lap.usable]
        if not recent:
            return None, ""
        step = max(set(recent), key=recent.count)
    score = 25.0 * (step - 1) + 25.0 * min(streak, CLEAN_LAPS_TO_ADVANCE) / CLEAN_LAPS_TO_ADVANCE
    nxt = STEPS.get(step + 1)
    hint = f"{CLEAN_LAPS_TO_ADVANCE - min(streak, CLEAN_LAPS_TO_ADVANCE)} czyste okrążenia do kroku: {nxt}" if nxt else "jedziesz bez asyst"
    return score, hint


# --- profil --------------------------------------------------------------------

def _scores(
    laps: Sequence[LapRecord], ref: dict[int, CornerMetrics], reference_ms: int | None, names: dict[int, str] | None,
    step: int | None, streak: int,
) -> dict[str, tuple[float | None, str]]:
    return {
        "braking": _braking(laps, ref, names),
        "brake_control": _brake_control(laps, ref, names),
        "throttle": _throttle(laps, ref, names),
        "consistency": _consistency(laps, names),
        "pace": _pace(laps, reference_ms, ref, names),
        "independence": _independence(laps, step, streak),
    }


def skill_profile(
    laps: Sequence[LapRecord],
    reference: Sequence[CornerMetrics] | None,
    reference_ms: int | None = None,
    corner_names: dict[int, str] | None = None,
    track_id: int | None = None,
    track_name: str = "",
    step: int | None = None,
    streak: int = 0,
    external_reference: bool = False,
) -> SkillProfile:
    """Profil z listy okrążeń (w kolejności jazdy). `reference` = metryki najlepszego okrążenia (własnego albo ducha)."""
    usable = [lap for lap in laps if lap.usable]
    window = usable[-WINDOW:]
    previous = usable[-2 * WINDOW:-WINDOW]
    ref = {m.corner: m for m in reference} if reference else {}
    if reference_ms is None and window:
        reference_ms = min(lap.lap_time_ms for lap in usable)  # type: ignore[type-var]
    enough = len(window) >= MIN_LAPS
    now = _scores(window, ref, reference_ms, corner_names, step, streak)
    before = _scores(previous, ref, reference_ms, corner_names, step, streak) if len(previous) >= MIN_LAPS else {}
    skills: list[Skill] = []
    for key, name, basis in DIMENSIONS:
        if external_reference and key in ("braking", "brake_control", "throttle", "pace"):
            basis = basis.replace("twojego najlepszego okrążenia", "ducha z Time Trial").replace("najlepszego okrążenia", "ducha z Time Trial").replace("do referencji", "do ducha z Time Trial")
        value, hint = now[key]
        if key == "independence":
            score = _clip(value) if value is not None else None
        else:
            score = _clip(value) if (enough and value is not None) else None
        prev = before.get(key, (None, ""))[0]
        trend = None if score is None or prev is None else score - _clip(prev)
        skills.append(Skill(key, name, basis, score, trend, hint if score is not None else "", len(window) if key != "independence" else len(usable)))
    note = "" if enough else f"za mało danych: {len(window)} z {MIN_LAPS} ważnych okrążeń"
    return SkillProfile(track_id, track_name, tuple(skills), len(window), note)


def combine(profiles: Sequence[SkillProfile]) -> SkillProfile:
    """Profil łączny: średnia ważona liczbą okrążeń z torów, które mają wynik."""
    skills: list[Skill] = []
    for key, name, basis in DIMENSIONS:
        have = [(p.by_key(key), p.laps_used or 1) for p in profiles if p.by_key(key).score is not None]
        if not have:
            skills.append(Skill(key, name, basis, None, None, "", 0))
            continue
        total = sum(w for _, w in have)
        score = _clip(sum(s.score * w for s, w in have) / total)  # type: ignore[operator]
        trends = [(s.trend, w) for s, w in have if s.trend is not None]
        trend = int(round(sum(t * w for t, w in trends) / sum(w for _, w in trends))) if trends else None
        weakest = min(have, key=lambda sw: sw[0].score or 0)[0]
        hint = weakest.hint
        skills.append(Skill(key, name, basis, score, trend, hint, sum(w for _, w in have)))
    return SkillProfile(None, "wszystkie tory", tuple(skills), sum(p.laps_used for p in profiles))


def profile_for_track(db: Any, track_id: int, track_name: str = "", corner_names: dict[int, str] | None = None) -> SkillProfile:
    """Profil toru z bazy (`boxbox.storage.db.Database`): okrążenia, metryki, uwagi, postęp."""
    laps: list[LapRecord] = []
    for lap in db.laps_for_track(track_id):
        laps.append(LapRecord(
            lap.lap_time_ms, lap.valid, lap.complete, lap.pitted, db.corner_metrics(lap.id),
            tuple(db.lap_messages(lap.id)), lap.traction_control, lap.abs_on,
        ))
    ref = db.reference(track_id, allow_invalid=False)
    progress = db.load_progress(track_id)
    return skill_profile(
        laps, ref.corners if ref else None, ref.lap.lap_time_ms if ref else None, corner_names, track_id, track_name,
        step=progress.step if progress else None, streak=progress.streak if progress else 0,
    )


def profiles_from_db(db: Any) -> list[SkillProfile]:
    """Profil każdego toru z bazy (z nazwami zakrętów z plików torów, gdy są) plus łączny na końcu."""
    from boxbox.tracks.model import load_track_by_id

    rows = db.conn.execute("SELECT DISTINCT track_id FROM laps WHERE track_id IS NOT NULL ORDER BY track_id").fetchall()
    out: list[SkillProfile] = []
    for row in rows:
        tid = row["track_id"]
        names: dict[int, str] | None = None
        name = f"tor {tid}"
        try:
            track = load_track_by_id(tid)
            name, names = track.name, {c.number: c.name or f"zakręt {c.number}" for c in track.corners}
        except FileNotFoundError:
            pass
        out.append(profile_for_track(db, tid, name, names))
    if out:
        out.append(combine(out))
    return out


def render(profile: SkillProfile) -> str:
    lines = [f"{profile.track_name}: {profile.laps_used} okrążeń" + (f" ({profile.note})" if profile.note else "")]
    for s in profile.skills:
        score = "  —" if s.score is None else f"{s.score:3d}"
        trend = "" if s.trend is None else f" ({s.trend:+d})"
        lines.append(f"  {s.name:<16}{score}{trend:<6}  {s.hint}".rstrip())
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    from boxbox.storage.db import Database

    parser = argparse.ArgumentParser(description="Profil umiejętności gracza z bazy")
    parser.add_argument("--db", type=Path, default=Path("data") / "boxbox.sqlite")
    parser.add_argument("--track", type=int, help="tylko ten tor (id z gry)")
    args = parser.parse_args(argv)
    if not args.db.exists():
        print(f"brak bazy {args.db}")
        return 1
    db = Database(args.db)
    profiles = profiles_from_db(db)
    db.close()
    if args.track is not None:
        profiles = [p for p in profiles if p.track_id == args.track]
    if not profiles:
        print("brak okrążeń w bazie")
        return 1
    print("\n\n".join(render(p) for p in profiles))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
