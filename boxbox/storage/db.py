"""SQLite: sesje, okrążenia, metryki zakrętów, próbki. Najlepsze ważne okrążenie = referencja."""
import sqlite3
import struct
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from boxbox.coach.corners import CornerMetrics, LapAnalysis
from boxbox.coach.ers_sample import ErsSample
from boxbox.coach.lap_samples import DrsSample
from boxbox.coach.laps import Lap, Sample
from boxbox.telemetry.session import SessionPacket

_SAMPLE = struct.Struct("<fIHffbf")  # dystans, czas, prędkość, gaz, hamulec, bieg, kierownica
_DRS = struct.Struct("<fI??")  # dystans, czas, lampka, skrzydło
_ERS = struct.Struct("<ffffB")  # dystans, bateria, deploy, odzysk, tryb

SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY,
    session_uid TEXT,  -- uint64 z gry nie mieści się w INTEGER SQLite (max 2^63-1)
    game TEXT NOT NULL DEFAULT 'f1_25',
    source TEXT NOT NULL,
    track_id INTEGER,
    track_name TEXT,
    session_type INTEGER,
    packet_format INTEGER,
    created_at TEXT NOT NULL,
    UNIQUE (session_uid, source)
);
CREATE TABLE IF NOT EXISTS laps (
    id INTEGER PRIMARY KEY,
    session_id INTEGER NOT NULL REFERENCES sessions(id),
    game TEXT NOT NULL DEFAULT 'f1_25',
    track_id INTEGER,
    number INTEGER NOT NULL,
    lap_time_ms INTEGER,
    valid INTEGER NOT NULL,
    complete INTEGER NOT NULL,
    pitted INTEGER NOT NULL,
    gearbox INTEGER,
    traction_control INTEGER,
    abs_on INTEGER,
    created_at TEXT NOT NULL,
    UNIQUE (session_id, number)
);
CREATE TABLE IF NOT EXISTS corner_metrics (
    lap_id INTEGER NOT NULL REFERENCES laps(id) ON DELETE CASCADE,
    corner INTEGER NOT NULL,
    min_speed_kmh INTEGER NOT NULL,
    apex_m REAL NOT NULL,
    gear_at_apex INTEGER NOT NULL,
    entry_speed_kmh INTEGER NOT NULL,
    exit_speed_kmh INTEGER NOT NULL,
    time_ms INTEGER NOT NULL,
    brake_point_m REAL,
    full_throttle_m REAL,
    brake_end_m REAL,
    brake_release_s REAL,
    max_brake REAL NOT NULL DEFAULT 0,
    PRIMARY KEY (lap_id, corner)
);
CREATE TABLE IF NOT EXISTS lap_samples (
    lap_id INTEGER PRIMARY KEY REFERENCES laps(id) ON DELETE CASCADE,
    data BLOB NOT NULL
);
CREATE TABLE IF NOT EXISTS lap_channels (
    lap_id INTEGER NOT NULL REFERENCES laps(id) ON DELETE CASCADE,
    kind TEXT NOT NULL,  -- drs | ers
    data BLOB NOT NULL,
    PRIMARY KEY (lap_id, kind)
);
CREATE TABLE IF NOT EXISTS lap_messages (
    lap_id INTEGER NOT NULL REFERENCES laps(id) ON DELETE CASCADE,
    corner INTEGER NOT NULL,
    rule TEXT NOT NULL,
    weight REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS progress (
    track_id INTEGER PRIMARY KEY,
    game TEXT NOT NULL DEFAULT 'f1_25',
    step INTEGER NOT NULL,
    streak INTEGER NOT NULL,
    achieved_steps TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS laps_track ON laps(track_id, valid, complete, lap_time_ms);
"""


@dataclass(frozen=True)
class StoredLap:
    id: int
    session_id: int
    track_id: int | None
    number: int
    lap_time_ms: int | None
    valid: bool
    complete: bool
    pitted: bool
    gearbox: int | None
    traction_control: int | None
    abs_on: bool | None


@dataclass(frozen=True)
class ReferenceLap:
    lap: StoredLap
    corners: tuple[CornerMetrics, ...]
    samples: tuple[Sample, ...]

    @property
    def analysis(self) -> LapAnalysis:
        return LapAnalysis(self.lap.number, self.lap.lap_time_ms, self.corners)


def pack_samples(samples: list[Sample]) -> bytes:
    return b"".join(
        _SAMPLE.pack(s.distance_m, s.lap_time_ms, s.speed_kmh, s.throttle, s.brake, s.gear, s.steer) for s in samples
    )


def unpack_samples(data: bytes) -> tuple[Sample, ...]:
    return tuple(Sample(*_SAMPLE.unpack_from(data, i)) for i in range(0, len(data), _SAMPLE.size))


def pack_drs(samples: list[DrsSample]) -> bytes:
    return b"".join(_DRS.pack(s.distance_m, s.lap_time_ms, s.allowed, s.active) for s in samples)


def unpack_drs(data: bytes) -> tuple[DrsSample, ...]:
    return tuple(DrsSample(*_DRS.unpack_from(data, i)) for i in range(0, len(data), _DRS.size))


def pack_ers(samples: list[ErsSample]) -> bytes:
    return b"".join(_ERS.pack(s.distance_m, s.store_j, s.deployed_j, s.harvested_j, s.deploy_mode) for s in samples)


def unpack_ers(data: bytes) -> tuple[ErsSample, ...]:
    return tuple(ErsSample(*_ERS.unpack_from(data, i)) for i in range(0, len(data), _ERS.size))


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Database:
    def __init__(self, path: Path | str = ":memory:") -> None:
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(path))
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.executescript(SCHEMA)
        self._migrate()

    def _migrate(self) -> None:
        """Dokłada kolumny dodane po pierwszych bazach (CREATE TABLE IF NOT EXISTS ich nie doda)."""
        have = {row["name"] for row in self.conn.execute("PRAGMA table_info(corner_metrics)")}
        for column, ddl in (
            ("brake_end_m", "REAL"), ("brake_release_s", "REAL"), ("max_brake", "REAL NOT NULL DEFAULT 0"),
        ):
            if column not in have:
                self.conn.execute(f"ALTER TABLE corner_metrics ADD COLUMN {column} {ddl}")
        for table in ("sessions", "laps", "progress"):  # gra: bazy sprzed adapterów gier dostają F1 25
            cols = {row["name"] for row in self.conn.execute(f"PRAGMA table_info({table})")}
            if "game" not in cols:
                self.conn.execute(f"ALTER TABLE {table} ADD COLUMN game TEXT NOT NULL DEFAULT 'f1_25'")
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()

    def save_session(self, session: SessionPacket | None, source: str) -> int:
        """Zwraca id sesji; ta sama sesja (session_uid) z tego samego źródła nie jest dublowana."""
        uid = str(session.header.session_uid) if session else None
        row = self.conn.execute(
            "SELECT id FROM sessions WHERE session_uid IS ? AND source = ?", (uid, source)
        ).fetchone()
        if row:
            return int(row["id"])
        cur = self.conn.execute(
            "INSERT INTO sessions (session_uid, source, track_id, track_name, session_type, packet_format, created_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                uid, source,
                session.track_id if session else None, session.track_name if session else None,
                session.session_type if session else None, session.header.packet_format if session else None,
                _now(),
            ),
        )
        self.conn.commit()
        return int(cur.lastrowid)  # type: ignore[arg-type]

    def save_lap(
        self,
        session_id: int,
        lap: Lap,
        analysis: LapAnalysis,
        track_length_m: float,
        track_id: int | None = None,
        gearbox: int | None = None,
        traction_control: int | None = None,
        abs_on: bool | None = None,
    ) -> int:
        """Zapisuje okrążenie z metrykami i próbkami; ten sam numer w tej samej sesji nadpisuje."""
        if track_id is None:
            row = self.conn.execute("SELECT track_id FROM sessions WHERE id = ?", (session_id,)).fetchone()
            track_id = row["track_id"] if row else None
        old = self.conn.execute(
            "SELECT id FROM laps WHERE session_id = ? AND number = ?", (session_id, lap.number)
        ).fetchone()
        if old:
            self.conn.execute("DELETE FROM laps WHERE id = ?", (old["id"],))
        cur = self.conn.execute(
            "INSERT INTO laps (session_id, track_id, number, lap_time_ms, valid, complete, pitted,"
            " gearbox, traction_control, abs_on, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                session_id, track_id, lap.number, lap.lap_time_ms, int(not lap.invalid),
                int(lap.is_complete(track_length_m)), int(lap.pitted),
                gearbox, traction_control, None if abs_on is None else int(abs_on), _now(),
            ),
        )
        lap_id = int(cur.lastrowid)  # type: ignore[arg-type]
        self.conn.executemany(
            "INSERT INTO corner_metrics (lap_id, corner, min_speed_kmh, apex_m, gear_at_apex, entry_speed_kmh,"
            " exit_speed_kmh, time_ms, brake_point_m, full_throttle_m, brake_end_m, brake_release_s, max_brake)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                (lap_id, m.corner, m.min_speed_kmh, m.apex_m, m.gear_at_apex, m.entry_speed_kmh,
                 m.exit_speed_kmh, m.time_ms, m.brake_point_m, m.full_throttle_m,
                 m.brake_end_m, m.brake_release_s, m.max_brake)
                for m in analysis.corners
            ],
        )
        self.conn.execute("INSERT INTO lap_samples VALUES (?, ?)", (lap_id, pack_samples(lap.samples)))
        for kind, data in (("drs", pack_drs(lap.drs)), ("ers", pack_ers(lap.ers))):  # kanały do wykresów w Analizie
            if data:
                self.conn.execute("INSERT INTO lap_channels VALUES (?, ?, ?)", (lap_id, kind, data))
        self.conn.commit()
        return lap_id

    @staticmethod
    def _stored(row: sqlite3.Row) -> StoredLap:
        return StoredLap(
            id=row["id"], session_id=row["session_id"], track_id=row["track_id"], number=row["number"],
            lap_time_ms=row["lap_time_ms"], valid=bool(row["valid"]), complete=bool(row["complete"]),
            pitted=bool(row["pitted"]), gearbox=row["gearbox"], traction_control=row["traction_control"],
            abs_on=None if row["abs_on"] is None else bool(row["abs_on"]),
        )

    def laps_for_track(self, track_id: int) -> list[StoredLap]:
        rows = self.conn.execute(
            "SELECT * FROM laps WHERE track_id = ? ORDER BY session_id, number", (track_id,)
        ).fetchall()
        return [self._stored(r) for r in rows]

    def best_lap(self, track_id: int, allow_invalid: bool = False) -> StoredLap | None:
        """Najszybsze ważne, pełne okrążenie bez pit lane z tego toru.

        `allow_invalid`: gdy nie ma ważnego (np. Time Trial z wyjazdami poza tor), weź najszybsze nieważne.
        """
        for valid_clause in (["AND valid = 1"] + (["AND valid = 0"] if allow_invalid else [])):
            row = self.conn.execute(
                f"SELECT * FROM laps WHERE track_id = ? {valid_clause} AND complete = 1 AND pitted = 0"
                " AND lap_time_ms IS NOT NULL ORDER BY lap_time_ms LIMIT 1",
                (track_id,),
            ).fetchone()
            if row:
                return self._stored(row)
        return None

    def corner_metrics(self, lap_id: int) -> tuple[CornerMetrics, ...]:
        rows = self.conn.execute(
            "SELECT * FROM corner_metrics WHERE lap_id = ? ORDER BY corner", (lap_id,)
        ).fetchall()
        return tuple(
            CornerMetrics(
                corner=r["corner"], min_speed_kmh=r["min_speed_kmh"], apex_m=r["apex_m"],
                gear_at_apex=r["gear_at_apex"], entry_speed_kmh=r["entry_speed_kmh"],
                exit_speed_kmh=r["exit_speed_kmh"], time_ms=r["time_ms"],
                brake_point_m=r["brake_point_m"], full_throttle_m=r["full_throttle_m"],
                brake_end_m=r["brake_end_m"], brake_release_s=r["brake_release_s"], max_brake=r["max_brake"] or 0.0,
            )
            for r in rows
        )

    def samples(self, lap_id: int) -> tuple[Sample, ...]:
        row = self.conn.execute("SELECT data FROM lap_samples WHERE lap_id = ?", (lap_id,)).fetchone()
        return unpack_samples(row["data"]) if row else ()

    def drs_samples(self, lap_id: int) -> tuple[DrsSample, ...]:
        row = self.conn.execute("SELECT data FROM lap_channels WHERE lap_id = ? AND kind = 'drs'", (lap_id,)).fetchone()
        return unpack_drs(row["data"]) if row else ()

    def ers_samples(self, lap_id: int) -> tuple[ErsSample, ...]:
        row = self.conn.execute("SELECT data FROM lap_channels WHERE lap_id = ? AND kind = 'ers'", (lap_id,)).fetchone()
        return unpack_ers(row["data"]) if row else ()

    def save_messages(self, lap_id: int, messages: list) -> None:
        self.conn.execute("DELETE FROM lap_messages WHERE lap_id = ?", (lap_id,))
        self.conn.executemany(
            "INSERT INTO lap_messages VALUES (?, ?, ?, ?)",
            [(lap_id, m.corner, m.rule, m.weight) for m in messages],
        )
        self.conn.commit()

    def lap_messages(self, lap_id: int) -> list[tuple[int, str, float]]:
        rows = self.conn.execute("SELECT corner, rule, weight FROM lap_messages WHERE lap_id = ?", (lap_id,)).fetchall()
        return [(r["corner"], r["rule"], r["weight"]) for r in rows]

    def load_progress(self, track_id: int) -> "TrackProgress":
        from boxbox.coach.progress import TrackProgress

        row = self.conn.execute("SELECT * FROM progress WHERE track_id = ?", (track_id,)).fetchone()
        if row is None:
            return TrackProgress(track_id)
        achieved = {int(x) for x in row["achieved_steps"].split(",") if x}
        return TrackProgress(track_id, row["step"], row["streak"], achieved)

    def save_progress(self, progress: "TrackProgress") -> None:
        self.conn.execute(
            "INSERT INTO progress (track_id, step, streak, achieved_steps, updated_at) VALUES (?, ?, ?, ?, ?)"
            " ON CONFLICT(track_id) DO UPDATE SET step = excluded.step, streak = excluded.streak,"
            " achieved_steps = excluded.achieved_steps, updated_at = excluded.updated_at",
            (
                progress.track_id, progress.step, progress.streak,
                ",".join(str(s) for s in sorted(progress.achieved_steps or set())), _now(),
            ),
        )
        self.conn.commit()

    def best_time_per_step(self, track_id: int) -> dict[int, int]:
        """Najlepszy ważny czas dla każdego kroku asyst (wg TC/ABS zapisanych przy okrążeniu)."""
        from boxbox.coach.progress import step_for

        out: dict[int, int] = {}
        for lap in self.laps_for_track(track_id):
            if lap.valid and lap.complete and not lap.pitted and lap.lap_time_ms:
                step = step_for(lap.traction_control, lap.abs_on)
                if step not in out or lap.lap_time_ms < out[step]:
                    out[step] = lap.lap_time_ms
        return out

    def recent_corner_issues(self, track_id: int, laps: int = 3, min_weight: float = 0.3) -> dict[int, list[str]]:
        """Zakręt -> reguły z ostatnich `laps` ważnych okrążeń. Zakręt bez wpisu = opanowany."""
        rows = self.conn.execute(
            "SELECT id FROM laps WHERE track_id = ? AND valid = 1 AND complete = 1 AND pitted = 0"
            " ORDER BY id DESC LIMIT ?",
            (track_id, laps),
        ).fetchall()
        issues: dict[int, list[str]] = {}
        for r in rows:
            for corner, rule, weight in self.lap_messages(r["id"]):
                if weight >= min_weight:
                    issues.setdefault(corner, []).append(rule)
        return issues

    def overview(self) -> dict:
        """Liczby do karty kierowcy: sesje, okrążenia, tory z najlepszym czasem."""
        sessions = self.conn.execute("SELECT COUNT(*) AS n FROM sessions").fetchone()["n"]
        laps = self.conn.execute("SELECT COUNT(*) AS n FROM laps WHERE complete = 1").fetchone()["n"]
        rows = self.conn.execute(
            "SELECT track_id, COUNT(*) AS laps, MIN(CASE WHEN valid = 1 AND pitted = 0 THEN lap_time_ms END) AS best,"
            " COUNT(DISTINCT session_id) AS sessions FROM laps WHERE track_id IS NOT NULL AND complete = 1"
            " GROUP BY track_id ORDER BY laps DESC"
        ).fetchall()
        tracks = [{"track_id": r["track_id"], "laps": r["laps"], "best_ms": r["best"], "sessions": r["sessions"]} for r in rows]
        return {"sessions": sessions, "laps": laps, "tracks": tracks}

    def lap_table(self, track_id: int, limit: int = 200) -> list[dict]:
        """Przejazdy toru od najnowszych: do tabeli w oknie."""
        rows = self.conn.execute(
            "SELECT l.id, l.number, l.lap_time_ms, l.valid, l.pitted, l.traction_control, l.abs_on, l.gearbox,"
            " l.created_at, s.source FROM laps l JOIN sessions s ON s.id = l.session_id"
            " WHERE l.track_id = ? AND l.complete = 1 ORDER BY l.id DESC LIMIT ?",
            (track_id, limit),
        ).fetchall()
        return [dict(r) for r in rows]

    def session_list(self, limit: int = 60) -> list[dict]:
        """Sesje z pełnymi okrążeniami, od najnowszej: id, data, tor, liczba okrążeń, najlepszy czas."""
        rows = self.conn.execute(
            "SELECT s.id, s.created_at, s.track_id, s.track_name, COUNT(l.id) AS laps,"
            " MIN(CASE WHEN l.valid = 1 AND l.pitted = 0 THEN l.lap_time_ms END) AS best"
            " FROM sessions s JOIN laps l ON l.session_id = s.id AND l.complete = 1"
            " GROUP BY s.id ORDER BY s.id DESC LIMIT ?", (limit,),
        ).fetchall()
        return [dict(r) for r in rows]

    def laps_for_session(self, session_id: int) -> list[StoredLap]:
        rows = self.conn.execute(
            "SELECT * FROM laps WHERE session_id = ? AND complete = 1 ORDER BY number", (session_id,)
        ).fetchall()
        return [self._stored(r) for r in rows]

    def track_hours(self) -> float:
        row = self.conn.execute("SELECT COALESCE(SUM(lap_time_ms), 0) AS ms FROM laps WHERE complete = 1").fetchone()
        return row["ms"] / 3_600_000

    def session_dates(self) -> list[str]:
        return [r["d"] for r in self.conn.execute("SELECT DISTINCT substr(created_at, 1, 10) AS d FROM sessions ORDER BY d").fetchall()]

    def reference(self, track_id: int, allow_invalid: bool = True) -> ReferenceLap | None:
        best = self.best_lap(track_id, allow_invalid)
        if best is None:
            return None
        return ReferenceLap(best, self.corner_metrics(best.id), self.samples(best.id))
