"""Materiały marki BoxBox Academy: paleta, znak wodny, makieta okna, stemplowanie grafik.

Użycie:
  python tools/brand_assets.py            -> assets/brand/paleta.png, znak-wodny*.png, makieta-start.png
  python tools/brand_assets.py stempluj obraz.png [wynik.png]   -> logo w prawym dolnym rogu (materiały do publikacji)
"""
import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
BRAND = ROOT / "assets" / "brand"
FONT_DIR = Path("/usr/share/fonts/truetype/dejavu")

PALETTE = [
    ("Carbon", "#0B0C0E", "tło okna"),
    ("Graphite", "#15171B", "panele, karty"),
    ("Steel", "#1F232A", "pola, kafelki, stan hover"),
    ("Line", "#2A2F37", "jedyna linia podziału (1 px)"),
    ("Chalk", "#F4F5F7", "tekst główny"),
    ("Ash", "#9BA3AD", "tekst drugorzędny, podpisy"),
    ("Signal Red", "#E8232A", "jedna akcja główna, błąd, logo"),
    ("Telemetry Cyan", "#19E6E6", "dane na żywo, wykres gracza, akcent logo"),
    ("Track Green", "#35D07F", "postęp, zaliczone, poprawa"),
    ("Pit Amber", "#FFC43D", "cel na okrążenie, ostrzeżenie"),
]


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT_DIR / ("DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf")), size)


def hex_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def palette_image(path: Path) -> None:
    w, h = 1400, 120 * len(PALETTE) + 40
    im = Image.new("RGB", (w, h), hex_rgb("#0B0C0E"))
    d = ImageDraw.Draw(im)
    for i, (name, hx, use) in enumerate(PALETTE):
        y = 20 + i * 120
        d.rounded_rectangle((20, y, 320, y + 100), 16, fill=hex_rgb(hx), outline=hex_rgb("#2A2F37"))
        d.text((350, y + 14), name, font=font(34, True), fill=hex_rgb("#F4F5F7"))
        d.text((350, y + 58), f"{hx}   {use}", font=font(24), fill=hex_rgb("#9BA3AD"))
    im.save(path)


def watermark(path_logo: Path, out: Path, opacity: float = 0.32, width: int = 600) -> None:
    im = Image.open(path_logo).convert("RGBA")
    im = im.resize((width, int(width * im.size[1] / im.size[0])), Image.LANCZOS)
    alpha = im.getchannel("A").point(lambda a: int(a * opacity))
    im.putalpha(alpha)
    im.save(out)


def stamp(src: Path, dst: Path, mark: Path | None = None, scale: float = 0.18, margin: int = 24, opacity: float = 0.85) -> None:
    """Logo w prawym dolnym rogu grafiki do publikacji (YouTube, Patreon, social)."""
    mark = mark or ROOT / "assets" / "logo.png"
    base = Image.open(src).convert("RGBA")
    logo = Image.open(mark).convert("RGBA")
    width = max(80, int(base.size[0] * scale))
    logo = logo.resize((width, int(width * logo.size[1] / logo.size[0])), Image.LANCZOS)
    logo.putalpha(logo.getchannel("A").point(lambda a: int(a * opacity)))
    base.alpha_composite(logo, (base.size[0] - logo.size[0] - margin, base.size[1] - logo.size[1] - margin))
    base.convert("RGB" if dst.suffix.lower() in (".jpg", ".jpeg") else "RGBA").save(dst)


