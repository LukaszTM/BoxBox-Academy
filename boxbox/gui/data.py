"""Dane dla interfejsu (index.html + app.js): jeden słownik `D`, który okno rysuje. Zero HTML tutaj."""
import base64
import json
from datetime import date, datetime
from pathlib import Path

from boxbox.coach.analyze import format_time
from boxbox.coach.corners import analyze_lap
from boxbox.coach.delta import delta_trace
from boxbox.coach.glossary import GLOSSARY
from boxbox.coach.laps import Lap, Sample
from boxbox.coach.lessons import LESSONS
from boxbox.coach.progress import CLEAN_LAPS_TO_ADVANCE, STEPS
from boxbox.coach.summary import rule_pl
from boxbox.games import adapter
from boxbox.gui import texts
from boxbox.gui.settings import Settings
from boxbox.storage.db import Database
from boxbox.tracks.atlas import (
    FIT_DIR,
    AtlasFit,
    fit_path,
    load_atlas,
    outline_shape,
    to_shape,
)
from boxbox.tracks.model import load_track_by_id
from boxbox.tracks.shape import SHAPE_DIR, TrackShape, load_shape, shape_path

ICONS = {"braking_one_corner": "target", "throttle_exit": "bolt", "clean_lap": "flag", "trail_braking": "layers", "ers_straights": "spark"}
BUILD = "1101"


def _track_name(track_id: int | None) -> str:
    if track_id is None:
        return "tor nieznany"
    try:
        return load_track_by_id(track_id).name
    except FileNotFoundError:
        return f"tor {track_id}"


def _norm(values: list[float], lo: float | None = None, hi: float | None = None) -> list[float]:
    if not values:
        return []
    lo = min(values) if lo is None else lo
    hi = max(values) if hi is None else hi
    span = hi - lo if hi > lo else 1.0
    return [round((v - lo) / span, 4) for v in values]


def _resample(samples: tuple[Sample, ...] | list[Sample], attr: str, n: int = 120) -> list[float]:
    pts = [s for s in samples if s.distance_m >= 0]
    if len(pts) < 2:
        return []
    out = []
    for i in range(n):
        target = pts[0].distance_m + (pts[-1].distance_m - pts[0].distance_m) * i / (n - 1)
        j = min(range(len(pts)), key=lambda k: abs(pts[k].distance_m - target))
        out.append(float(getattr(pts[j], attr)))
    return out


def _badges(db: Database, overview: dict, tracks_progress: dict) -> list[dict]:
    any_clean = any(p["streak"] > 0 or p["achieved"] for p in tracks_progress.values())
    no_tc = db.conn.execute("SELECT 1 FROM laps WHERE traction_control = 0 AND complete = 1 LIMIT 1").fetchone() is not None
    mastered_track = any(p["mastered_all"] for p in tracks_progress.values())
    dates = [date.fromisoformat(d) for d in db.session_dates() if len(d) == 10]
    streak_days = best = 0
    prev = None
    for d in dates:
        streak_days = streak_days + 1 if prev is not None and (d - prev).days == 1 else 1
        best = max(best, streak_days)
        prev = d
    return [
        {"icon": "flag", "name": "Pierwsze czyste", "got": any_clean, "hint": "Pierwsze czyste okrążenie"},
        {"icon": "shield", "name": "Jazda bez TC", "got": no_tc, "hint": "Okrążenie bez kontroli trakcji"},
        {"icon": "clock", "name": "10 sesji", "got": overview["sessions"] >= 10, "hint": f"{overview['sessions']}/10 sesji"},
        {"icon": "target", "name": "Tor opanowany", "got": mastered_track, "hint": "Wszystkie zakręty bez uwag w 3 okrążeniach"},
        {"icon": "spark", "name": "Seria 7 dni", "got": best >= 7, "hint": f"najdłuższa seria: {best} dni"},
    ]


def _photo_data_url(path: str) -> str:
    p = Path(path) if path else None
    if not p or not p.is_file():
        return ""
    mime = {"jpg": "jpeg"}.get(p.suffix.lower().lstrip("."), p.suffix.lower().lstrip("."))
    return f"data:image/{mime};base64," + base64.b64encode(p.read_bytes()).decode("ascii")


