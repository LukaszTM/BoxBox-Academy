"""Okno Qt bez ekranu (QT_QPA_PLATFORM=offscreen): strony, samouczek, sesja z nagrania, karta kierowcy."""
import os
import time
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")
from PySide6.QtWidgets import QApplication  # noqa: E402

from boxbox.gui import texts  # noqa: E402
from boxbox.gui.main import MainWindow  # noqa: E402
from boxbox.gui.probe import ProbeResult, probe  # noqa: E402
from boxbox.gui.settings import Settings  # noqa: E402
from boxbox.session import SessionConfig  # noqa: E402

MONZA = Path("recordings/monza-glos-test2_2026-10-26_232722.bin.xz")


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def pump(app, seconds: float = 0.0) -> None:
    end = time.monotonic() + seconds
    app.processEvents()
    while time.monotonic() < end:
        app.processEvents()
        time.sleep(0.02)


def test_settings_roundtrip(tmp_path: Path) -> None:
    s = Settings(nick="KIEROWCA", volume=2.0)
    s.save(tmp_path / "s.json")
    again = Settings.load(tmp_path / "s.json")
    assert again.nick == "KIEROWCA" and again.volume == 2.0 and again.player_id == s.player_id
    assert Settings.load(tmp_path / "brak.json").nick == ""


def test_probe_on_free_port_reports_nothing() -> None:
    r = probe(port=0, seconds=0.2)  # port 0 = dowolny wolny: nic nie dotrze, ale gniazdo się otworzy
    assert r.packets == 0 and not r.busy and not r.connected and r.rate == 0


def test_window_first_run_shows_wizard_then_tutorial(app, tmp_path: Path) -> None:
    w = MainWindow(tmp_path)
    w.show()
    pump(app)
    assert w.current_page() == "wizard"
    wizard = w.pages["wizard"]
    for _ in range(3):
        wizard.on_next()
    wizard.nick.setText("Tester")
    wizard.on_next()  # ostatni krok: zapis i przejście do startu
    pump(app, 0.5)
    assert w.current_page() == "home" and w.ctx.settings.wizard_done and w.ctx.settings.nick == "Tester"
    assert (tmp_path / "settings.json").exists()
    assert w.bubble.isVisible() and w.tutorial_index == 0
    for _ in range(len(texts.TUTORIAL)):
        w.tutorial_next()
        pump(app)
    assert not w.bubble.isVisible() and w.ctx.settings.tutorial_done
    for key in texts.NAV:
        w.show_page(key)
        assert w.current_page() == key
    w.close()


def test_home_runs_replay_session_and_shows_summary(app, tmp_path: Path) -> None:
    s = Settings(wizard_done=True, tutorial_done=True, overlay=False)
    s.save(tmp_path / "settings.json")
    w = MainWindow(tmp_path)
    w.show()
    pump(app)
    home = w.pages["home"]
    home.use_overlay.setChecked(False)
    home.start_session(SessionConfig(replay=MONZA, speed=0, db=tmp_path / "boxbox.sqlite", no_voice=True))
    assert home.go.text() == texts.HOME["stop"]
    deadline = time.monotonic() + 120
    while home.session is not None and time.monotonic() < deadline:
        pump(app, 0.1)
    assert home.session is None and home.go.text() == texts.HOME["go"]
    text = home.l_messages.toPlainText()
    assert "Mechanik na radiu" in text and "Okrążenie" in text
    assert home.summary.isVisible() and "Monza" in home.summary.toPlainText()
    w.show_page("profile")
    assert w.pages["profile"].c_laps.value.text() != "0"
    w.show_page("progress")
    progress = w.pages["progress"]
    assert progress.track_box.count() == 1 and progress.table.rowCount() > 0 and "Krok" in progress.step_label.text()
    w.close()


def test_probe_result_properties() -> None:
    r = ProbeResult(packets=120, seconds=2.0, fmt=2025, track="Monza")
    assert r.connected and r.rate == 60.0 and r.supported
