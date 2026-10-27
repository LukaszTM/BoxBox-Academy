"""Okno z interfejsem z makiety (Qt WebEngine, bez ekranu): kreator, sesja z nagrania, ekrany, mostek."""
import os
import time
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QTWEBENGINE_CHROMIUM_FLAGS", "--no-sandbox --disable-gpu")
pytest.importorskip("PySide6.QtWebEngineWidgets")
from PySide6.QtWidgets import QApplication  # noqa: E402

from boxbox.gui.data import DataBuilder, map_for  # noqa: E402
from boxbox.gui.settings import Settings  # noqa: E402
from boxbox.gui.webapp import WebWindow  # noqa: E402
from boxbox.session import SessionConfig  # noqa: E402

MONZA = Path("recordings/monza-trening_2026-10-26_153411.bin.xz")


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def pump(app, seconds: float) -> None:
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        app.processEvents()
        time.sleep(0.02)


def js(w: WebWindow, app, code: str, timeout: float = 5.0):
    box: dict = {}
    w.view.page().runJavaScript(code, lambda r: box.setdefault("r", r))
    end = time.monotonic() + timeout
    while "r" not in box and time.monotonic() < end:
        pump(app, 0.05)
    return box.get("r")


def wait_loaded(w: WebWindow, app) -> None:
    end = time.monotonic() + 20
    while time.monotonic() < end:
        if js(w, app, "!!(window.boxbox && document.querySelector('.page-title'))"):
            return
        pump(app, 0.2)
    raise AssertionError("interfejs nie załadował się")


def test_data_builder_empty_db(tmp_path: Path) -> None:
    d = DataBuilder(Settings(nick="X"), tmp_path / "b.sqlite", tmp_path).build()
    assert d["driver"]["nick"] == "X" and d["driver"]["level"] == 1 and d["progress"]["tracks"] == []
    assert d["analysis"]["sessions"] == [] and len(d["lessons"]["cards"]) == 5 and d["glossary"]
    assert map_for(11, tmp_path) is None


def test_window_wizard_session_and_screens(app, tmp_path: Path) -> None:
    Settings(nick="", wizard_done=False, auto_start=False).save(tmp_path / "settings.json")
    w = WebWindow(tmp_path)
    w.resize(1500, 1000)
    w.show()
    wait_loaded(w, app)
    assert "Pierwsze uruchomienie" in js(w, app, "document.title")
    for _ in range(3):
        js(w, app, "document.querySelector('[data-action=wizard-next]').click(); 1")
        pump(app, 0.2)
    js(w, app, "document.getElementById('driver-nick').value='Tester'; document.querySelector('[data-action=wizard-next]').click(); 1")
    pump(app, 0.8)
    assert w.settings.wizard_done and w.settings.nick == "Tester"
    assert js(w, app, "document.title").endswith("Start")
    assert js(w, app, "document.querySelector('.license-name').textContent") == "Tester"
    # sesja z nagrania przez okno
    w.start_session_cfg(SessionConfig(replay=MONZA, speed=0, db=tmp_path / "boxbox.sqlite", no_voice=True), overlay=False, name="monza test")
    deadline = time.monotonic() + 120
    while w.session is not None and time.monotonic() < deadline:
        pump(app, 0.2)
    pump(app, 1.0)
    assert w.session is None and w.data.summary is not None and w.data.summary["laps"] >= 5
    assert "Podsumowanie" in js(w, app, "document.title")
    assert w.settings.last_session["track"] == "Monza"
    for view, title in (("analysis", "Analiza"), ("progress", "Postęp"), ("lessons", "Lekcje"), ("driver", "Karta kierowcy"), ("settings", "Ustawienia"), ("help", "Pomoc")):
        js(w, app, f"window.boxbox.navigate('{view}'); 1")
        pump(app, 0.4)
        assert js(w, app, "document.title").endswith(title)
    js(w, app, "window.boxbox.navigate('analysis'); 1")
    pump(app, 0.5)
    assert js(w, app, "document.querySelectorAll('.chart-line').length") >= 2  # prędkość, pedały, delta
    assert js(w, app, "document.querySelectorAll('.chart-ref').length") >= 1  # referencja = inne okrążenie
    # mostek: ustawienia i eksport CSV
    js(w, app, "window.boxbox.bridge.setSetting(JSON.stringify({volume: 200, nick: 'Nowy'})); 1")
    pump(app, 0.5)
    assert abs(w.settings.volume - 2.0) < 1e-6 and w.settings.nick == "Nowy"
    w.export_csv()
    assert list((tmp_path / "eksport").glob("okrazenie-*.csv"))
    w.close()
