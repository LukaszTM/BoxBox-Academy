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
    assert map_for(11, tmp_path, fit_dir=tmp_path / "fit")["source"] == "outline"  # Monza bez nagrania: sam obrys z atlasu


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
    assert js(w, app, "document.querySelectorAll('.chart-line').length") >= 4  # prędkość, pedały, bieg, kierownica
    assert js(w, app, "document.querySelectorAll('.chart-ref').length") >= 1  # referencja = inne okrążenie
    assert js(w, app, "document.querySelectorAll('.chart-frame path[stroke=\"#35d07f\"], .chart-frame path[stroke=\"#ff3c42\"]').length") >= 2  # delta wokół zera
    assert js(w, app, "document.querySelector('.track-map') && document.querySelectorAll('.track-pin').length") == 6  # mapa Monzy: kształt zapisany po sesji
    assert (tmp_path / "shape" / "11.json").exists()
    # makieta v3: pasek komunikatów, sortowanie historii, samouczek, zakładka HUD z edytorem
    js(w, app, "window.boxbox.showNotice('error','Port zajęty',{label:'Sprawdź',code:'check-telemetry'}); 1")
    pump(app, 0.3)
    assert js(w, app, "document.querySelector('.notice.error .notice-content').textContent") == "Port zajęty"
    js(w, app, "document.querySelector('[data-action=notice-close]').click(); 1")
    pump(app, 0.3)
    assert js(w, app, "!document.querySelector('.notice')")
    js(w, app, "window.boxbox.navigate('progress'); document.querySelector('[data-sort=\"2\"]').click(); 1")
    pump(app, 0.4)
    assert js(w, app, "document.querySelectorAll('.data-table tbody tr').length") >= 5 and js(w, app, "!!document.querySelector('tr.best-lap')")
    js(w, app, "window.boxbox.ui.tutorial=true; window.boxbox.ui.tutorialStep=0; window.boxbox.navigate('start'); 1")
    pump(app, 0.3)
    assert "SAMOUCZEK" in js(w, app, "document.querySelector('.tutorial').textContent")
    seen = []
    for _ in range(int(js(w, app, "window.boxbox.TUTORIAL.length"))):
        seen.append(js(w, app, "window.boxbox.ui.tutorialStep + ':' + window.boxbox.ui.view + ':' + !!document.querySelector('[data-action=tutorial-next]')"))
        js(w, app, "document.querySelector('[data-action=tutorial-next]').click(); 1")
        pump(app, 0.3)
    assert js(w, app, "!document.querySelector('.tutorial')") and w.settings.tutorial_done, seen
    js(w, app, "window.boxbox.navigate('hud'); 1")
    pump(app, 2.5)
    assert js(w, app, "document.querySelector('#hud-frame').contentDocument.querySelectorAll('.block').length") == 7
    js(w, app, "window.boxbox.bridge.setSetting(JSON.stringify({hud:{positions:{status:[5,55]},visible:{minimap:false},opacity:35,scale:110}})); 1")
    pump(app, 0.4)
    assert w.settings.hud_layout["positions"]["status"] == [5, 55] and w.settings.overlay_opacity == 35 and abs(w.settings.overlay_scale - 1.1) < 1e-9
    # mostek: ustawienia i eksport CSV
    js(w, app, "window.boxbox.bridge.setSetting(JSON.stringify({volume: 200, nick: 'Nowy'})); 1")
    pump(app, 0.5)
    assert abs(w.settings.volume - 2.0) < 1e-6 and w.settings.nick == "Nowy"
    w.export_csv()
    assert list((tmp_path / "eksport").glob("okrazenie-*.csv"))
    w.close()