def mockup(out: Path) -> None:
    """Makieta ekranu Start: docelowy wygląd okna (spokojny, dużo powietrza, jedna czerwona akcja)."""
    W, H = 1440, 900
    C = {k: hex_rgb(v) for k, v, _ in PALETTE}
    im = Image.new("RGB", (W, H), C["Carbon"])
    d = ImageDraw.Draw(im)
    # nawigacja
    d.rectangle((0, 0, 240, H), fill=C["Graphite"])
    logo = Image.open(ROOT / "assets" / "logo.png").convert("RGBA").resize((150, 150), Image.LANCZOS)
    im.paste(logo, (45, 28), logo)
    items = [("Start", True), ("Analiza", False), ("Postęp", False), ("Karta kierowcy", False), ("Ustawienia", False)]
    for i, (name, active) in enumerate(items):
        y = 220 + i * 56
        if active:
            d.rounded_rectangle((16, y - 8, 224, y + 40), 10, fill=C["Steel"])
            d.rectangle((16, y - 8, 20, y + 40), fill=C["Signal Red"])
        d.ellipse((34, y + 6, 54, y + 26), outline=C["Ash"] if not active else C["Chalk"], width=2)
        d.text((70, y + 2), name, font=font(20, not active), fill=C["Chalk"] if active else C["Ash"])
    d.text((32, H - 48), "0.6.0 beta", font=font(14), fill=C["Ash"])
    # nagłówek
    d.text((280, 36), "Start", font=font(34, True), fill=C["Chalk"])
    d.text((280, 84), "Trener na radiu: włącz telemetrię w grze, wyjedź na tor i naciśnij Jedź.", font=font(18), fill=C["Ash"])
    d.rounded_rectangle((1020, 40, 1400, 84), 22, fill=C["Steel"])
    d.ellipse((1038, 52, 1058, 72), fill=C["Track Green"])
    d.text((1070, 50), "Gra połączona · Monza · 60 pakietów/s", font=font(17), fill=C["Chalk"])
    # karta główna
    d.rounded_rectangle((280, 130, 1400, 330), 18, fill=C["Graphite"])
    d.text((312, 160), "Tryb nauki", font=font(22, True), fill=C["Chalk"])
    d.text((312, 196), "Nazwa sesji", font=font(15), fill=C["Ash"])
    d.rounded_rectangle((312, 220, 640, 262), 10, fill=C["Steel"])
    d.text((328, 230), "monza, środa", font=font(17), fill=C["Chalk"])
    for i, (txt, on) in enumerate([("Nagrywaj sesję", True), ("Nakładka na grze", True)]):
        x = 680 + i * 220
        d.rounded_rectangle((x, 222, x + 44, 246), 12, fill=C["Track Green"] if on else C["Steel"])
        d.ellipse((x + 22 if on else x + 2, 224, x + 42 if on else x + 22, 244), fill=C["Chalk"])
        d.text((x + 56, 224), txt, font=font(16), fill=C["Chalk"])
    d.rounded_rectangle((1150, 190, 1368, 268), 14, fill=C["Signal Red"])
    d.text((1208, 210), "JEDŹ", font=font(34, True), fill=(255, 255, 255))
    # panel na żywo
    d.rounded_rectangle((280, 356, 920, 820), 18, fill=C["Graphite"])
    d.text((312, 382), "OKRĄŻENIE 4", font=font(26, True), fill=C["Chalk"])
    d.text((312, 428), "T8-T10", font=font(44, True), fill=C["Telemetry Cyan"])
    d.text((512, 446), "za 120 m", font=font(26), fill=C["Ash"])
    d.text((312, 500), "Na tym okrążeniu popraw: T1-T2, hamuj 20 m wcześniej", font=font(17, True), fill=C["Pit Amber"])
    d.line((312, 540, 888, 540), fill=C["Line"], width=1)
    msgs = [("0:42", "T1-T2: hamowanie za późno, o jakieś dwadzieścia metrów.", C["Chalk"], 18),
            ("0:11", "Pierwsze okrążenie zapisane jako odniesienie. Teraz postaraj się je poprawić.", C["Ash"], 16),
            ("0:00", "Mechanik na radiu, słyszę cię.", C["Ash"], 16)]
    y = 560
    for t, m, col, sz in msgs:
        d.text((312, y), t, font=font(sz), fill=C["Ash"])
        d.text((372, y), m, font=font(sz, sz == 18), fill=col)
        y += 44
    d.rounded_rectangle((312, 720, 888, 790), 12, fill=C["Steel"])
    d.text((330, 734), "Cel: 3 czyste okrążenia z rzędu", font=font(16, True), fill=C["Chalk"])
    d.rounded_rectangle((330, 764, 870, 776), 6, fill=C["Line"])
    d.rounded_rectangle((330, 764, 690, 776), 6, fill=C["Track Green"])
    d.text((760, 736), "2 / 3", font=font(16), fill=C["Track Green"])
    # wykres
    d.rounded_rectangle((944, 356, 1400, 600), 18, fill=C["Graphite"])
    d.text((972, 380), "Prędkość · ostatnie okrążenie vs najlepsze", font=font(16), fill=C["Ash"])
    pts_ref, pts_now = [], []
    for i in range(0, 400, 4):
        x = 972 + i
        v = 0.5 + 0.45 * math.sin(i / 38.0) ** 2 * math.cos(i / 90.0)
        pts_ref.append((x, 560 - v * 140))
        pts_now.append((x, 560 - (v - 0.04 * math.sin(i / 23.0)) * 140))
    d.line(pts_ref, fill=C["Ash"], width=2)
    d.line(pts_now, fill=C["Telemetry Cyan"], width=3)
    d.text((972, 568), "0 m", font=font(12), fill=C["Ash"])
    d.text((1340, 568), "5793 m", font=font(12), fill=C["Ash"])
    # kafelki
    for i, (val, name, col) in enumerate([("1:24.279", "Najlepsze dziś", C["Chalk"]), ("-0.41 s", "Do referencji", C["Track Green"]), ("4", "Okrążenia", C["Chalk"])]):
        x = 944 + i * 156
        d.rounded_rectangle((x, 624, x + 144, 720), 14, fill=C["Graphite"])
        d.text((x + 16, 640), val, font=font(24, True), fill=col)
        d.text((x + 16, 684), name, font=font(14), fill=C["Ash"])
    d.rounded_rectangle((944, 744, 1400, 820), 14, fill=C["Graphite"])
    d.text((972, 760), "Obciążenie 1,2 % · nagrywam monza-sroda.bin · 60 Hz", font=font(15), fill=C["Ash"])
    d.text((972, 786), "Esc na nakładce albo Zakończ sesję w tym oknie", font=font(14), fill=C["Ash"])
    im.save(out)


