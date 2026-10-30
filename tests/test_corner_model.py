"""Model zakrętu z wielu okrążeń: MAD, ważona średnia najlepszych prób, EMA między sesjami, baza."""
from boxbox.coach.corner_model import (
    MIN_SAMPLES, blend, build_models, describe, merge_reference, model_corner, models_from_db, robust_keep,
)
from boxbox.coach.corners import CornerMetrics, LapAnalysis, analyze_lap
from boxbox.coach.rules import evaluate_lap
from boxbox.storage.db import Database
from tests.conftest import RecordedSession


def cm(corner: int, brake: float, time_ms: int, exit_kmh: int = 200, vmin: int = 120, full: float | None = 700.0, gear: int = 3) -> CornerMetrics:
    return CornerMetrics(corner, vmin, 650.0, gear, 250, exit_kmh, time_ms, brake, full, brake + 60, 0.6, 0.9, brake - 40)


def test_robust_keep_rejects_outliers_only_with_spread() -> None:
    assert robust_keep([10, 11, 12, 13, 60]) == [True, True, True, True, False]
    assert robust_keep([10, 10, 10, 10, 10]) == [True] * 5  # MAD 0: nic nie odrzucamy
    assert robust_keep([1, 2]) == [True, True]


def test_model_corner_weights_best_attempts_and_rejects_spin() -> None:
    samples = [cm(1, 520, 6000), cm(1, 515, 5950, exit_kmh=205), cm(1, 530, 6100), cm(1, 500, 6050, exit_kmh=195),
               cm(1, 525, 6020), cm(1, 420, 9000, exit_kmh=120, vmin=60)]  # ostatnia: obrót, czas 9 s
    target = model_corner(1, samples)
    assert target is not None and target.samples == 5 and target.rejected == 1
    assert 512 <= target.metrics.brake_point_m <= 525  # średnia ważona lepszej połowy, blisko najszybszych prób
    assert 5950 <= target.metrics.time_ms <= 6020 and target.metrics.gear_at_apex == 3 and target.metrics.exit_speed_kmh >= 200
    assert target.spread_m > 0
    assert model_corner(1, samples[:3]) is None  # za mało prób
    assert model_corner(1, [cm(1, 500, 0)] * 6) is None  # bez czasu zakrętu


def test_blend_moves_target_by_alpha() -> None:
    a = model_corner(1, [cm(1, 500, 6000), cm(1, 500, 6000), cm(1, 500, 6000), cm(1, 500, 6000)])
    b = model_corner(1, [cm(1, 540, 5800), cm(1, 540, 5800), cm(1, 540, 5800), cm(1, 540, 5800)])
    assert a is not None and b is not None
    merged = blend(a, b, alpha=0.5)
    assert merged.metrics.brake_point_m == 520.0 and merged.metrics.time_ms == 5900 and merged.samples == 8
    assert blend(None, b) is b
    # wagi świeżości: te same próby, ale nowsze ważą więcej, więc cel idzie w ich stronę
    samples = [cm(1, 500, 6000), cm(1, 540, 6000)] * 4  # te same czasy: do lepszej połowy wchodzą po dwie próby z każdej sesji
    fresh_new = model_corner(1, samples, recency=[0.4, 1.0] * 4)
    fresh_old = model_corner(1, samples, recency=[1.0, 0.4] * 4)
    assert fresh_new is not None and fresh_old is not None and fresh_new.metrics.brake_point_m > fresh_old.metrics.brake_point_m


