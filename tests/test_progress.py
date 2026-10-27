from pathlib import Path

from boxbox.app import main as app_main
from boxbox.coach.analyze import render_progress
from boxbox.coach.laps import Lap
from boxbox.coach.progress import STEPS, TrackProgress, is_clean, step_for
from boxbox.coach.rules import Message
from boxbox.storage.db import Database
from tests.conftest import RecordedSession
from tests.synthetic import LENGTH
from tests.test_laps import synthetic_samples


def lap(number: int, tc: int | None = 2, abs_on: bool | None = True, invalid: bool = False, pitted: bool = False) -> Lap:
    return Lap(number, synthetic_samples(), 90_000, invalid=invalid, pitted=pitted, traction_control=tc, abs_on=abs_on, track_length_m=LENGTH)


def big(corner: int = 1) -> Message:
    return Message(1, corner, "T1", "brake_late", "p", "h", 2.5, variant="big")


def small() -> Message:
    return Message(1, 2, "T4", "throttle_late", "p", "h", 0.4)


def test_step_for_and_clean() -> None:
    assert step_for(2, True) == 1 and step_for(None, None) == 1 and step_for(1, True) == 2
    assert step_for(0, True) == 3 and step_for(0, False) == 4
    assert is_clean(lap(1), [small()]) and not is_clean(lap(1), [big()])
    assert not is_clean(lap(1, invalid=True), []) and not is_clean(lap(1, pitted=True), [])


def test_progress_streak_and_step_change() -> None:
    p = TrackProgress(3)
    assert p.record(lap(1), []) == ("streak_1", "Czyste okrążenie, pierwsze z trzech.")
    assert p.record(lap(2), [small()]) == ("streak_2", "Czyste okrążenie, drugie z trzech.")
    clip, text = p.record(lap(3), [])
    assert clip == "step_tc_medium" and "kontrola trakcji na średnią" in text and p.achieved_steps == {1}
    assert p.record(lap(4), []) == (None, None)  # cel kroku 1 ogłoszony raz
    assert p.record(lap(5), [big()]) == (None, None) and p.streak == 0
    # zmiana asyst -> nowy krok, seria od zera
    assert p.record(lap(6, tc=1), []) == ("streak_1", "Czyste okrążenie, pierwsze z trzech.") and p.step == 2
    p.record(lap(7, tc=1), []); clip, _ = p.record(lap(8, tc=1), [])
    assert clip == "step_tc_off"
    p2 = TrackProgress(3, step=4)
    for n in (1, 2):
        p2.record(lap(n, tc=0, abs_on=False), [])
    assert p2.record(lap(3, tc=0, abs_on=False), [])[0] == "step_done"
    assert p.record(lap(9, tc=1, pitted=True), []) == (None, None)  # pit: nie liczy się ani w górę, ani w dół


def test_progress_persists_in_db(tmp_path: Path) -> None:
    db = Database(tmp_path / "p.sqlite")
    p = db.load_progress(11)
    assert (p.step, p.streak, p.achieved_steps) == (1, 0, set())
    p.record(lap(1, tc=0), []); p.record(lap(2, tc=0), []); p.record(lap(3, tc=0), [])
    db.save_progress(p)
    again = db.load_progress(11)
    assert (again.step, again.streak, again.achieved_steps) == (3, 3, {3})


def test_report_saves_messages_and_progress_screen(tmp_path: Path, monza: RecordedSession, capsys) -> None:
    db_file = tmp_path / "m.sqlite"
    assert app_main(["--replay", "recordings/monza-trening_2026-10-26_153411.bin.xz", "--speed", "0", "--db", str(db_file)]) == 0
    db = Database(db_file)
    laps = db.laps_for_track(11)
    assert laps
    lap4 = next(s for s in laps if s.number == 4)
    rules = {r for _, r, _ in db.lap_messages(lap4.id)}
    assert "brake_late" in rules
    assert db.load_progress(11).step == 2  # TC średnia w tej sesji
    issues = db.recent_corner_issues(11)
    assert isinstance(issues, dict)
    text = render_progress(db)
    assert text.startswith("Monza: krok 2 (TC średnia)") and "najlepszy czas, krok 2" in text and "zakręty opanowane" in text
    db.close()
    capsys.readouterr()
    assert app_main(["--progress", "--db", str(db_file)]) == 0
    assert "Monza: krok 2" in capsys.readouterr().out


def test_emphasis_after_removing_assists() -> None:
    from boxbox.coach.rules import emphasize
    msgs = [Message(1, 1, "T1", "throttle_early", "p", "h", 1.0), Message(1, 2, "T4", "brake_release", "p", "h", 1.0)]
    assert [m.weight for m in emphasize(msgs, 2, True)] == [1.0, 1.0]
    assert [m.weight for m in emphasize(msgs, 0, True)] == [1.5, 1.0]
    assert [m.weight for m in emphasize(msgs, 0, False)] == [1.5, 1.5]
