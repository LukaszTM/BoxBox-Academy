"""Atlas obrysów torów (boxbox/tracks/atlas/<track_id>.json): mapa działa, zanim recorder nagra realny kształt.

Obrys to uproszczona polilinia z projektu f1-circuits (MIT), w lokalnych współrzędnych 0..1000 (y w dół,
północ u góry). Sprawdzone na nagraniach z Monzy i Bahrajnu: po przeskalowaniu i przesunięciu obrys leży
na śladzie auta z gry z błędem średnim 2-4 m, bez obracania. Dlatego dopasowanie to tylko skala i przesunięcie.

Atlas nie zna linii mety gry. `fit()` z kilkuset metrów pozycji auta (Motion + dystans okrążenia) wyznacza
skalę, przesunięcie, frakcję obrysu w miejscu mety i kierunek jazdy; od tej chwili dystans okrążenia
przekłada się na punkt obrysu (`position_at`). Realny kształt z recordera (shape.py) ma pierwszeństwo.
"""
import json
import math
from dataclasses import dataclass, field
from pathlib import Path

from boxbox.tracks.model import Track
from boxbox.tracks.shape import ShapeCorner, ShapePoint, TrackShape

ATLAS_DIR = Path(__file__).parent / "atlas"
FIT_DIR = Path("data") / "atlas_fit"
MIN_FIT_M = 300.0  # tyle metrów jazdy wystarcza, żeby dopasować obrys do gry
_DENSE_STEP = 2.0


@dataclass(frozen=True)
class Atlas:
    track_id: int
    name: str
    length_m: float
    points: tuple[tuple[float, float], ...]  # polilinia zamknięta, 0..1000

    @property
    def perimeter(self) -> float:
        return sum(_dist(self.points[i], self.points[(i + 1) % len(self.points)]) for i in range(len(self.points)))

    def dense(self, step: float = _DENSE_STEP) -> tuple[list[tuple[float, float]], list[float]]:
        """Punkty co `step` jednostek i frakcja obwodu każdego z nich (0..1)."""
        per = self.perimeter
        out: list[tuple[float, float]] = []
        fr: list[float] = []
        acc = 0.0
        n_pts = len(self.points)
        for i in range(n_pts):
            a, b = self.points[i], self.points[(i + 1) % n_pts]
            seg = _dist(a, b)
            n = max(1, int(seg / step))
            for k in range(n):
                t = k / n
                out.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))
                fr.append((acc + seg * t) / per)
            acc += seg
        return out, fr

    def at_fraction(self, fraction: float) -> tuple[float, float]:
        """Punkt obrysu dla frakcji obwodu (0..1, zawija)."""
        per = self.perimeter
        target = (fraction % 1.0) * per
        acc = 0.0
        n_pts = len(self.points)
        for i in range(n_pts):
            a, b = self.points[i], self.points[(i + 1) % n_pts]
            seg = _dist(a, b)
            if acc + seg >= target and seg > 0:
                t = (target - acc) / seg
                return a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t
            acc += seg
        return self.points[0]


@dataclass
class AtlasFit:
    """Przekształcenie atlas -> świat gry: game = scale * atlas + (tx, tz); meta przy `start_fraction`."""
    track_id: int
    scale: float
    tx: float
    tz: float
    start_fraction: float
    forward: bool  # True = kolejność punktów obrysu zgodna z kierunkiem jazdy
    error_m: float = 0.0
    samples: int = 0

    def to_game(self, x: float, y: float) -> tuple[float, float]:
        return self.scale * x + self.tx, self.scale * y + self.tz

    def to_atlas(self, x: float, z: float) -> tuple[float, float]:
        return (x - self.tx) / self.scale, (z - self.tz) / self.scale

    def fraction_at(self, distance_m: float, length_m: float) -> float:
        f = distance_m / length_m if length_m > 0 else 0.0
        return (self.start_fraction + f) % 1.0 if self.forward else (self.start_fraction - f) % 1.0

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.__dict__, ensure_ascii=False, indent=1), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> "AtlasFit":
        doc = json.loads(path.read_text(encoding="utf-8"))
        return cls(**{k: doc[k] for k in cls.__dataclass_fields__ if k in doc})


