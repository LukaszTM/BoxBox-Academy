"""Raport sesji jako jedna strona HTML (do PDF przez Qt `printToPdf`, bez okna drukowania i bez nowych zależności).

Układ z makiety v4, rozdział „Raport PDF sesji”: nagłówek, radar sześciu umiejętności z poprzednim oknem,
sześć linii „wymiar: wynik, trend, zdanie”, zadanie na następną sesję, „Dobrze / Do pracy”, tabela
okrążeń i tabela zakrętów referencji. Czysta funkcja: dane wchodzą jako słowniki z `DataBuilder`.
"""
import html
import math
from typing import Any

DIMENSIONS = (
    ("braking", "Hamowanie"), ("brake_control", "Praca hamulcem"), ("throttle", "Gaz na wyjściu"),
    ("consistency", "Powtarzalność"), ("pace", "Tempo"), ("independence", "Samodzielność"),
)
CSS = """
*{box-sizing:border-box}body{margin:0;background:#111925;color:#e3e9f0;font-family:'Inter','Segoe UI',Arial,sans-serif;font-size:12px}
.page{padding:28px 34px}.top{border-top:6px solid #ff3c42;margin:-28px -34px 22px;padding:16px 34px 0;display:flex;justify-content:space-between;align-items:baseline}
.brand{font-weight:800;letter-spacing:.14em;font-size:14px}.brand span{color:#19e6e6}.meta{color:#8fa0b3;font-size:11px;letter-spacing:.08em;text-transform:uppercase}
h1{font-size:30px;margin:0 0 4px;letter-spacing:-.03em}.sub{color:#b3c0ce;margin:0 0 20px;font-size:13px}
.grid{display:grid;grid-template-columns:38% 1fr;gap:18px}.panel{background:#182334;border:1px solid #243247;border-radius:14px;padding:18px 20px}
h2{font-size:15px;margin:0 0 4px;letter-spacing:.04em}.panel .sub{font-size:11px;margin-bottom:10px}
svg.radar{width:100%;height:auto;display:block}.legend{display:flex;gap:16px;color:#afbdcc;font-size:11px;margin-top:6px}
.legend i{display:inline-block;width:22px;height:2px;background:#19e6e6;vertical-align:middle;margin-right:6px}.legend i.prev{background:none;border-top:2px dashed #8290a1}
.row{display:flex;justify-content:space-between;align-items:baseline;gap:12px;padding:9px 0;border-bottom:1px solid #2a3a50}.row:last-child{border-bottom:0}
.row .name{font-weight:700;font-size:14px}.row .hint{color:#a9b8c8;font-size:11px;margin-top:2px}.row .score{color:#19e6e6;font-weight:800;font-size:20px;white-space:nowrap}
.row .trend{font-size:12px;font-weight:800;margin-left:10px}.pos{color:#35d07f}.neg{color:#f0b429}.muted{color:#7f8fa3}
.task{margin-top:18px;background:#182334;border-left:3px solid #19e6e6;border-radius:12px;padding:14px 18px;display:flex;gap:18px;align-items:baseline}
.task b{color:#19e6e6;letter-spacing:.1em;font-size:11px;text-transform:uppercase;white-space:nowrap}.task span{font-size:14px;font-weight:700}
.two{display:grid;grid-template-columns:1fr 1fr;gap:18px;margin-top:18px}.two .panel b{font-size:11px;letter-spacing:.1em}.two .panel p{font-size:14px;font-weight:700;margin:8px 0 0}
table{width:100%;border-collapse:collapse;margin-top:10px;font-size:11px}th{text-align:left;color:#8fa0b3;font-weight:600;padding:6px 8px;border-bottom:1px solid #2a3a50}
td{padding:6px 8px;border-bottom:1px solid #1f2c3f}tr.best td{color:#19e6e6;font-weight:700}.foot{margin-top:18px;color:#7f8fa3;font-size:10px;display:flex;justify-content:space-between}
@page{size:A4;margin:0}
"""


def _esc(v: Any) -> str:
    return html.escape("" if v is None else str(v))


