"""Model zakrętu: cel z wielu czystych okrążeń zamiast jednego okrążenia referencyjnego.

Pomysł z pierwszego feedbacku (30.10): punkt hamowania zależy od paliwa, opon, asyst i stylu, więc
„hamujesz 8 m za późno” względem jednego okrążenia nie zawsze jest realną stratą. Dla każdego zakrętu
zbieramy próby z czystych okrążeń tego toru na tym samym kroku asyst, odrzucamy nietypowe przez MAD,
a cel wyznaczamy jako średnią ważoną najlepszych prób (waga rośnie, im krótszy czas zakrętu i wyższa
prędkość wyjścia). Między sesjami cel jest wygładzany wykładniczo (EMA), żeby jedna sesja go nie
przesuwała. Najlepsze okrążenie zostaje jako drugi punkt odniesienia tam, gdzie model nie ma dość prób.

Silnik bez UI: wejście to metryki zakrętów z bazy, wyjście to LapAnalysis z celami, które reguły trenera
czytają tak samo jak metryki okrążenia referencyjnego.
"""
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass, replace
from statistics import median
from typing import TYPE_CHECKING

from boxbox.coach.corners import CornerMetrics, LapAnalysis

if TYPE_CHECKING:
    from boxbox.storage.db import Database

MIN_SAMPLES = 4  # mniej prób: zostaje najlepsze okrążenie
MAD_K = 3.0  # próba dalej niż 3 odchylenia (MAD * 1,4826) od mediany jest nietypowa
TOP_SHARE = 0.5  # cel liczony z lepszej połowy prób (co najmniej 3)
TIME_SCALE_S = 0.5  # waga próby maleje o połowę przy +0,5 s do najlepszego czasu zakrętu
EXIT_SCALE_KMH = 10.0  # i o połowę przy -10 km/h prędkości wyjścia
EMA_ALPHA = 0.35  # udział nowej sesji w celu (0,35 = trzy sesje, żeby cel „dojechał” do nowego poziomu)
MAX_SESSIONS = 12  # starsze sesje nie wchodzą do modelu (zmienia się styl i asysty)


@dataclass(frozen=True)
class CornerTarget:
    corner: int
    metrics: CornerMetrics  # cel w polach metryk (reguły czytają go jak referencję)
    samples: int  # ile prób weszło do modelu (po odrzuceniu nietypowych)
    rejected: int
    spread_m: float  # MAD punktu hamowania w metrach (rozrzut, nie błąd)


def robust_keep(values: Sequence[float], k: float = MAD_K) -> list[bool]:
    """True dla wartości w zasięgu k odchyleń MAD od mediany; przy MAD 0 zostają wszystkie."""
    if len(values) < 3:
        return [True] * len(values)
    med = median(values)
    mad = median(abs(v - med) for v in values) * 1.4826
    if mad <= 1e-9:
        return [True] * len(values)
    return [abs(v - med) <= k * mad for v in values]


def _weighted(values: Sequence[float | None], weights: Sequence[float]) -> float | None:
    pairs = [(v, w) for v, w in zip(values, weights) if v is not None]
    if not pairs:
        return None
    total = sum(w for _, w in pairs)
    return sum(v * w for v, w in pairs) / total if total > 0 else None