def _dist(a: tuple[float, float], b: tuple[float, float]) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def atlas_path(track_id: int, atlas_dir: Path = ATLAS_DIR) -> Path:
    return atlas_dir / f"{track_id}.json"


def fit_path(track_id: int, fit_dir: Path = FIT_DIR) -> Path:
    return fit_dir / f"{track_id}.json"


def load_atlas(track_id: int, atlas_dir: Path = ATLAS_DIR) -> Atlas | None:
    path = atlas_path(track_id, atlas_dir)
    if not path.exists():
        return None
    doc = json.loads(path.read_text(encoding="utf-8"))
    return Atlas(int(doc["track_id"]), doc["name"], float(doc["length_m"]), tuple((float(x), float(y)) for x, y in doc["points"]))


def _subsample(pts: list[tuple[float, float, float]], n: int) -> list[tuple[float, float, float]]:
    if len(pts) <= n:
        return pts
    step = len(pts) / n
    return [pts[int(i * step)] for i in range(n)]


class _Dense:
    """Gęsta polilinia atlasu z szybkim odczytem punktu dla frakcji (bisekcja po frakcjach)."""

    def __init__(self, atlas: Atlas) -> None:
        self.pts, self.fr = atlas.dense()
        self.n = len(self.pts)

    def at(self, fraction: float) -> tuple[float, float]:
        f = fraction % 1.0
        lo, hi = 0, self.n
        while lo < hi:  # bisect_right
            mid = (lo + hi) // 2
            if self.fr[mid] <= f:
                lo = mid + 1
            else:
                hi = mid
        return self.pts[(lo - 1) % self.n]


def _similarity(ax: list[float], ay: list[float], gx: list[float], gz: list[float], scale: float | None) -> tuple[float, float, float]:
    """Skala (gdy None: z najmniejszych kwadratów) i przesunięcie: game = scale * atlas + t."""
    ma, mb, mgx, mgz = _mean(ax), _mean(ay), _mean(gx), _mean(gz)
    if scale is None:
        num = sum((ax[k] - ma) * (gx[k] - mgx) + (ay[k] - mb) * (gz[k] - mgz) for k in range(len(ax)))
        den = sum((ax[k] - ma) ** 2 + (ay[k] - mb) ** 2 for k in range(len(ax)))
        scale = num / den if den > 0 else 0.0
    return scale, mgx - scale * ma, mgz - scale * mb


def _residual(dense: _Dense, pts: list[tuple[float, float, float]], length_m: float, s0: float, forward: bool,
              scale: float | None) -> tuple[float, float, float, float]:
    """Dopasowanie dla danej mety i kierunku: (błąd średni m, skala, tx, tz)."""
    ax, ay = [], []
    for d, _, _ in pts:
        f = d / length_m
        x, y = dense.at(s0 + f if forward else s0 - f)
        ax.append(x)
        ay.append(y)
    gx = [x for _, x, _ in pts]
    gz = [z for _, _, z in pts]
    sc, tx, tz = _similarity(ax, ay, gx, gz, scale)
    err = _mean([math.hypot(sc * ax[k] + tx - gx[k], sc * ay[k] + tz - gz[k]) for k in range(len(pts))])
    return err, sc, tx, tz


MAX_FIT_ERROR_M = 25.0
AMBIGUITY_FRACTION = 0.03  # gdy równie dobre dopasowania rozciągają się na >3% obwodu (sama prosta), nie zgadujemy


