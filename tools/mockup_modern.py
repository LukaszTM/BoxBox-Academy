"""Makieta nowoczesna: gradientowe tło, panele ze szkła, poświaty neonowe, miękkie cienie."""
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "brand" / "makieta-start-nowoczesna.png"
FONT_DIR = Path("/usr/share/fonts/truetype/dejavu")
W, H = 1600, 1000
RED = (232, 35, 42)
CYAN = (25, 230, 230)
GREEN = (53, 208, 127)
AMBER = (255, 196, 61)
WHITE = (244, 245, 247)
ASH = (155, 163, 173)


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT_DIR / ("DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf")), size)


def background() -> Image.Image:
    # gradient: granat -> grafit, z dwiema poświatami (czerwona i cyjanowa) i delikatnymi liniami toru
    base = Image.new("RGB", (W, H))
    px = base.load()
    for y in range(H):
        t = y / H
        for x in range(W):
            u = x / W
            r = int(10 + 12 * (1 - t) + 6 * u)
            g = int(12 + 16 * (1 - t))
            b = int(22 + 30 * (1 - t) - 8 * u)
            px[x, y] = (r, g, b)
    glow = Image.new("RGB", (W, H), (0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.ellipse((-200, -300, 700, 500), fill=(90, 10, 20))
    gd.ellipse((1100, 600, 2000, 1400), fill=(5, 70, 80))
    glow = glow.filter(ImageFilter.GaussianBlur(220))
    base = Image.blend(base, Image.eval(glow, lambda v: v), 0.0)
    base = Image.fromarray(__import__("numpy").clip(__import__("numpy").asarray(base, dtype=int) + __import__("numpy").asarray(glow, dtype=int), 0, 255).astype("uint8"))
    # linie "toru" w tle
    lines = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ld = ImageDraw.Draw(lines)
    pts = [(x, int(520 + 260 * math.sin(x / 260) * math.cos(x / 700))) for x in range(-50, W + 50, 6)]
    ld.line(pts, fill=(255, 255, 255, 14), width=90)
    ld.line([(x, y - 110) for x, y in pts], fill=(255, 255, 255, 9), width=60)
    base = Image.alpha_composite(base.convert("RGBA"), lines)
    return base


def glass(im: Image.Image, box: tuple[int, int, int, int], radius: int = 22, alpha: int = 46, border: int = 36, shadow: int = 90) -> None:
    x0, y0, x1, y1 = box
    # cień
    sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle((x0 + 6, y0 + 14, x1 + 6, y1 + 14), radius, fill=(0, 0, 0, shadow))
    sh = sh.filter(ImageFilter.GaussianBlur(18))
    im.alpha_composite(sh)
    # rozmyte tło pod szkłem
    region = im.crop(box).filter(ImageFilter.GaussianBlur(14))
    mask = Image.new("L", region.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, region.size[0] - 1, region.size[1] - 1), radius, fill=255)
    im.paste(region, (x0, y0), mask)
    panel = Image.new("RGBA", im.size, (0, 0, 0, 0))
    pd = ImageDraw.Draw(panel)
    pd.rounded_rectangle(box, radius, fill=(255, 255, 255, alpha), outline=(255, 255, 255, border), width=1)
    # połysk na górnej krawędzi
    pd.line((x0 + radius, y0 + 1, x1 - radius, y0 + 1), fill=(255, 255, 255, 70), width=1)
    im.alpha_composite(panel)


def glow_text(im: Image.Image, xy: tuple[int, int], text: str, f: ImageFont.FreeTypeFont, color: tuple[int, int, int], blur: int = 16, strength: int = 160) -> None:
    layer = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ImageDraw.Draw(layer).text(xy, text, font=f, fill=color + (strength,))
    im.alpha_composite(layer.filter(ImageFilter.GaussianBlur(blur)))
    ImageDraw.Draw(im).text(xy, text, font=f, fill=color + (255,))


def glow_line(im: Image.Image, pts: list[tuple[float, float]], color: tuple[int, int, int], width: int = 3, blur: int = 10) -> None:
    layer = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ImageDraw.Draw(layer).line(pts, fill=color + (170,), width=width + 6)
    im.alpha_composite(layer.filter(ImageFilter.GaussianBlur(blur)))
    ImageDraw.Draw(im).line(pts, fill=color + (255,), width=width)


def button(im: Image.Image, box: tuple[int, int, int, int], text: str, f: ImageFont.FreeTypeFont) -> None:
    x0, y0, x1, y1 = box
    layer = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ImageDraw.Draw(layer).rounded_rectangle((x0 - 10, y0 - 6, x1 + 10, y1 + 16), 24, fill=RED + (150,))
    im.alpha_composite(layer.filter(ImageFilter.GaussianBlur(22)))
    grad = Image.new("RGBA", (x1 - x0, y1 - y0))
    gp = grad.load()
    for y in range(y1 - y0):
        t = y / (y1 - y0)
        c = (int(255 - 30 * t), int(60 - 25 * t), int(66 - 24 * t), 255)
        for x in range(x1 - x0):
            gp[x, y] = c
    mask = Image.new("L", grad.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, grad.size[0] - 1, grad.size[1] - 1), 18, fill=255)
    im.paste(grad, (x0, y0), mask)
    d = ImageDraw.Draw(im)
    tw = d.textlength(text, font=f)
    d.text((x0 + (x1 - x0 - tw) / 2, y0 + (y1 - y0) / 2 - f.size / 2 - 4), text, font=f, fill=(255, 255, 255))