def _polygon(scores: list[float | None], cx: float, cy: float, r: float) -> str:
    pts = []
    for i, v in enumerate(scores):
        a = math.pi * (i / 3 - 0.5)
        d = r * max(0.0, min(100.0, v or 0)) / 100
        pts.append(f"{cx + math.cos(a) * d:.1f},{cy + math.sin(a) * d:.1f}")
    return " ".join(pts)


def radar_svg(scores: list[int | None], previous: list[int | None] | None, labels: list[str]) -> str:
    """Radar sześciu osi jak w oknie (ta sama geometria), do raportu."""
    cx = cy = 260.0
    r = 146.0
    rad = lambda i: math.pi * (i / 3 - 0.5)  # noqa: E731
    grids = "".join(f'<polygon points="{_polygon([v] * 6, cx, cy, r)}" fill="none" stroke="#627389" stroke-opacity=".35"/>' for v in (20, 40, 60, 80, 100))
    axes = "".join(f'<line x1="{cx}" y1="{cy}" x2="{cx + math.cos(rad(i)) * r:.1f}" y2="{cy + math.sin(rad(i)) * r:.1f}" stroke="#6f8195" stroke-opacity=".4"/>' for i in range(6))
    positions = [(260, 48), (422, 146), (431, 367), (260, 471), (83, 367), (87, 146)]
    texts = ""
    for i, (x, y) in enumerate(positions):
        shown = "—" if scores[i] is None else str(scores[i])
        texts += (f'<text x="{x}" y="{y}" text-anchor="middle" fill="#cbd6e1" font-size="13" font-weight="600">{_esc(labels[i])}'
                  f'<tspan x="{x}" dy="21" fill="#19e6e6" font-size="18" font-weight="800">{shown}</tspan></text>')
    current = f'<polygon points="{_polygon(scores, cx, cy, r)}" fill="rgba(25,230,230,.22)" stroke="#19e6e6" stroke-width="2.8" stroke-linejoin="round"/>' if all(v is not None for v in scores) else ""
    prev = f'<polygon points="{_polygon(previous, cx, cy, r)}" fill="none" stroke="#91a0b5" stroke-width="2" stroke-dasharray="5 6"/>' if previous and all(v is not None for v in previous) else ""
    dots = "".join(
        f'<circle cx="{cx + math.cos(rad(i)) * r * ((v or 0) / 100):.1f}" cy="{cy + math.sin(rad(i)) * r * ((v or 0) / 100):.1f}" r="4" fill="{"#778596" if v is None else "#19e6e6"}" stroke="#192637" stroke-width="2"/>'
        for i, v in enumerate(scores)
    )
    return f'<svg class="radar" viewBox="0 0 520 520" xmlns="http://www.w3.org/2000/svg">{grids}{axes}{prev}{current}{dots}{texts}</svg>'


def _cap(text: str) -> str:
    return text[:1].upper() + text[1:] + ("" if text.endswith(".") else ".") if text else ""


