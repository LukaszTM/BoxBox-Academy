"""Buduje PDF-y z dokumentów Markdown w docs/ tym samym silnikiem co instrukcja nagrań.

Użycie: python tools/build_docs.py  ->  dist/BoxBox_Academy_plan_testow.pdf, dist/BoxBox_Academy_dokumentacja.pdf
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_recorder_package import DIST, ROOT, build_pdf  # noqa: E402

DOCS = {
    "PLAN_TESTOW.md": ("BoxBox_Academy_plan_testow.pdf", "BoxBox Academy – plan testów"),
    "DOKUMENTACJA.md": ("BoxBox_Academy_dokumentacja.pdf", "BoxBox Academy – dokumentacja"),
    "WYTYCZNE_GUI.md": ("BoxBox_Academy_wytyczne_GUI_i_marki.pdf", "BoxBox Academy – wytyczne GUI i marki"),
    "SPECYFIKACJA_FUNKCJI.md": ("BoxBox_Academy_specyfikacja_funkcji.pdf", "BoxBox Academy – specyfikacja funkcji i rozpiska do makiety"),
    "LISTA_TOROW.md": ("BoxBox_Academy_lista_torow.pdf", "BoxBox Academy – lista torów F1 25 i sezon 2026"),
    "MAKIETA_V2_BRIEF.md": ("BoxBox_Academy_makieta_v2_wytyczne.pdf", "BoxBox Academy – makieta v2 i nakładka HUD: wytyczne"),
    "MAKIETA_V2_OCENA.md": ("BoxBox_Academy_makieta_v2_ocena.pdf", "BoxBox Academy – makieta v2 i HUD v2: ocena i zmiany"),
    "LOGO_WYTYCZNE.md": ("BoxBox_Academy_logo_wytyczne.pdf", "BoxBox Academy – logo: wytyczne do przeróbki"),
}


def main() -> None:
    DIST.mkdir(exist_ok=True)
    for src, (name, title) in DOCS.items():
        build_pdf(DIST / name, source=ROOT / "docs" / src, title=title)
        print(f"PDF: {DIST / name}")


if __name__ == "__main__":
    main()