def fit(atlas: Atlas, samples: list[tuple[float, float, float]], length_m: float) -> AtlasFit | None:
    """`samples` = (dystans okrążenia, x, z) z gry, dowolna liczba okrążeń. None, gdy za mało jazdy albo dopasowanie niejednoznaczne.

    Dystans okrążenia to długość łuku, więc szukamy tylko frakcji obrysu przy mecie i kierunku jazdy
    (skala startowa = długość toru / obwód obrysu), a potem doprecyzowujemy skalę i przesunięcie.
    """
    pts = sorted((d, x, z) for d, x, z in samples if d >= 0)
    if len(pts) < 20:
        return None
    if pts[-1][0] - pts[0][0] < MIN_FIT_M:
        return None
    pts = _subsample(pts, 600)
    dense = _Dense(atlas)
    scale0 = length_m / atlas.perimeter
    coarse: list[tuple[float, float, bool]] = []
    steps = 400
    for forward in (True, False):
        for i in range(steps):
            s0 = i / steps
            err = _residual(dense, pts, length_m, s0, forward, scale0)[0]
            coarse.append((err, s0, forward))
    coarse.sort()
    best_err, best_s0, forward = coarse[0]
    close = [s0 for err, s0, fw in coarse if fw == forward and err <= best_err * 1.5 + 2.0]
    spread = max(((s - best_s0 + 0.5) % 1.0) - 0.5 for s in close) - min(((s - best_s0 + 0.5) % 1.0) - 0.5 for s in close)
    if spread > AMBIGUITY_FRACTION:
        return None
    # doprecyzowanie mety, potem skali i przesunięcia
    for fine in (1 / steps / 10, 1 / steps / 100):
        cands = [(best_s0 + k * fine) % 1.0 for k in range(-10, 11)]
        best_err, best_s0 = min((_residual(dense, pts, length_m, s, forward, scale0)[0], s) for s in cands)
    err, scale, tx, tz = _residual(dense, pts, length_m, best_s0, forward, None)
    if err > MAX_FIT_ERROR_M or scale <= 0:
        return None
    return AtlasFit(atlas.track_id, scale, tx, tz, best_s0, forward, round(err, 1), len(samples))


def to_shape(atlas: Atlas, fit_: AtlasFit, name: str, length_m: float, track: Track | None = None, step_m: float = 10.0) -> TrackShape:
    """Kształt jak z recordera (punkty co `step_m` w świecie gry), żeby mapa i nakładka miały jeden format."""
    out: list[ShapePoint] = []
    d = 0.0
    while d < length_m:
        x, y = atlas.at_fraction(fit_.fraction_at(d, length_m))
        gx, gz = fit_.to_game(x, y)
        out.append(ShapePoint(d, gx, gz))
        d += step_m
    shape = TrackShape(atlas.track_id, name, length_m, out, step_m=step_m)
    if track is not None:
        for c in track.corners:
            x, z = shape.position_at(c.apex_m)
            shape.corners.append(ShapeCorner(c.number, c.name or f"Z{c.number}", c.apex_m, x, z))
    return shape


def outline_shape(atlas: Atlas, step: float = 10.0) -> TrackShape:
    """Sam obrys bez dopasowania do gry: do mapy toru, zanim gracz przejedzie pierwsze metry."""
    dense, fractions = atlas.dense(step)
    pts = [ShapePoint(f * atlas.length_m, x, y) for (x, y), f in zip(dense, fractions)]
    return TrackShape(atlas.track_id, atlas.name, atlas.length_m, pts, step_m=step)


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


@dataclass
class ShapeSampler:
    """Zbiera (dystans, x, z) z pakietów w sesji; po sesji daje realny kształt (pełne okrążenie) albo dopasowanie atlasu."""
    laps: dict[int, list[tuple[float, float, float]]] = field(default_factory=dict)
    _last_key: tuple[int, float] = (-1, -1.0)

    def feed(self, state) -> None:  # TelemetryState; bez importu, żeby nie ciągnąć telemetrii do modułu torów
        m, lap = state.motion, state.lap
        if m is None or lap is None or m.header.frame_identifier != lap.header.frame_identifier:
            return
        p = lap.player
        key = (m.header.frame_identifier, p.lap_distance)
        if key == self._last_key:  # ten sam pakiet policzony dwa razy (Motion i Lap Data tej samej klatki)
            return
        self._last_key = key
        if p.lap_distance >= 0 and not p.pit_status:
            self.laps.setdefault(p.current_lap_num, []).append((p.lap_distance, m.player.x, m.player.z))

    def complete_lap(self, length_m: float, coverage: float = 0.95) -> list[tuple[float, float, float]] | None:
        best = None
        for pts in self.laps.values():
            if len(pts) < 200:
                continue
            ds = [d for d, _, _ in pts]
            if (max(ds) - min(ds)) >= coverage * length_m and (best is None or len(pts) > len(best)):
                best = pts
        return best

    def all_samples(self) -> list[tuple[float, float, float]]:
        return [s for pts in self.laps.values() for s in pts]
