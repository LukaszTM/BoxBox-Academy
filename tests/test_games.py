from pathlib import Path

from boxbox.games import DEFAULT_GAME, GAMES, adapter, split_track_key, track_key
from boxbox.storage.db import Database
from boxbox.tracks.model import track_path


def test_adapter_registry_and_track_keys() -> None:
    a = adapter()
    assert a.id == DEFAULT_GAME == "f1_25" and a.formats == (2025, 2026) and a.has_ers
    assert a.tc_levels[1] == "średnia" and len(a.assist_steps) == 4
    assert adapter("nieznana").id == "f1_25" and list(GAMES) == ["f1_25"]
    assert track_key(11) == "f1_25:11" and split_track_key("acc:7") == ("acc", 7)
    assert track_path(11).name == "11.json" and track_path(11, "acc").parts[-2:] == ("acc", "11.json")


def test_db_has_game_column_and_migrates_old_schema(tmp_path: Path) -> None:
    import sqlite3

    old = tmp_path / "stara.sqlite"
    conn = sqlite3.connect(old)
    conn.executescript(
        "CREATE TABLE sessions (id INTEGER PRIMARY KEY, session_uid TEXT, source TEXT NOT NULL, track_id INTEGER,"
        " track_name TEXT, session_type INTEGER, packet_format INTEGER, created_at TEXT NOT NULL);"
        "CREATE TABLE laps (id INTEGER PRIMARY KEY, session_id INTEGER NOT NULL, track_id INTEGER, number INTEGER NOT NULL,"
        " lap_time_ms INTEGER, valid INTEGER NOT NULL, complete INTEGER NOT NULL, pitted INTEGER NOT NULL, gearbox INTEGER,"
        " traction_control INTEGER, abs_on INTEGER, created_at TEXT NOT NULL);"
        "CREATE TABLE progress (track_id INTEGER PRIMARY KEY, step INTEGER NOT NULL, streak INTEGER NOT NULL,"
        " achieved_steps TEXT NOT NULL, updated_at TEXT NOT NULL);"
        "INSERT INTO sessions VALUES (1, '5', 'x', 11, 'Monza', 1, 2025, '2026-10-27');"
    )
    conn.commit()
    conn.close()
    db = Database(old)
    cols = {r["name"] for r in db.conn.execute("PRAGMA table_info(sessions)")}
    assert "game" in cols
    assert db.conn.execute("SELECT game FROM sessions").fetchone()["game"] == "f1_25"
    db.close()
