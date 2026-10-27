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
}


def main() -> None:
    DIST.mkdir(exist_ok=True)
    for src, (name, title) in DOCS.items():
        build_pdf(DIST / name, source=ROOT / "docs" / src, title=title)
        print(f"PDF: {DIST / name}")


if __name__ == "__main__":
    main()
