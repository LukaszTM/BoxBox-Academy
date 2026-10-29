"""Okno z interfejsem z makiety (Qt WebEngine, bez ekranu): kreator, sesja z nagrania, ekrany, mostek."""
import os
import re
import time
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QTWEBENGINE_CHROMIUM_FLAGS", "--no-sandbox --disable-gpu")
pytest.importorskip("PySide6.QtWebEngineWidgets")
from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from boxbox.gui.data import DataBuilder, map_for  # noqa: E402
from boxbox.gui.settings import Settings  # noqa: E402
from boxbox.gui.webapp import WebWindow, zoom_for_width, zoom_for_window  # noqa: E402
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
    assert d["analysis"]["sessions"] == [] and len(d["lessons"]["cards"]) == 7 and d["glossary"]
    assert d["skills"] == {"tracks": [], "all": None, "minLaps": 5, "window": 10}  # pusta baza: zakładka pokazuje stan „profil się tworzy”
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
    # raport PDF sesji przez Qt (bez okna drukowania): plik w data/raporty
    js(w, app, "document.querySelector('[data-action=session-report]').click(); 1")
    end = time.monotonic() + 30
    while w.report_path is None and time.monotonic() < end:
        pump(app, 0.2)
    assert w.report_path is not None and w.report_path.exists() and w.report_path.stat().st_size > 10_000 and w.report_path.name.startswith("raport-monza-")
    assert w.report_path.read_bytes()[:5] == b"%PDF-"
    pump(app, 1.0)  # komunikat „Zapisano raport” dociera do strony chwilę po zapisie
    assert any(r["key"] == "first_clean" and r["got"] for r in w.data.build()["progress"]["badges"])  # odznaki z silnika
    for view, title in (("analysis", "Analiza"), ("progress", "Postęp"), ("skills", "Umiejętności"), ("lessons", "Lekcje"), ("driver", "Karta kierowcy"), ("settings", "Ustawienia"), ("help", "Pomoc")):
        js(w, app, f"window.boxbox.navigate('{view}'); 1")
        pump(app, 0.4)
        assert js(w, app, "document.title").endswith(title)
    # makieta v4: Umiejętności z silnika (Monza: 5 ważnych okrążeń = profil), karta -> Analiza z banerem, mini-radar w karcie kierowcy
    skills = w.data.build()["skills"]
    assert [t["track"] for t in skills["tracks"]] == ["Monza"] and skills["all"]["lapsUsed"] >= 5
    assert all(s["score"] is not None for s in skills["tracks"][0]["skills"]) and skills["tracks"][0]["ref"].startswith("twoje najlepsze 1:")
    js(w, app, "window.boxbox.navigate('skills'); 1")
    pump(app, 0.5)
    assert js(w, app, "document.querySelectorAll('.skill-card').length") == 6 and js(w, app, "!!document.querySelector('.skill-radar-current')")
    assert js(w, app, "document.querySelectorAll('.skill-number').length") == 6 and "—" not in js(w, app, "Array.from(document.querySelectorAll('.skill-number')).map(e=>e.textContent).join()")
    assert js(w, app, "document.querySelector('.skill-goal-text').textContent").strip() != ""
    js(w, app, "document.querySelector('[data-skills-track=\"11\"]').click(); 1")
    pump(app, 0.4)
    assert "Monza" in js(w, app, "document.querySelector('.skills-meta').textContent")
    js(w, app, "document.querySelector('.skill-card[data-skill-open=\"braking\"]').click(); 1")
    pump(app, 0.5)
    assert js(w, app, "document.title").endswith("Analiza") and "Hamowanie" in js(w, app, "document.querySelector('.skill-analysis-return').textContent")
    js(w, app, "document.querySelector('[data-action=skills-back]').click(); 1")
    pump(app, 0.4)
    assert js(w, app, "document.title").endswith("Umiejętności")
    js(w, app, "document.querySelector('[data-action=skills-lesson]').click(); 1")
    pump(app, 0.4)
    assert js(w, app, "document.title").endswith("Lekcje") and js(w, app, "window.boxbox.ui.lesson") in ("braking_one_corner", "trail_braking", "throttle_exit", "clean_lap")
    js(w, app, "window.boxbox.navigate('driver'); 1")
    pump(app, 0.4)
    assert js(w, app, "!!document.querySelector('.license-radar-link svg')")
    # tło z głębią (siatka, poświaty, obrys toru z sesji) i skalowanie okna przy maksymalizacji na 2560 px
    assert js(w, app, "document.querySelectorAll('.bg-3d .bg-glow').length") == 3 and js(w, app, "(document.querySelector('.bg-track .road').getAttribute('d')||'').length") > 200
    assert js(w, app, "!!document.querySelector('.bg-track .start')")  # start/meta z kształtu Monzy
    assert w.view.zoomFactor() == 1.0
    w.resize(2560, 1400)
    pump(app, 0.3)
    assert abs(w.view.zoomFactor() - 1.45) < 0.01 and zoom_for_width(1920) == 1.097 and zoom_for_width(1200) == 1.0
    # wysokie okna: powiększenie z wysokości, ale nie poniżej szerokości jednokolumnowego układu
    assert zoom_for_window(1920, 1080) == 1.097 and zoom_for_window(1920, 1200) == 1.2 and zoom_for_window(1600, 1300) == 1.3
    assert zoom_for_window(1480, 960) == 1.0 and zoom_for_window(2560, 1440) == 1.45 and zoom_for_window(1200, 1400) == 1.017
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
    assert js(w, app, "(document.querySelector('.notice')||{textContent:''}).textContent") == ""
    js(w, app, "window.boxbox.navigate('progress'); document.querySelector('[data-sort=\"2\"]').click(); 1")
    pump(app, 0.4)
    assert js(w, app, "document.querySelectorAll('.data-table tbody tr').length") >= 5 and js(w, app, "!!document.querySelector('tr.best-lap')")
    # spójność jazdy i „wtedy vs dziś” (jedna sesja: porównanie dopiero po drugim dniu)
    prog = w.data.build()["progress"]
    assert prog["consistency"]["laps"] >= 3 and prog["consistency"]["spread"].startswith("±") and prog["clean"]["share"].endswith("%")
    assert prog["thenNow"] is None and "Spójność jazdy" in js(w, app, "document.body.textContent") and "Wtedy vs dziś" in js(w, app, "document.body.textContent")
    # sektory z nagrania Monzy: w historii, suma najlepszych, wyróżnienie w tabeli podsumowania
    assert len(prog["history"][0]) == 14 and all(re.match(r"^\d+\.\d{3}$", x) for x in prog["history"][1][3:6]) and prog["idealLap"].startswith("1:2")
    assert js(w, app, "document.querySelectorAll('.data-table td.best-sector').length") >= 3
    summ = w.data.build()["summary"]
    assert summ["idealLap"].startswith("1:2") and any(any(r["bestSectors"]) for r in summ["lapRows"]) and "S1" in js(w, app, "document.querySelector('.data-table thead').textContent")
    # Analiza: dowolne okrążenie sesji jako referencja
    an = w.data.build()["analysis"]
    other = next(c for c in an["comps"] if c["id"].startswith("lap:"))
    w.data.analysis_sel["comp"] = other["id"]
    an2 = w.data.build()["analysis"]
    assert an2["comp"] == other["id"] and an2["compLabel"].startswith("okrążenie ") and an2["speed"]["ref"]
    w.data.analysis_sel["comp"] = "best"
    # kanały DRS i ERS z bazy: wykresy i strefy DRS na mapie
    assert len(an["drs"]["own"]) == 120 and an["drs"]["zones"] == 2 and an["drs"]["used"] == 2 and len(an["ers"]["own"]) == 120
    assert len(an["map"]["drsZones"]) == 2
    js(w, app, "window.boxbox.navigate('analysis'); 1")
    pump(app, 0.4)
    assert js(w, app, "document.querySelectorAll('.track-drs.used').length") == 2 and "BATERIA ERS" in js(w, app, "document.body.textContent")
    js(w, app, "window.boxbox.ui.tutorial=true; window.boxbox.ui.tutorialStep=0; window.boxbox.navigate('start'); 1")
    pump(app, 0.3)
    assert "SAMOUCZEK" in js(w, app, "document.querySelector('.tutorial').textContent")
    seen = []
    for _ in range(int(js(w, app, "window.boxbox.TUTORIAL.length"))):
        seen.append(js(w, app, "window.boxbox.ui.tutorialStep + ':' + window.boxbox.ui.view + ':' + !!document.querySelector('[data-action=tutorial-next]')"))
        js(w, app, "document.querySelector('[data-action=tutorial-next]').click(); 1")
        pump(app, 0.3)
    assert js(w, app, "!document.querySelector('.tutorial')") and w.settings.tutorial_done, seen
    assert w.say_tutorial(0) is False  # lektor samouczka: bez klipów w bibliotece cicho, bez błędu
    js(w, app, "window.boxbox.navigate('hud'); 1")
    pump(app, 2.5)
    assert js(w, app, "document.querySelector('#hud-frame').contentDocument.querySelectorAll('.block').length") == 8  # z modułem DRS · bateria · sektory
    js(w, app, "window.boxbox.bridge.setSetting(JSON.stringify({hud:{positions:{status:[5,55]},visible:{minimap:false},opacity:35,scale:110}})); 1")
    pump(app, 0.4)
    assert w.settings.hud_layout["positions"]["status"] == [5, 55] and w.settings.overlay_opacity == 35 and abs(w.settings.overlay_scale - 1.1) < 1e-9
    # mostek: ustawienia i eksport CSV
    js(w, app, "window.boxbox.bridge.setSetting(JSON.stringify({volume: 200, nick: 'Nowy', photoFit: {x: 30, y: 120, zoom: 180}})); 1")
    pump(app, 0.5)
    assert abs(w.settings.volume - 2.0) < 1e-6 and w.settings.nick == "Nowy"
    assert w.settings.photo_fit == {"x": 30, "y": 100, "zoom": 180} and w.data.build()["driver"]["photoFit"] == {"x": 30, "y": 100, "zoom": 180}  # przycięte do zakresu
    w.export_csv()
    csv_files = list((tmp_path / "eksport").glob("okrazenie-*.csv"))
    assert csv_files and csv_files[0].read_text(encoding="utf-8-sig").splitlines()[0].endswith(";drs;bateria_mj")  # kanały z bazy w CSV
    w.close()