def _shape_for(track_id: int, shape_dirs: list[Path], fit_dir: Path) -> tuple[TrackShape | None, str]:
    """Kształt toru w kolejności: recorder (realny ślad) -> atlas dopasowany do gry -> sam obrys z atlasu."""
    for d in shape_dirs:
        path = shape_path(track_id, d)
        if path.exists():
            return load_shape(path), "recorder"
    atlas = load_atlas(track_id)
    if atlas is None:
        return None, ""
    fp = fit_path(track_id, fit_dir)
    if fp.exists():
        try:
            track = load_track_by_id(track_id)
        except FileNotFoundError:
            track = None
        fit_ = AtlasFit.load(fp)
        return to_shape(atlas, fit_, atlas.name, track.length_m if track else atlas.length_m, track), "atlas"
    return outline_shape(atlas), "outline"


def map_for(track_id: int, shape_dir: Path = SHAPE_DIR, active: str = "", fit_dir: Path = FIT_DIR,
            brakes: list[float] | None = None, ref_brakes: list[float] | None = None) -> dict | None:
    """Mapa do SVG 500x270: obrys, zakręty, meta i (opcjonalnie) punkty hamowania gracza i referencji (dystanse w m)."""
    dirs = [shape_dir] + ([SHAPE_DIR] if shape_dir != SHAPE_DIR else [])
    shape, source = _shape_for(track_id, dirs, fit_dir)
    if shape is None or not shape.points:
        return None
    xs = [p.x for p in shape.points]
    zs = [p.z for p in shape.points]
    w, h = (max(xs) - min(xs)) or 1.0, (max(zs) - min(zs)) or 1.0
    scale = min(440 / w, 230 / h)
    ox, oz = 30 + (440 - w * scale) / 2, 20 + (230 - h * scale) / 2

    def pt(x: float, z: float) -> list[float]:
        return [round(ox + (x - min(xs)) * scale, 1), round(oz + (z - min(zs)) * scale, 1)]

    step = max(1, len(shape.points) // 160)
    placed = source != "outline"  # bez dopasowania do gry dystans nie wskazuje punktu obrysu

    def marks(ds: list[float] | None) -> list[list[float]]:
        return [pt(*shape.position_at(d)) for d in (ds or [])] if placed else []

    return {
        "points": [pt(p.x, p.z) for p in shape.points[::step]],
        "corners": [{"name": c.name, "x": pt(c.x, c.z)[0], "y": pt(c.x, c.z)[1]} for c in shape.corners] if placed else [],
        "start": pt(shape.points[0].x, shape.points[0].z) if placed else None,
        "brakes": marks(brakes), "refBrakes": marks(ref_brakes),
        "source": source,
    }


class DataBuilder:
    """Składa `D` z ustawień, bazy i stanu sesji. Okno woła `build()` po każdej zmianie."""

    def __init__(self, settings: Settings, db_path: Path, data_dir: Path, shape_dir: Path | None = None) -> None:
        self.settings = settings
        self.db_path = db_path
        self.data_dir = data_dir
        self.shape_dir = shape_dir or data_dir / "shape"  # kształty z sesji; boxbox/tracks/shape (recorder) jako drugie źródło
        self.fit_dir = data_dir / "atlas_fit"
        self.status: dict = {"connected": False, "busy": False, "track": "", "fmt": None, "rate": 0, "port": settings.port}
        self.live: dict | None = None
        self.summary: dict | None = None
        self.wizard: dict = {"checkResult": "", "hearResult": "", "checking": False, "bugResult": ""}
        self.progress_track: int | None = None
        self.analysis_sel: dict = {"session": None, "lap": None, "comp": "best"}

    # --- części ---
    def _driver(self, db: Database, overview: dict, per_track: dict) -> dict:
        s = self.settings
        tracks = []
        for t in overview["tracks"]:
            p = per_track[t["track_id"]]
            tracks.append({"name": _track_name(t["track_id"]), "best": format_time(t["best_ms"]), "step": p["step"],
                           "mastered": p["mastered_n"], "corners": p["corners_n"], "laps": t["laps"]})
        level = max([p["step"] for p in per_track.values()] or [1])
        active = self._active_track(overview)
        ap = per_track.get(active) if active is not None else None
        streak = ap["streak"] if ap else 0
        step = ap["step"] if ap else 1
        nxt = STEPS.get(step + 1)
        return {
            "nick": s.nick, "id": s.player_id.upper(), "level": level, "stepText": f"{step} · {STEPS[step]}",
            "tracksText": f"{len(tracks)} · {sum(1 for p in per_track.values() if p['mastered_all'])} opanowany",
            "laps": overview["laps"], "streakText": f"{streak} / {CLEAN_LAPS_TO_ADVANCE} czystych",
            "progressPct": round(100 * streak / CLEAN_LAPS_TO_ADVANCE),
            "nextText": (f"Do następnego kroku: {CLEAN_LAPS_TO_ADVANCE - streak} czyste okrążenia" if nxt else "Jedziesz bez asyst: pracujemy nad czasem"),
            "since": s.since, "sessions": overview["sessions"], "hours": f"{db.track_hours():.1f} h".replace(".", ","),
            "photo": _photo_data_url(s.photo), "tracks": tracks,
        }

    def _active_track(self, overview: dict) -> int | None:
        if self.progress_track is not None:
            return self.progress_track
        last = self.settings.last_session.get("track_id")
        if last is not None:
            return int(last)
        return overview["tracks"][0]["track_id"] if overview["tracks"] else None

    def _per_track(self, db: Database, overview: dict) -> dict:
        out = {}
        for t in overview["tracks"]:
            tid = t["track_id"]
            p = db.load_progress(tid)
            issues = db.recent_corner_issues(tid)
            try:
                corners = load_track_by_id(tid).corners
            except FileNotFoundError:
                corners = ()
            mastered = [c for c in corners if c.number not in issues]
            out[tid] = {"step": p.step, "streak": p.streak, "achieved": bool(p.achieved_steps), "issues": issues,
                        "mastered_n": len(mastered), "corners_n": len(corners), "mastered_all": bool(corners) and len(mastered) == len(corners),
                        "mastered": [c.name or f"Z{c.number}" for c in mastered],
                        "todo": [{"corner": c.name or f"Z{c.number}", "rule": rule_pl(max(set(issues[c.number]), key=issues[c.number].count))} for c in corners if c.number in issues]}
        return out

    def _progress(self, db: Database, overview: dict, per_track: dict) -> dict:
        active = self._active_track(overview)
        if active is None:
            return {"tracks": [], "active": "", "step": 1, "stepName": STEPS[1], "streak": 0, "needed": CLEAN_LAPS_TO_ADVANCE, "nextStep": STEPS[2], "nextText": "", "bestPerStep": {}, "trend": [], "trendDelta": None, "mastered": [], "todo": [], "badges": [], "history": []}
        p = per_track[active]
        rows = db.lap_table(active, limit=200)
        valid_times = [r["lap_time_ms"] for r in reversed(rows) if r["valid"] and r["lap_time_ms"]][-20:]
        trend = _norm([-t for t in valid_times]) if valid_times else []
        best_all = min((r["lap_time_ms"] for r in rows if r["valid"] and r["lap_time_ms"]), default=None)
        tc = {0: "Wył.", 1: "Średnia", 2: "Pełna"}
        gb = {1: "Ręczna", 2: "Ręczna+", 3: "Auto"}
        try:
            names = {c.number: (c.name or f"Z{c.number}") for c in load_track_by_id(active).corners}
        except FileNotFoundError:
            names = {}
        history = []
        for r in rows[:60]:
            msgs = [(c, rule) for c, rule, w in db.lap_messages(r["id"]) if w >= 0.3]
            delta = (r["lap_time_ms"] - best_all) / 1000 if best_all and r["lap_time_ms"] else None
            history.append([r["created_at"][5:10].replace("-", "."), f"{r['number']:02d}", format_time(r["lap_time_ms"]),
                            ("" if delta is None else f"{delta:+.2f}".replace(".", ",")), "Tak" if r["valid"] else "Nie",
                            tc.get(r["traction_control"], "-"), "Tak" if r["abs_on"] else "Nie", gb.get(r["gearbox"], "-"), str(len(msgs)),
                            "; ".join(f"{names.get(c, f'Z{c}')}: {rule_pl(rule)}" for c, rule in msgs),  # tooltip w tabeli
                            bool(r["valid"] and r["lap_time_ms"] and r["lap_time_ms"] == best_all)])
        nxt = STEPS.get(p["step"] + 1)
        return {
            "tracks": [_track_name(t["track_id"]) for t in overview["tracks"]], "active": _track_name(active),
            "step": p["step"], "stepName": STEPS[p["step"]], "streak": p["streak"], "needed": CLEAN_LAPS_TO_ADVANCE,
            "nextStep": nxt or "", "nextText": f"Brakuje {CLEAN_LAPS_TO_ADVANCE - p['streak']} czystych okrążeń." if nxt else "",
            "bestPerStep": [[f"{k} · {STEPS[k]}", format_time(v) if v else "—"] for k, v in ((k, db.best_time_per_step(active).get(k)) for k in sorted(STEPS))],
            "trend": trend, "trendDelta": (valid_times[-1] - valid_times[0]) / 1000 if len(valid_times) > 1 else None,
            "mastered": p["mastered"], "todo": p["todo"], "badges": _badges(db, overview, per_track), "history": history,
        }

    def _analysis(self, db: Database) -> dict:
        sessions = db.session_list()
        empty = {"sessions": [], "laps": [], "comps": [], "session": None, "lap": None, "comp": "best", "compLabel": "", "track": "", "lengthText": "",
                 "speed": {"own": [], "ref": []}, "pedal": {"own": [], "ref": []}, "gear": {"own": [], "ref": []}, "steer": {"own": [], "ref": []},
                 "delta": {"own": [], "values": [], "end": ""}, "axis": [], "map": None, "notes": []}
        if not sessions:
            return empty
        sel = self.analysis_sel
        session = next((s for s in sessions if s["id"] == sel["session"]), sessions[0])
        laps = db.laps_for_session(session["id"])
        if not laps:
            return empty
        lap = next((l for l in laps if l.id == sel["lap"]), None) or next((l for l in laps if l.lap_time_ms == session["best"]), laps[-1])
        comps = [{"id": "best", "label": "Najlepsze okrążenie toru"}, {"id": "prev", "label": "Poprzednie okrążenie"}]
        comp = sel["comp"] if sel["comp"] in ("best", "prev") else "best"
        ref_lap = None
        if comp == "best" and session["track_id"] is not None:
            # najlepsze okrążenie toru inne niż wybrane; gdy wybrane jest najlepsze, drugie najlepsze
            rows = db.conn.execute(
                "SELECT id FROM laps WHERE track_id = ? AND complete = 1 AND pitted = 0 AND lap_time_ms IS NOT NULL AND id != ?"
                " ORDER BY valid DESC, lap_time_ms ASC LIMIT 1", (session["track_id"], lap.id),
            ).fetchone()
            ref_lap = next((l for l in laps if l.id == rows["id"]), None) if rows else None
            if rows and ref_lap is None:
                ref_lap = db._stored(db.conn.execute("SELECT * FROM laps WHERE id = ?", (rows["id"],)).fetchone())
        if comp == "prev":
            idx = [l.id for l in laps].index(lap.id)
            ref_lap = laps[idx - 1] if idx > 0 else None
        own = db.samples(lap.id)
        ref = db.samples(ref_lap.id) if ref_lap else ()
        speeds_own, speeds_ref = _resample(own, "speed_kmh"), _resample(ref, "speed_kmh")
        hi = max(speeds_own + speeds_ref) if speeds_own else 1
        thr_own, thr_ref = _resample(own, "throttle"), _resample(ref, "throttle")
        brk_own = _resample(own, "brake")
        trace = delta_trace(own, ref) if ref else []
        deltas = [p.delta_s for p in trace]
        delta_values = [round(deltas[int(i * (len(deltas) - 1) / 119)], 3) for i in range(120)] if len(deltas) > 1 else []
        gear_own, gear_ref = _resample(own, "gear"), _resample(ref, "gear")
        steer_own, steer_ref = _resample(own, "steer"), _resample(ref, "steer")
        length = max((s.distance_m for s in own), default=0.0)
        try:
            track = load_track_by_id(session["track_id"]) if session["track_id"] is not None else None
        except FileNotFoundError:
            track = None
        brakes = ref_brakes = None
        if track is not None and own:
            brakes = [m.brake_point_m for m in analyze_lap(Lap(lap.number, list(own)), track).corners if m.brake_point_m is not None]
            if ref:
                ref_brakes = [m.brake_point_m for m in analyze_lap(Lap(ref_lap.number, list(ref)), track).corners if m.brake_point_m is not None]
        names = {c.number: (c.name or f"Z{c.number}") for c in track.corners} if track else {}
        notes = []
        for corner, rule, weight in sorted(db.lap_messages(lap.id), key=lambda x: -x[2]):
            if weight >= 0.15:
                notes.append({"corner": names.get(corner, f"Z{corner}"), "text": rule_pl(rule).capitalize() + ".", "delta": f"+{weight:.2f} s względem referencji".replace(".", ",")})
        return {
            "sessions": [{"id": s["id"], "label": f"{s['created_at'][5:10].replace('-', '.')} · {_track_name(s['track_id'])} · {s['laps']} okr."} for s in sessions],
            "laps": [{"id": l.id, "label": f"Okrążenie {l.number} · {format_time(l.lap_time_ms)}"} for l in laps],
            "comps": comps, "session": session["id"], "lap": lap.id, "comp": comp,
            "compLabel": "najlepsze okrążenie toru" if comp == "best" else "poprzednie okrążenie",
            "track": _track_name(session["track_id"]), "lengthText": f"{length:,.0f} m".replace(",", " "),
            "speed": {"own": _norm(speeds_own, 0, hi), "ref": _norm(speeds_ref, 0, hi) if speeds_ref else []},
            "pedal": {"own": _norm(thr_own, 0, 1), "ref": _norm(thr_ref, 0, 1) if thr_ref else [], "brake": _norm(brk_own, 0, 1)},
            "gear": {"own": _norm(gear_own, 0, 8), "ref": _norm(gear_ref, 0, 8) if gear_ref else []},
            "steer": {"own": _norm(steer_own, -1, 1), "ref": _norm(steer_ref, -1, 1) if steer_ref else []},
            "delta": {"own": _norm(deltas) if deltas else [], "values": delta_values,
                      "end": (f"{deltas[-1]:+.2f} s".replace(".", ",").replace("+", "+").replace("-", "−") if deltas else "")},
            "axis": [f"{int(length * k / 4):,} m".replace(",", " ") for k in range(5)],
            "map": map_for(session["track_id"], self.shape_dir, fit_dir=self.fit_dir, brakes=brakes, ref_brakes=ref_brakes) if session["track_id"] is not None else None,
            "notes": notes,
        }

    def _lessons(self, track_id: int | None = None) -> dict:
        state = self.settings.lesson_state
        corners: list[dict] = []
        if track_id is not None:
            try:
                corners = [{"number": c.number, "name": c.name or f"Z{c.number}"} for c in load_track_by_id(track_id).corners]
            except FileNotFoundError:
                corners = []
        cards = []
        for item in LESSONS:
            st = state.get(item.id, {})
            if st.get("passed"):
                status = "Zaliczona"
            elif st.get("best"):
                needed = int(item.pass_rule.rsplit(":", 1)[-1])
                status = f"W toku · {st['best']}/{needed}"
            else:
                status = "Nowa"
            needed = int(item.pass_rule.rsplit(":", 1)[-1])
            cards.append({"id": item.id, "title": item.title, "desc": item.goal, "goal": item.goal, "explain": item.explain, "laps": item.laps,
                          "status": status, "icon": ICONS.get(item.id, "target"), "premium": item.premium, "cornerOnly": item.corner_only,
                          "passText": f"{needed} okrążenia z rzędu spełniające cel."})
        return {"cards": cards, "corners": corners}

    def _last(self) -> dict | None:
        ls = self.settings.last_session
        return ls or None

    def build(self) -> dict:
        s = self.settings
        game = adapter(s.game)
        db = Database(self.db_path)
        try:
            overview = db.overview()
            per_track = self._per_track(db, overview)
            driver = self._driver(db, overview, per_track)
            progress = self._progress(db, overview, per_track)
            analysis = self._analysis(db)
            active_id = self._active_track(overview)
        finally:
            db.close()
        active_name = progress["active"]
        return {
            "app": {"version": texts.VERSION, "build": f"BUILD {BUILD}", "game": f"{game.name} · 2026 Season Pack", "gameShort": game.name, "dataDir": str(self.data_dir.resolve()),
                    "recordingsDir": str(Path("recordings").resolve())},
            "status": self.status,
            "settings": {"nick": s.nick, "volume": int(round(s.volume * 100)), "overlayDefault": s.overlay, "quietDefault": s.quiet, "record": s.record,
                         "autoStart": s.auto_start, "autoStopS": s.auto_stop_s, "port": s.port, "voice": "Piotr", "explain": s.explain,
                         "consent": s.consent, "wizardDone": s.wizard_done, "tutorialDone": s.tutorial_done, "scale": int(round(s.overlay_scale * 100)),
                         "opacity": s.overlay_opacity, "hud": s.hud_layout},
            "driver": driver,
            "last": self._last(),
            "todo": {"step": progress["step"], "stepName": progress["stepName"], "streak": progress["streak"], "needed": progress["needed"],
                     "nextStep": progress["nextStep"] or "praca nad czasem", "track": active_name},
            "live": self.live, "summary": self.summary, "progress": progress, "analysis": analysis, "lessons": self._lessons(active_id),
            "glossary": [[name, desc] for name, desc in GLOSSARY.values()], "wizard": self.wizard,
            "defaultSessionName": f"{active_name or 'sesja'} {datetime.now():%d.%m}".strip(),
        }


def to_json(d: dict) -> str:
    return json.dumps(d, ensure_ascii=False)