def model_corner(
    corner: int, samples: Sequence[CornerMetrics], min_samples: int = MIN_SAMPLES, recency: Sequence[float] | None = None,
) -> CornerTarget | None:
    """Cel zakrętu z prób: MAD po czasie zakrętu i punkcie hamowania, potem ważona średnia najlepszych.

    `recency` to mnożnik wagi każdej próby (1,0 = najnowsza sesja, mniej dla starszych): wygładzanie wykładnicze
    po wieku sesji, żeby jedna stara albo jedna nowa sesja nie przesuwała celu.
    """
    rec = list(recency) if recency is not None else [1.0] * len(samples)
    pairs = [(s, r) for s, r in zip(samples, rec) if s.time_ms > 0 and s.min_speed_kmh > 0]
    if len(pairs) < min_samples:
        return None
    usable = [s for s, _ in pairs]
    keep = robust_keep([s.time_ms for s in usable])
    brake_values = [s.brake_point_m for s in usable if s.brake_point_m is not None]
    brake_keep = dict(zip([id(s) for s in usable if s.brake_point_m is not None], robust_keep(brake_values)))
    kept_pairs = [(s, r) for (s, r), k in zip(pairs, keep) if k and brake_keep.get(id(s), True)]
    rejected = len(usable) - len(kept_pairs)
    if len(kept_pairs) < min_samples:
        return None
    kept_pairs.sort(key=lambda p: p[0].time_ms)
    kept = [s for s, _ in kept_pairs]
    top_pairs = kept_pairs[: max(3, int(round(len(kept_pairs) * TOP_SHARE)))]
    top = [s for s, _ in top_pairs]
    best_time, best_exit = top[0].time_ms, max(s.exit_speed_kmh for s in top)
    weights = [
        r / (1.0 + (s.time_ms - best_time) / 1000 / TIME_SCALE_S) / (1.0 + max(0.0, best_exit - s.exit_speed_kmh) / EXIT_SCALE_KMH)
        for s, r in top_pairs
    ]
    gear = Counter(s.gear_at_apex for s in top if s.gear_at_apex > 0).most_common(1)
    metrics = CornerMetrics(
        corner=corner,
        min_speed_kmh=int(round(_weighted([s.min_speed_kmh for s in top], weights) or 0)),
        apex_m=_weighted([s.apex_m for s in top], weights) or top[0].apex_m,
        gear_at_apex=gear[0][0] if gear else 0,
        entry_speed_kmh=int(round(_weighted([s.entry_speed_kmh for s in top], weights) or 0)),
        exit_speed_kmh=int(round(_weighted([s.exit_speed_kmh for s in top], weights) or 0)),
        time_ms=int(round(_weighted([s.time_ms for s in top], weights) or 0)),
        brake_point_m=_weighted([s.brake_point_m for s in top], weights),
        full_throttle_m=_weighted([s.full_throttle_m for s in top], weights),
        brake_end_m=_weighted([s.brake_end_m for s in top], weights),
        brake_release_s=_weighted([s.brake_release_s for s in top], weights),
        max_brake=_weighted([s.max_brake for s in top], weights) or 0.0,
        lift_m=_weighted([s.lift_m for s in top], weights),
    )
    brakes = [s.brake_point_m for s in kept if s.brake_point_m is not None]
    spread = median(abs(b - median(brakes)) for b in brakes) * 1.4826 if len(brakes) >= 3 else 0.0
    return CornerTarget(corner, metrics, len(kept), rejected, round(spread, 1))


def _blend_value(prev: float | None, new: float | None, alpha: float) -> float | None:
    if prev is None:
        return new
    if new is None:
        return prev
    return prev + alpha * (new - prev)


def blend(previous: CornerTarget | None, current: CornerTarget, alpha: float = EMA_ALPHA) -> CornerTarget:
    """EMA między sesjami: cel z poprzednich sesji przesuwa się o `alpha` w stronę celu z nowej sesji."""
    if previous is None:
        return current
    p, c = previous.metrics, current.metrics
    merged = CornerMetrics(
        corner=current.corner,
        min_speed_kmh=int(round(_blend_value(p.min_speed_kmh, c.min_speed_kmh, alpha) or 0)),
        apex_m=_blend_value(p.apex_m, c.apex_m, alpha) or c.apex_m,
        gear_at_apex=c.gear_at_apex or p.gear_at_apex,
        entry_speed_kmh=int(round(_blend_value(p.entry_speed_kmh, c.entry_speed_kmh, alpha) or 0)),
        exit_speed_kmh=int(round(_blend_value(p.exit_speed_kmh, c.exit_speed_kmh, alpha) or 0)),
        time_ms=int(round(_blend_value(p.time_ms, c.time_ms, alpha) or 0)),
        brake_point_m=_blend_value(p.brake_point_m, c.brake_point_m, alpha),
        full_throttle_m=_blend_value(p.full_throttle_m, c.full_throttle_m, alpha),
        brake_end_m=_blend_value(p.brake_end_m, c.brake_end_m, alpha),
        brake_release_s=_blend_value(p.brake_release_s, c.brake_release_s, alpha),
        max_brake=_blend_value(p.max_brake, c.max_brake, alpha) or 0.0,
        lift_m=_blend_value(p.lift_m, c.lift_m, alpha),
    )
    return CornerTarget(current.corner, merged, previous.samples + current.samples, previous.rejected + current.rejected,
                        round(_blend_value(previous.spread_m, current.spread_m, alpha) or 0.0, 1))