def test_hud_overlay_follows_session(app, tmp_path: Path) -> None:
    """Nakładka HUD nad grą: przezroczyste okno, treść z sesji, minimapa po dopasowaniu atlasu, plansza po okrążeniu."""
    from boxbox.gui.hud import HudWindow, demo_frame

    Settings(nick="Tester", wizard_done=True, tutorial_done=True, auto_start=False).save(tmp_path / "settings.json")
    w = WebWindow(tmp_path)
    w.show()
    wait_loaded(w, app)
    w.start_session_cfg(SessionConfig(replay=MONZA, speed=12.0, db=tmp_path / "boxbox.sqlite", no_voice=True), overlay=True, name="monza hud")
    ov = w.overlay
    assert isinstance(ov, HudWindow) and ov.windowFlags() & Qt.WindowType.WindowTransparentForInput

    def ovjs(code: str):
        box: dict = {}
        ov.page().runJavaScript(code, lambda r: box.setdefault("r", r))
        end = time.monotonic() + 5
        while "r" not in box and time.monotonic() < end:
            pump(app, 0.05)
        return box.get("r")

    deadline = time.monotonic() + 150
    fit_done = seen_finish = False
    while w.session is not None and time.monotonic() < deadline:
        pump(app, 0.2)
        if w.session is None:
            break
        with w.session.shared.lock:
            n = len(w.session.shape_sampler.all_samples())
        if not fit_done and n > 1500:
            w.fit_atlas_now(wait=True)
            fit_done = True
            pump(app, 0.6)
            assert (tmp_path / "atlas_fit" / "11.json").exists()
            assert ovjs("document.querySelector('.block.minimap').className") == "block minimap"  # minimapa widoczna
            assert ovjs("(document.getElementById('track-outline').getAttribute('d')||'').length") > 100
            assert "TRENER · MONZA" in ovjs("document.getElementById('status-value').textContent")
        if not seen_finish and "finish" in (ovjs("document.getElementById('hud').className") or ""):
            seen_finish = True
            assert "OKRĄŻENIE" in ovjs("document.querySelector('.lapend-head').textContent")
            assert ovjs("document.querySelector('.timing-label').textContent").startswith("OKRĄŻENIE")
            assert "CZYSTYCH" in ovjs("document.querySelector('.timing-foot').textContent")
            assert ovjs("document.querySelector('.radio-line').textContent")  # mechanik mówił
            assert ovjs("document.getElementById('energy-batt').textContent").endswith("%")  # moduł DRS · bateria · sektory z telemetrii
            assert ovjs("document.getElementById('energy-drs').textContent") in ("—", "GOTOWY", "OTWARTY")
    assert fit_done and seen_finish
    pump(app, 1.0)
    assert w.session is None and w.overlay is None  # po sesji nakładka znika
    # podgląd na 5 s bez sesji
    w.preview_overlay()
    pump(app, 1.5)
    assert w._preview.isVisible() and demo_frame().corner == "T8–T10"
    w._preview.close()
    w.close()
