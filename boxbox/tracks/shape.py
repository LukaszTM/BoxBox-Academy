"""Realny kształt toru z pakietów Motion: pozycja auta gracza co `STEP_M` metrów okrążenia.

Plik `boxbox/tracks/shape/<track_id>.json`:
  {"track_id": 11, "name": "Monza", "length_m": 5793.0, "step_m": 10,
   "points": [[0.0, x, z], [10.0, x, z], ...],            # dystans okrążenia -> pozycja w świecie gry
   "corners": [{"number": 1, "name": "T1", "apex_m": 600.0, "x": ..., "z": ...}, ...]}
Do tego SVG z obrysem, metą i numerami zakrętów, żeby obejrzeć bez programu.
"""
import json
from dataclasses import dataclass, field
from pathlib import Path

from boxbox.tracks.model import Track

SHAPE_DIR = Path(__file__).parent / "shape"
STEP_M = 10.0
MIN_COVERAGE = 0.95  # okrążenie nadaje się na kształt, gdy próbki pokrywają 95% długości toru


@dataclass(frozen=True)
class ShapePoint:
    distance_m: float
    x: float
    z: float


@dataclass(frozen=True)
class ShapeCorner:
    number: int
    name: str
    apex_m: float
    x: float
    z: float


@dataclass
class TrackShape:
    track_id: int
    name: str
    length_m: float
    points: list[ShapePoint]
    corners: list[ShapeCorner] = field(default_factory=list)
    step_m: float = STEP_M

    def position_at(self, distance_m: float) -> tuple[float, float]:
        """Interpolacja liniowa pozycji dla dystansu okrążenia (zawija na mecie)."""
        if not self.points:
            raise ValueError("pusty kształt")
        d = distance_m % self.length_m
        pts = self.points
        for a, b in zip(pts, pts[1:] + [ShapePoint(self.length_m, pts[0].x, pts[0].z)]):
            if a.distance_m <= d <= b.distance_m:
                span = b.distance_m - a.distance_m
                t = (d - a.distance_m) / span if span > 0 else 0.0
                return a.x + (b.x - a.x) * t, a.z + (b.z - a.z) * t
        return pts[-1].x, pts[-1].z


def build_shape(
    samples: list[tuple[float, float, float]], track_id: int, name: str, length_m: float,
    track: Track | None = None, step_m: float = STEP_M,
) -> TrackShape:
    """`samples` = (dystans okrążenia, x, z) z jednego okrążenia, w kolejności jazdy."""
    pts = sorted((d, x, z) for d, x, z in samples if 0 <= d < length_m)
    if not pts or (pts[-1][0] - pts[0][0]) < MIN_COVERAGE * length_m:
        raise ValueError("za mało próbek na pełny kształt toru")
    out: list[ShapePoint] = []
    target = 0.0
    i = 0
    while target < length_m:
        while i + 1 < len(pts) and pts[i + 1][0] <= target:
            i += 1
        d0, x0, z0 = pts[i]
        if i + 1 < len(pts):
            d1, x1, z1 = pts[i + 1]
            t = (target - d0) / (d1 - d0) if d1 > d0 else 0.0
            t = min(1.0, max(0.0, t))
            out.append(ShapePoint(target, x0 + (x1 - x0) * t, z0 + (z1 - z0) * t))
        else:
            out.append(ShapePoint(target, x0, z0))
        target += step_m
    shape = TrackShape(track_id, name, length_m, out, step_m=step_m)
    if track is not None:
        for c in track.corners:
            x, z = shape.position_at(c.apex_m)
            shape.corners.append(ShapeCorner(c.number, c.name or f"Z{c.number}", c.apex_m, x, z))
    return shape


def save_shape(shape: TrackShape, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = {
        "track_id": shape.track_id, "name": shape.name, "length_m": shape.length_m, "step_m": shape.step_m,
        "points": [[round(p.distance_m, 1), round(p.x, 2), round(p.z, 2)] for p in shape.points],
        "corners": [{"number": c.number, "name": c.name, "apex_m": c.apex_m, "x": round(c.x, 2), "z": round(c.z, 2)}
                    for c in shape.corners],
    }
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")


def load_shape(path: Path) -> TrackShape:
    doc = json.loads(path.read_text(encoding="utf-8"))
    return TrackShape(
        doc["track_id"], doc["name"], float(doc["length_m"]),
        [ShapePoint(float(d), float(x), float(z)) for d, x, z in doc["points"]],
        [ShapeCorner(c["number"], c["name"], float(c["apex_m"]), float(c["x"]), float(c["z"])) for c in doc.get("corners", [])],
        float(doc.get("step_m", STEP_M)),
    )


def shape_path(track_id: int, shape_dir: Path = SHAPE_DIR) -> Path:
    return shape_dir / f"{track_id}.json"


def to_svg(shape: TrackShape, size: int = 900, margin: int = 50) -> str:
    """Obrys toru z metą i numerami zakrętów. Oś Z gry idzie w dół ekranu, jak na mapie w grze."""
    xs = [p.x for p in shape.points]
    zs = [p.z for p in shape.points]
    w, h = max(xs) - min(xs) or 1.0, max(zs) - min(zs) or 1.0
    scale = (size - 2 * margin) / max(w, h)

    def sx(x: float) -> float:
        return margin + (x - min(xs)) * scale

    def sz(z: float) -> float:
        return margin + (z - min(zs)) * scale

    poly = " ".join(f"{sx(p.x):.1f},{sz(p.z):.1f}" for p in shape.points)
    start = shape.points[0]
    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 {size} {size}">',
        f'<rect width="{size}" height="{size}" fill="#101010"/>',
        f'<text x="{margin}" y="{margin - 18}" fill="#f2f2f2" font-family="sans-serif" font-size="20">'
        f'{shape.name} ({shape.length_m:.0f} m, co {shape.step_m:.0f} m)</text>',
        f'<polygon points="{poly}" fill="none" stroke="#19e6e6" stroke-width="4" stroke-linejoin="round"/>',
        f'<circle cx="{sx(start.x):.1f}" cy="{sz(start.z):.1f}" r="7" fill="#ff2d2d"/>',
        f'<text x="{sx(start.x) + 10:.1f}" y="{sz(start.z) - 10:.1f}" fill="#ff2d2d" font-family="sans-serif" font-size="14">META</text>',
    ]
    for c in shape.corners:
        lines.append(f'<circle cx="{sx(c.x):.1f}" cy="{sz(c.z):.1f}" r="5" fill="#ffd34d"/>')
        lines.append(f'<text x="{sx(c.x) + 8:.1f}" y="{sz(c.z) + 5:.1f}" fill="#ffd34d" font-family="sans-serif" font-size="14">{c.name}</text>')
    lines.append("</svg>")
    return "\n".join(lines)