def build_models(
    sessions: Sequence[Sequence[Sequence[CornerMetrics]]], min_samples: int = MIN_SAMPLES, alpha: float = EMA_ALPHA,
) -> dict[int, CornerTarget]:
    """Modele zakrętów z sesji w kolejności chronologicznej: `sessions[i]` = lista okrążeń, okrążenie = metryki zakrętów.

    Próby ze wszystkich sesji trafiają do jednej puli z wagą świeżości (1 - alpha)^wiek_sesji: najnowsza sesja
    waży 1, poprzednia 0,65, kolejna 0,42 itd. To wygładzanie wykładnicze, które działa także dla krótkich sesji
    (kilka czystych okrążeń), gdzie osobny cel na sesję nie miałby dość prób.
    """
    by_corner: dict[int, list[CornerMetrics]] = {}
    recency: dict[int, list[float]] = {}
    for age, laps in enumerate(reversed(sessions)):
        weight = (1.0 - alpha) ** age
        for lap in laps:
            for m in lap:
                by_corner.setdefault(m.corner, []).append(m)
                recency.setdefault(m.corner, []).append(weight)
    out: dict[int, CornerTarget] = {}
    for corner, samples in by_corner.items():
        target = model_corner(corner, samples, min_samples, recency[corner])
        if target is not None:
            out[corner] = target
    return out


def merge_reference(reference: LapAnalysis, models: dict[int, CornerTarget]) -> LapAnalysis:
    """Referencja dla reguł: cel z modelu tam, gdzie jest; metryki najlepszego okrążenia w pozostałych zakrętach."""
    corners = tuple(models[m.corner].metrics if m.corner in models else m for m in reference.corners)
    return replace(reference, corners=corners)


def describe(models: dict[int, CornerTarget], total_corners: int) -> str:
    """Zdanie do okna i dziennika: ile zakrętów ma model i z ilu prób."""
    if not models:
        return "najlepsze okrążenie"
    samples = sum(t.samples for t in models.values())
    return f"model zakrętów ({len(models)} z {total_corners} zakrętów, {samples} prób) + najlepsze okrążenie"


def models_from_db(db: "Database", track_id: int, traction_control: int | None, abs_on: bool | None,
                   max_sessions: int = MAX_SESSIONS, big_error_weight: float = 1.0) -> dict[int, CornerTarget]:
    """Czyste okrążenia toru na tym samym kroku asyst, pogrupowane po sesjach, w kolejności chronologicznej."""
    laps = [l for l in db.laps_for_track(track_id) if l.complete and l.valid and not l.pitted and l.lap_time_ms]
    if traction_control is not None:
        laps = [l for l in laps if l.traction_control is None or l.traction_control == traction_control]
    if abs_on is not None:
        laps = [l for l in laps if l.abs_on is None or l.abs_on == abs_on]
    by_session: dict[int, list[Sequence[CornerMetrics]]] = {}
    for lap in laps:
        if any(w >= big_error_weight for _, _, w in db.lap_messages(lap.id)):
            continue  # obrót, wypadnięcie: nie uczymy się z tego
        by_session.setdefault(lap.session_id, []).append(db.corner_metrics(lap.id))
    ordered = [by_session[s] for s in sorted(by_session)][-max_sessions:]
    return build_models(ordered)
