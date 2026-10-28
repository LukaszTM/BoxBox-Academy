"""Raport sesji HTML (do PDF): radar, sześć linii, zadanie, tabele; działa też bez profilu."""
from boxbox.gui.report import radar_svg, session_report_html

SUMMARY = {
    "name": "monza test", "track": "Monza", "trackId": 11, "laps": 5, "elapsed": 420.0, "date": "28.10.2026", "coach": True,
    "best": "1:26.918", "clean": 2, "delta": -0.4, "good": "Nowe najlepsze okrążenie", "toWork": "T1-T2: hamowanie za późno",
    "lapRows": [{"number": 2, "time": "1:33.476", "delta": "+6.558", "valid": True, "notes": 2},
                {"number": 6, "time": "1:26.918", "delta": "+0.000", "valid": True, "notes": 0, "sectors": ["28.038", "29.112", "29.768"], "bestSectors": [True, True, False]}],
    "idealLap": "1:26.908",
    "cornerRows": [["T1-T2", "62 km/h", "1", "779 m", "1024 m", "–"]],
}
PROFILE = {
    "trackId": 11, "track": "Monza", "lapsUsed": 10, "note": "", "ref": "twoje najlepsze 1:26,918 (26.10)",
    "skills": [
        {"key": "braking", "name": "Hamowanie", "score": 68, "trend": 12, "hint": "hamuj ok. 20 m później w T4", "corner": 2, "cornerName": "T4-T5"},
        {"key": "brake_control", "name": "Praca hamulcem", "score": 46, "trend": -5, "hint": "zwalniaj hamulec stopniowo aż do apeksu w T1-T2"},
        {"key": "throttle", "name": "Gaz na wyjściu", "score": 74, "trend": 7, "hint": "łagodniej z gazem na wyjściu z T8-T10, tam tracisz przyczepność"},
        {"key": "consistency", "name": "Powtarzalność", "score": 59, "trend": -3, "hint": "3 z 5 okrążeń czystych; największe błędy w T1-T2"},
        {"key": "pace", "name": "Tempo", "score": 72, "trend": 9, "hint": "najwięcej czasu tracisz w T6: 0,4 s na okrążenie"},
        {"key": "independence", "name": "Samodzielność", "score": 53, "trend": 8, "hint": "2 czyste okrążenia do kroku: ABS wyłączony"},
    ],
}


def test_report_with_profile_has_radar_rows_task_and_tables() -> None:
    page = session_report_html(SUMMARY, PROFILE, "Tester", "F1 25")
    assert page.startswith("<!doctype html>") and "<svg" in page and page.count("<polygon") == 5 + 2  # siatka 5 + poprzednie + obecne
    assert page.count('class="row"') == 6 and "▲ +12" in page and "▼ −5" in page
    assert "Zwalniaj hamulec stopniowo aż do apeksu w T1-T2." in page  # zadanie = najsłabszy wymiar (46)
    assert "Monza · 28.10.2026 · 5 okrążeń · najlepsze 1:26.918 · Tester" in page
    assert "Nowe najlepsze okrążenie" in page and "T1-T2: hamowanie za późno" in page
    assert '<tr class="best"><td>6</td>' in page and "<td>779 m</td>" in page and "Poprzednie 10" in page
    assert '<td class="best-sector">28.038</td><td class="best-sector">29.112</td><td class="">29.768</td>' in page  # sektory z wyróżnieniem
    assert "z najlepszych sektorów 1:26.908" in page and page.count('<td class="">-</td>') == 3  # okrążenie 2 bez sektorów
    assert "&lt;" not in page.split("<body>")[0]  # bez wycieków HTML w nagłówku


def test_report_without_profile_and_escaping() -> None:
    summary = dict(SUMMARY, good="<b>x</b>", lapRows=[], cornerRows=[])
    page = session_report_html(summary, None, "")
    assert page.count("—") >= 6 and "Za mało okrążeń, żeby ocenić." in page and "Profil powstaje z minimum 5" in page
    assert "&lt;b&gt;x&lt;/b&gt;" in page and "<b>x</b>" not in page
    assert "OKRĄŻENIA</h2>" not in page and "T1-T2: hamowanie za późno" in page  # zadanie z „do pracy”, gdy nie ma profilu
    svg = radar_svg([10, None, 30, 40, 50, 60], None, ["a", "b", "c", "d", "e", "f"])
    assert svg.count("<polygon") == 5 and 'fill="#778596"' in svg  # bez pełnego kompletu: tylko siatka i punkty