def session_report_html(summary: dict, profile: dict | None, nick: str = "", game: str = "F1 25") -> str:
    """Strona raportu. `summary` jak `DataBuilder.summary`, `profile` jak `SkillProfile.to_dict()` (+`ref`) albo None."""
    skills = {s["key"]: s for s in (profile or {}).get("skills", [])}
    scores = [skills.get(k, {}).get("score") for k, _ in DIMENSIONS]
    trends = [skills.get(k, {}).get("trend") for k, _ in DIMENSIONS]
    previous = [None if (s is None or t is None) else max(0, min(100, s - t)) for s, t in zip(scores, trends)]
    have_profile = profile is not None and any(v is not None for v in scores)
    rows = ""
    for (key, name), score, trend in zip(DIMENSIONS, scores, trends):
        s = skills.get(key, {})
        tr = "" if trend is None else f'<span class="trend {"pos" if trend >= 0 else "neg"}">{"▲ +" if trend >= 0 else "▼ −"}{abs(trend)}</span>'
        hint = _cap(s.get("hint", "")) if score is not None else "Za mało okrążeń, żeby ocenić."
        rows += (f'<div class="row"><div><div class="name">{name}</div><div class="hint">{_esc(hint)}</div></div>'
                 f'<div><span class="score">{"—" if score is None else score}</span>{tr}</div></div>')
    weakest = min((skills[k] for k, _ in DIMENSIONS if skills.get(k, {}).get("score") is not None), key=lambda s: (s["score"], s.get("trend") or 0), default=None)
    task = _cap(weakest["hint"]) if weakest and weakest.get("hint") else (summary.get("toWork") or "Powtórz swoje najlepsze okrążenie.")
    lap_rows = "".join(
        f'<tr class="{"best" if r.get("delta") in ("+0.000", "0.000") else ""}"><td>{r["number"]}</td><td>{_esc(r["time"])}</td><td>{_esc(r.get("delta", ""))}</td>'
        f'<td>{"tak" if r.get("valid") else "nie"}</td><td>{r.get("notes", 0)}</td></tr>'
        for r in summary.get("lapRows", [])
    )
    corner_rows = "".join("<tr>" + "".join(f"<td>{_esc(c)}</td>" for c in row) + "</tr>" for row in summary.get("cornerRows", []))
    lap_count = summary.get("laps", 0)
    sub = " · ".join(x for x in (summary.get("track", ""), summary.get("date", ""), f"{lap_count} okrążeń", f"najlepsze {summary['best']}" if summary.get("best") else "", nick) if x)
    note = "" if have_profile else '<p class="sub muted">Profil powstaje z minimum 5 ważnych okrążeń na torze. Po kolejnych sesjach radar się wypełni.</p>'
    ref = (profile or {}).get("ref") or "twoje najlepsze okrążenie"
    window = (profile or {}).get("lapsUsed", 0)
    return f"""<!doctype html><html lang="pl"><head><meta charset="utf-8"><title>Raport sesji</title><style>{CSS}</style></head><body><div class="page">
<div class="top"><div class="brand">BOXBOX <span>/ ACADEMY</span></div><div class="meta">{_esc(game)} · raport sesji</div></div>
<h1>Profil umiejętności</h1><p class="sub">{_esc(sub)}</p>
<div class="grid"><div class="panel"><h2>MAPA PRACY</h2><p class="sub">Referencja: {_esc(ref)}{f" · {window} ostatnich ważnych okrążeń" if window else ""}</p>{radar_svg(scores, previous, [n for _, n in DIMENSIONS])}
<div class="legend"><span><i></i> Obecne okno</span>{'<span><i class="prev"></i> Poprzednie 10</span>' if any(v is not None for v in previous) else ''}</div>{note}</div>
<div class="panel"><h2>SZEŚĆ UMIEJĘTNOŚCI</h2>{rows}</div></div>
<div class="task"><b>Zadanie na następną sesję</b><span>{_esc(task)}</span></div>
<div class="two"><div class="panel"><b class="pos">✓ DOBRZE</b><p>{_esc(summary.get("good") or "Sesja zapisana")}</p></div><div class="panel"><b class="neg">◎ DO PRACY</b><p>{_esc(summary.get("toWork") or "Nic pilnego")}</p></div></div>
{f'<div class="panel" style="margin-top:18px"><h2>OKRĄŻENIA</h2><table><thead><tr><th>Nr</th><th>Czas</th><th>Δ do najlepszego</th><th>Ważne</th><th>Uwagi</th></tr></thead><tbody>{lap_rows}</tbody></table></div>' if lap_rows else ''}
{f'<div class="panel" style="margin-top:18px"><h2>ZAKRĘTY REFERENCJI</h2><table><thead><tr><th>Zakręt</th><th>Min. prędkość</th><th>Bieg</th><th>Hamowanie</th><th>Pełny gaz</th><th>Δ czasu vs poprzednie</th></tr></thead><tbody>{corner_rows}</tbody></table></div>' if corner_rows else ''}
<div class="foot"><span>BoxBox Academy · wszystkie dane zostają na tym komputerze</span><span>wysoki wynik = powtarzasz swoje najlepsze zachowania; to mapa pracy, nie ranking</span></div>
</div></body></html>"""