def badge(out: Path, nick: str = "KIEROWCA", player_id: str = "DEMO-0000-0000", level: int = 2, tracks: int = 3, laps: int = 148) -> None:
    """Plakietka kierowcy jak prawo jazdy: na ekranie Start z boku, w karcie kierowcy w powiększeniu."""
    W, H = 640, 400
    C = {k: hex_rgb(v) for k, v, _ in PALETTE}
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, W - 1, H - 1), 28, fill=C["Graphite"], outline=C["Line"], width=2)
    d.rounded_rectangle((0, 0, W - 1, 70), 28, fill=C["Steel"])
    d.rectangle((0, 40, W - 1, 70), fill=C["Steel"])
    d.rectangle((0, 70, W - 1, 74), fill=C["Signal Red"])
    mark = Image.open(ROOT / "assets" / "mark.png").convert("RGBA")
    mark = mark.resize((78, int(78 * mark.size[1] / mark.size[0])), Image.LANCZOS)
    im.alpha_composite(mark, (24, 10))
    d.text((112, 18), "BOXBOX ACADEMY", font=font(20, True), fill=C["Chalk"])
    d.text((112, 44), "LICENCJA KIEROWCY", font=font(13), fill=C["Ash"])
    d.text((W - 150, 24), f"L{level}", font=font(34, True), fill=C["Telemetry Cyan"])
    # zdjęcie (koło)
    cx, cy, r = 110, 215, 80
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=C["Steel"], outline=C["Line"], width=2)
    d.ellipse((cx - 28, cy - 44, cx + 28, cy + 8), fill=C["Line"])
    d.pieslice((cx - 56, cy + 4, cx + 56, cy + 108), 180, 360, fill=C["Line"])
    d.text((220, 108), nick, font=font(36, True), fill=C["Chalk"])
    d.text((220, 156), "ID " + player_id, font=font(16), fill=C["Telemetry Cyan"])
    rows = [("Krok asyst", f"{level} · TC średnia"), ("Tory", f"{tracks} · 1 opanowany"), ("Okrążenia", str(laps)), ("Seria", "2 / 3 czystych")]
    y = 196
    for k, v in rows:
        d.text((220, y), k, font=font(14), fill=C["Ash"])
        d.text((400, y), v, font=font(16, True), fill=C["Chalk"])
        y += 34
    d.rounded_rectangle((24, 340, W - 24, 362), 11, fill=C["Line"])
    d.rounded_rectangle((24, 340, 24 + int((W - 48) * 0.66), 362), 11, fill=C["Track Green"])
    d.text((24, 368), "do następnego kroku: 1 czyste okrążenie", font=font(13), fill=C["Ash"])
    d.text((W - 150, 368), "od 10.2026", font=font(13), fill=C["Ash"])
    im.save(out)


def main(argv: list[str]) -> int:
    BRAND.mkdir(parents=True, exist_ok=True)
    if argv and argv[0] == "stempluj":
        src = Path(argv[1])
        dst = Path(argv[2]) if len(argv) > 2 else src.with_name(src.stem + "-boxbox" + src.suffix)
        stamp(src, dst)
        print(f"Ostemplowano: {dst}")
        return 0
    palette_image(BRAND / "paleta.png")
    watermark(ROOT / "assets" / "logo.png", BRAND / "znak-wodny.png")
    watermark(ROOT / "assets" / "mark.png", BRAND / "znak-wodny-znak.png", opacity=0.25, width=900)
    mockup(BRAND / "makieta-start.png")
    badge(BRAND / "plakietka-kierowcy.png")
    stamp(BRAND / "makieta-start.png", BRAND / "przyklad-stempla.png")
    print(f"Gotowe: {BRAND}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