def toggle(im: Image.Image, x: int, y: int, on: bool, text: str) -> None:
    d = ImageDraw.Draw(im)
    if on:
        layer = Image.new("RGBA", im.size, (0, 0, 0, 0))
        ImageDraw.Draw(layer).rounded_rectangle((x - 4, y - 4, x + 52, y + 30), 16, fill=GREEN + (120,))
        im.alpha_composite(layer.filter(ImageFilter.GaussianBlur(10)))
    d.rounded_rectangle((x, y, x + 48, y + 26), 13, fill=GREEN if on else (60, 66, 80))
    d.ellipse((x + 24 if on else x + 2, y + 2, x + 46 if on else x + 24, y + 24), fill=(255, 255, 255))
    d.text((x + 62, y + 2), text, font=font(17), fill=WHITE)


def main() -> None:
    im = background()
    d = ImageDraw.Draw(im)
    # nawigacja ze szkła
    glass(im, (24, 24, 270, H - 24), 26, alpha=28)
    logo = Image.open(ROOT / "assets" / "logo.png").convert("RGBA").resize((170, 170), Image.LANCZOS)
    gl = logo.filter(ImageFilter.GaussianBlur(14))
    im.alpha_composite(gl, (62, 44))
    im.alpha_composite(logo, (62, 44))
    items = ["Start", "Analiza", "Postęp", "Lekcje", "Karta kierowcy", "Ustawienia"]
    for i, name in enumerate(items):
        y = 262 + i * 62
        if i == 0:
            glass(im, (40, y - 12, 254, y + 42), 16, alpha=70, border=60, shadow=0)
            glow_line(im, [(44, y - 2), (44, y + 32)], RED, 4, 8)
        d.ellipse((66, y + 4, 88, y + 26), outline=WHITE if i == 0 else ASH, width=2)
        d.text((104, y + 2), name, font=font(19, i == 0), fill=WHITE if i == 0 else ASH)
    d.text((66, H - 70), "Pomoc", font=font(16), fill=ASH)
    d.text((66, H - 46), "0.6.0 beta", font=font(13), fill=ASH)
    # nagłówek
    d.text((310, 40), "Start", font=font(40, True), fill=WHITE)
    d.text((310, 96), "Trener na radiu: włącz telemetrię w grze, wyjedź na tor i naciśnij Jedź.", font=font(18), fill=ASH)
    glass(im, (1120, 44, 1576, 96), 26, alpha=40)
    glow_text(im, (1146, 58), "●", font(22), GREEN, 10, 200)
    d.text((1180, 58), "Gra połączona · Monza · 60 pakietów/s", font=font(18), fill=WHITE)
    # karta akcji
    glass(im, (310, 140, 1000, 356), 24)
    d.text((344, 170), "Tryb nauki", font=font(24, True), fill=WHITE)
    d.text((344, 212), "Nazwa sesji", font=font(14), fill=ASH)
    glass(im, (344, 236, 640, 284), 14, alpha=22, border=30, shadow=0)
    d.text((362, 250), "monza, środa", font=font(18), fill=WHITE)
    toggle(im, 344, 306, True, "Nagrywaj sesję")
    toggle(im, 560, 306, True, "Nakładka na grze")
    toggle(im, 800, 306, False, "Tryb cicho")
    button(im, (760, 170, 960, 254), "JEDŹ", font(36, True))
    # plakietka
    glass(im, (1024, 140, 1576, 500), 24, alpha=52, border=50)
    d.text((1056, 168), "LICENCJA KIEROWCY", font=font(13), fill=ASH)
    glow_text(im, (1470, 158), "L2", font(40, True), CYAN, 14, 170)
    d.ellipse((1056, 206, 1156, 306), fill=(48, 54, 68), outline=(255, 255, 255, 60), width=2)
    d.ellipse((1086, 226, 1126, 266), fill=(80, 88, 104))
    d.pieslice((1070, 262, 1142, 334), 180, 360, fill=(80, 88, 104))
    d.text((1180, 212), "KIEROWCA", font=font(32, True), fill=WHITE)
    d.text((1180, 256), "ID DEMO-0000-0000", font=font(14), fill=CYAN)
    for i, (k, v) in enumerate([("Krok asyst", "2 · TC średnia"), ("Tory", "3 · 1 opanowany"), ("Okrążenia", "148"), ("Seria", "2 / 3 czystych")]):
        x = 1056 + (i % 2) * 260
        y = 338 + (i // 2) * 52
        d.text((x, y), k, font=font(13), fill=ASH)
        d.text((x, y + 20), v, font=font(17, True), fill=WHITE)
    d.rounded_rectangle((1056, 452, 1544, 466), 7, fill=(255, 255, 255, 30))
    glow_line(im, [(1063, 459), (1063 + 0.66 * 481, 459)], GREEN, 10, 8)
    d.text((1056, 474), "do następnego kroku: 1 czyste okrążenie", font=font(13), fill=ASH)
    # panel na żywo
    glass(im, (310, 384, 1000, 976), 24)
    d.text((344, 412), "OKRĄŻENIE 4", font=font(26, True), fill=WHITE)
    glow_text(im, (344, 456), "T8-T10", font(60, True), CYAN, 22, 150)
    d.text((596, 486), "za 120 m", font=font(28), fill=ASH)
    glow_text(im, (344, 548), "Na tym okrążeniu popraw: T1-T2, hamuj 20 m wcześniej", font(18, True), AMBER, 10, 90)
    d.line((344, 596, 966, 596), fill=(255, 255, 255, 40), width=1)
    msgs = [("0:42", "T1-T2: hamowanie za późno, o jakieś dwadzieścia metrów.", WHITE, 19, True),
            ("0:11", "Pierwsze okrążenie zapisane jako odniesienie.", ASH, 17, False),
            ("0:00", "Mechanik na radiu, słyszę cię.", ASH, 17, False)]
    y = 616
    for t, m, col, sz, b in msgs:
        d.text((344, y + 2), t, font=font(14), fill=ASH)
        d.text((404, y), m, font=font(sz, b), fill=col)
        y += 50
    glass(im, (344, 790, 966, 870), 16, alpha=30, border=36, shadow=0)
    d.text((366, 806), "Cel: 3 czyste okrążenia z rzędu", font=font(17, True), fill=WHITE)
    glow_text(im, (880, 804), "2 / 3", font(18, True), GREEN, 8, 120)
    d.rounded_rectangle((366, 842, 944, 854), 6, fill=(255, 255, 255, 30))
    glow_line(im, [(372, 848), (372 + 0.66 * 572, 848)], GREEN, 8, 8)
    d.text((344, 900), "Obciążenie 1,2 % · nagrywam monza-sroda.bin · 60 Hz", font=font(14), fill=ASH)
    d.text((344, 926), "Esc na nakładce albo Zakończ sesję w tym oknie", font=font(14), fill=ASH)
    # wykres
    glass(im, (1024, 528, 1576, 770), 24)
    d.text((1056, 552), "Prędkość · ostatnie okrążenie vs najlepsze", font=font(16), fill=ASH)
    pts_ref, pts_now = [], []
    for i in range(0, 470, 4):
        x = 1056 + i
        v = 0.5 + 0.45 * math.sin(i / 40.0) ** 2 * math.cos(i / 95.0)
        pts_ref.append((x, 730 - v * 140))
        pts_now.append((x, 730 - (v - 0.04 * math.sin(i / 23.0)) * 140))
    d.line(pts_ref, fill=ASH + (160,), width=2)
    glow_line(im, pts_now, CYAN, 3, 12)
    d.text((1056, 740), "0 m", font=font(12), fill=ASH)
    d.text((1500, 740), "5793 m", font=font(12), fill=ASH)
    # kafelki
    for i, (val, name, col) in enumerate([("1:24.279", "Najlepsze dziś", WHITE), ("-0.41 s", "Do referencji", GREEN), ("4", "Okrążenia", WHITE)]):
        x = 1024 + i * 188
        glass(im, (x, 798, x + 176, 896), 20)
        if col is GREEN:
            glow_text(im, (x + 20, 814), val, font(28, True), GREEN, 12, 140)
        else:
            d.text((x + 20, 814), val, font=font(28, True), fill=col)
        d.text((x + 20, 860), name, font=font(14), fill=ASH)
    glass(im, (1024, 922, 1576, 976), 20)
    d.text((1056, 938), "Dziś: lekcja Hamowanie w T1 · 5 okrążeń", font=font(16), fill=ASH)
    d.text((1420, 938), "Zacznij  →", font=font(16, True), fill=CYAN)
    im.convert("RGB").save(OUT, quality=95)
    print(OUT)


if __name__ == "__main__":
    main()
