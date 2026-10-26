"""Buduje paczkę dla nagrywającego: PDF z instrukcją + recorder + skrypty .bat.

Użycie: python tools/build_recorder_package.py  ->  dist/boxbox-recorder.zip
Źródło instrukcji: docs/NAGRANIA.md (prosty podzbiór Markdown: nagłówki, listy,
tabele, bloki kodu, **pogrubienie**, `kod`).
"""
import re
import shutil
import zipfile
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    ListFlowable, ListItem, Paragraph, Preformatted, SimpleDocTemplate, Spacer, Table, TableStyle,
)

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "docs" / "NAGRANIA.md"
DIST = ROOT / "dist"
PDF_NAME = "BoxBox_Academy_instrukcja_nagran.pdf"
ZIP_NAME = "boxbox-recorder.zip"
FONT_DIR = Path("/usr/share/fonts/truetype/dejavu")


def _register_fonts() -> None:
    pdfmetrics.registerFont(TTFont("DejaVu", FONT_DIR / "DejaVuSans.ttf"))
    pdfmetrics.registerFont(TTFont("DejaVu-Bold", FONT_DIR / "DejaVuSans-Bold.ttf"))
    pdfmetrics.registerFont(TTFont("DejaVuMono", FONT_DIR / "DejaVuSansMono.ttf"))
    pdfmetrics.registerFontFamily("DejaVu", normal="DejaVu", bold="DejaVu-Bold", italic="DejaVu", boldItalic="DejaVu-Bold")


def _styles() -> dict[str, ParagraphStyle]:
    base = ParagraphStyle("base", fontName="DejaVu", fontSize=10, leading=14, alignment=TA_LEFT)
    return {
        "body": base,
        "h1": ParagraphStyle("h1", parent=base, fontName="DejaVu-Bold", fontSize=18, leading=22, spaceAfter=6),
        "h2": ParagraphStyle("h2", parent=base, fontName="DejaVu-Bold", fontSize=13, leading=17, spaceBefore=12, spaceAfter=4, keepWithNext=True),
        "h3": ParagraphStyle("h3", parent=base, fontName="DejaVu-Bold", fontSize=11, leading=15, spaceBefore=8, spaceAfter=2, keepWithNext=True),
        "cell": ParagraphStyle("cell", parent=base, fontSize=9, leading=12),
        "cellhead": ParagraphStyle("cellhead", parent=base, fontName="DejaVu-Bold", fontSize=9, leading=12),
        "code": ParagraphStyle("code", parent=base, fontName="DejaVuMono", fontSize=8.5, leading=11,
                               backColor=colors.whitesmoke, borderPadding=4, leftIndent=4),
    }


def _inline(text: str) -> str:
    """Markdown inline -> znaczniki reportlab."""
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"`(.+?)`", r'<font face="DejaVuMono">\1</font>', text)
    text = re.sub(r"(https?://[^\s)]+)", r'<link href="\1" color="blue">\1</link>', text)
    return text


def _table(rows: list[list[str]], st: dict[str, ParagraphStyle], width: float) -> Table:
    data = [[Paragraph(_inline(c), st["cellhead"]) for c in rows[0]]]
    data += [[Paragraph(_inline(c), st["cell"]) for c in r] for r in rows[1:]]
    ncols = len(rows[0])
    first = 0.32 if ncols == 2 else 1 / ncols
    widths = [width * first] + [width * (1 - first) / (ncols - 1)] * (ncols - 1)
    table = Table(data, colWidths=widths, repeatRows=1)
    table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8e8e8")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ]))
    return table


def markdown_to_story(text: str, width: float) -> list:
    st = _styles()
    story: list = []
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
            continue
        if line.startswith("```"):
            block: list[str] = []
            i += 1
            while i < len(lines) and not lines[i].startswith("```"):
                block.append(lines[i])
                i += 1
            story.append(Preformatted("\n".join(block), st["code"]))
            story.append(Spacer(1, 6))
            i += 1
            continue
        if line.startswith("# "):
            story.append(Paragraph(_inline(line[2:]), st["h1"]))
        elif line.startswith("## "):
            story.append(Paragraph(_inline(line[3:]), st["h2"]))
        elif line.startswith("### "):
            story.append(Paragraph(_inline(line[4:]), st["h3"]))
        elif line.startswith("|"):
            rows: list[list[str]] = []
            while i < len(lines) and lines[i].startswith("|"):
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                if not all(set(c) <= set("-: ") for c in cells):
                    rows.append(cells)
                i += 1
            story.append(_table(rows, st, width))
            story.append(Spacer(1, 6))
            continue
        elif re.match(r"^(\d+\.|-) ", line):
            items: list[str] = []
            numbered = line[0].isdigit()
            while i < len(lines) and re.match(r"^(\d+\.|-) ", lines[i]):
                items.append(re.sub(r"^(\d+\.|-) ", "", lines[i]))
                i += 1
            story.append(ListFlowable(
                [ListItem(Paragraph(_inline(it), st["body"]), leftIndent=12) for it in items],
                bulletType="1" if numbered else "bullet", bulletFontName="DejaVu", bulletFontSize=9,
                leftIndent=14,
            ))
            story.append(Spacer(1, 4))
            continue
        else:
            para = [line]
            while i + 1 < len(lines) and lines[i + 1].strip() and not re.match(r"^(#|\||```|- |\d+\. )", lines[i + 1]):
                i += 1
                para.append(lines[i])
            story.append(Paragraph(_inline(" ".join(para)), st["body"]))
            story.append(Spacer(1, 5))
        i += 1
    return story


def build_pdf(target: Path) -> None:
    _register_fonts()
    doc = SimpleDocTemplate(
        str(target), pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm, bottomMargin=16 * mm,
        title="BoxBox Academy – instrukcja nagrywania telemetrii", author="BoxBox Academy",
    )
    width = A4[0] - doc.leftMargin - doc.rightMargin
    doc.build(markdown_to_story(SOURCE.read_text(encoding="utf-8"), width))


def build_zip(pdf: Path, target: Path) -> None:
    package_dir = ROOT / "tools" / "package"
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(pdf, pdf.name)
        for extra in package_dir.iterdir():
            z.write(extra, extra.name)
        for path in sorted((ROOT / "boxbox").rglob("*.py")):
            z.write(path, path.relative_to(ROOT).as_posix())
        z.writestr("recordings/.gitkeep", "")


def main() -> None:
    DIST.mkdir(exist_ok=True)
    pdf = DIST / PDF_NAME
    build_pdf(pdf)
    build_zip(pdf, DIST / ZIP_NAME)
    print(f"PDF: {pdf}\nZIP: {DIST / ZIP_NAME}")


if __name__ == "__main__":
    main()