def test_build_models_and_merge_reference() -> None:
    s1 = [[cm(1, 500, 6000), cm(2, 1500, 4000)] for _ in range(2)]  # krótkie sesje: osobno za mało prób, razem dość
    s2 = [[cm(1, 540, 5800), cm(2, 1500, 4000)] for _ in range(2)] + [[cm(3, 3000, 5000)]]  # Z3: 1 próba, bez modelu
    models = build_models([s1, s2])
    assert set(models) == {1, 2} and 500 < models[1].metrics.brake_point_m < 540  # pula z wagą świeżości: cel między sesjami, bliżej nowszej
    assert models[1].metrics.brake_point_m > 520
    ref = LapAnalysis(6, 90_000, (cm(1, 480, 6300), cm(2, 1490, 4100), cm(3, 2990, 5100)))
    merged = merge_reference(ref, models)
    assert merged.lap_number == 6 and merged.corners[0].brake_point_m == models[1].metrics.brake_point_m
    assert merged.corners[2] is ref.corners[2]  # zakręt bez modelu: metryki najlepszego okrążenia
    assert describe(models, 3).startswith("model zakrętów (2 z 3 zakrętów, ") and describe({}, 3) == "najlepsze okrążenie"


def test_models_from_database_on_monza(tmp_path, monza: RecordedSession) -> None:
    db = Database(tmp_path / "m.sqlite")
    ref = analyze_lap(monza.lap(6), monza.track)
    laps = [l for l in monza.recorder.laps if l.is_complete(monza.track.length_m)]
    for n in range(3):  # trzy „sesje” z tych samych okrążeń: model ma dość prób, a EMA jest deterministyczna
        sid = db.save_session(monza.recorder.state.session, f"sesja {n}")
        for lap in laps:
            analysis = analyze_lap(lap, monza.track)
            lap_id = db.save_lap(sid, lap, analysis, monza.track.length_m, track_id=11, traction_control=1, abs_on=True)
            db.save_messages(lap_id, evaluate_lap(lap, analysis, ref, monza.track))
    models = models_from_db(db, 11, traction_control=1, abs_on=True)
    assert models, "Monza: czyste okrążenia powinny dać model dla części zakrętów"
    for corner, target in models.items():
        assert target.samples >= MIN_SAMPLES and target.metrics.time_ms > 0 and target.metrics.brake_point_m is not None
        own = next(c for c in ref.corners if c.corner == corner)
        assert abs(target.metrics.brake_point_m - (own.brake_point_m or 0)) < 150  # cel w okolicy realnego hamowania
    assert models_from_db(db, 11, traction_control=0, abs_on=False) == {}  # inny krok asyst: osobny model
    merged = merge_reference(ref, models)
    msgs = evaluate_lap(monza.lap(6), analyze_lap(monza.lap(6), monza.track), merged, monza.track)
    assert all(m.weight < 1.0 for m in msgs)  # najlepsze okrążenie względem modelu: bez poważnych uwag
    db.close()


def test_second_session_uses_corner_model_as_reference(tmp_path) -> None:
    """Dwie sesje na tym samym nagraniu i bazie: druga startuje z modelem zakrętów, nie z samym najlepszym okrążeniem."""
    from pathlib import Path

    from boxbox.session import CoachSession, SessionConfig

    from boxbox.coach.analyze import report_laps

    def run(n: int) -> CoachSession:
        cfg = SessionConfig(replay=Path("recordings/monza-trening_2026-10-26_153411.bin.xz"), speed=0, db=tmp_path / "s.sqlite", no_voice=True)
        s = CoachSession(cfg, on_message=lambda ids, text: None)
        s.start()
        s.loop()
        result = s.finish()
        report_laps(result.recorder, None, cfg.db, f"sesja {n}", "best", cfg.replay)  # zapis do bazy jak w aplikacji; źródło = osobna sesja
        return s

    first = run(1)
    assert first.reference_label == "pierwsze okrążenie sesji"
    second = run(2)
    assert second.reference_label == "najlepsze okrążenie"  # po jednej krótkiej sesji (3 czyste okrążenia) za mało prób na model
    third = run(3)
    assert third.reference_label.startswith("model zakrętów (") and "prób) + najlepsze okrążenie" in third.reference_label
    assert third.coach is not None and third.coach.corner_targets and third.coach.reference is not None
    for corner, target in third.coach.corner_targets.items():
        ref = next(c for c in third.coach.reference.corners if c.corner == corner)
        assert ref.brake_point_m == target.metrics.brake_point_m  # cel modelu w referencji, także po nowym najlepszym okrążeniu
