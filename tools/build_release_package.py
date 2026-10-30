"""Paczka ZIP z całym programem do pobrania (okno, trener, HUD, dokumentacja, klipy głosu).

Użycie: python tools/build_release_package.py
Wynik:  dist/BoxBoxAcademy-<wersja>.zip (z klipami głosu) i dist/BoxBoxAcademy-<wersja>-bez-glosu.zip

Do paczki nie trafiają: nagrania, baza, ustawienia, zdjęcia, surowe klipy (assets/voice/raw), testy, __pycache__.
"""
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from build_recorder_package import DIST, ROOT, _add, _dirs_added  # noqa: E402

from boxbox.gui import texts  # noqa: E402

PDFS = (
    "BoxBox_Academy_dokumentacja.pdf", "BoxBox_Academy_instrukcja_nagran.pdf", "BoxBox_Academy_antywirus.pdf",
    "BoxBox_Academy_co_nagrac.pdf", "BoxBox_Academy_formularze_nagran.pdf", "BoxBox_Academy_analiza_umiejetnosci.pdf",
    "BoxBox_Academy_lista_torow.pdf",
)
README = """BoxBox Academy {version} - trener jazdy do F1 25 (beta)

URUCHOMIENIE (Windows):
  1. Zainstaluj Python 3.12 lub nowszy z python.org (zaznacz "Add python.exe to PATH").
  2. Kliknij dwa razy akademia.bat. Przy pierwszym uruchomieniu doinstaluje sie PySide6 (kilka minut).
  3. W grze: Ustawienia -> Telemetria UDP wlaczona, port 20777, adres 127.0.0.1, format 2025 albo 2026.
  4. Przejdz kreator w oknie i kliknij JEDZ. Gra w trybie okna bez ramki, jesli chcesz nakladke HUD.

GLOS MECHANIKA: klipy sa w assets\\voice. Jesli paczka jest "bez-glosu", skopiuj tam klipy
  albo wygeneruj je przez wygeneruj_glos.bat (klucz ElevenLabs tylko w zmiennej srodowiskowej).

DOKUMENTACJA: folder docs (PDF). Gdy Windows blokuje program: BoxBox_Academy_antywirus.pdf.
TESTERZY: Discord https://discord.gg/t82VhVkVq (zgloszenia bledow, nagrania, pomysly).
DANE: wszystko zostaje na tym komputerze w folderach data i recordings obok programu.
"""


def build(target: Path, with_voice: bool) -> None:
    package_dir = ROOT / "tools" / "package"
    _dirs_added.clear()
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as z:
        _add(z, ROOT, "CZYTAJ-TO.txt", README.format(version=texts.VERSION).replace("\n", "\r\n").encode("utf-8"))
        for extra in sorted(package_dir.rglob("*")):
            if extra.is_file():
                _add(z, extra, extra.relative_to(package_dir).as_posix())
        for path in sorted((ROOT / "boxbox").rglob("*")):
            if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc":
                _add(z, path, path.relative_to(ROOT).as_posix())
        _add(z, ROOT / "pyproject.toml", "pyproject.toml")
        _add(z, ROOT / "assets" / "voice" / "phrases.csv", "assets/voice/phrases.csv")
        if with_voice:
            for path in sorted((ROOT / "assets" / "voice").glob("*.wav")):
                _add(z, path, f"assets/voice/{path.name}")
        for name in PDFS:
            pdf = DIST / name
            if pdf.exists():
                _add(z, pdf, f"docs/{name}")
        for form in sorted((ROOT / "docs" / "formularze").glob("*.txt")):
            _add(z, form, f"docs/formularze/{form.name}")
        _add(z, ROOT, "recordings/README-tu-trafiaja-nagrania.txt", b"Nagrania sesji zapisuja sie w tym folderze.\r\n")
        _add(z, ROOT, "data/README.txt", b"Baza, ustawienia, raporty i pliki torow programu.\r\n")


def main() -> None:
    DIST.mkdir(exist_ok=True)
    for suffix, voice in (("", True), ("-bez-glosu", False)):
        target = DIST / f"BoxBoxAcademy-{texts.VERSION}{suffix}.zip"
        build(target, voice)
        print(f"ZIP: {target} ({target.stat().st_size / 1_000_000:.1f} MB)")


if __name__ == "__main__":
    main()
