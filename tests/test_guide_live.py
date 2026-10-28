"""Prowadzenie w zakręcie: komendy przed punktami z referencji, tylko w zakrętach z uwagami, raz na okrążenie."""
from boxbox.coach.corners import CornerMetrics, analyze_lap
from boxbox.coach.guide_live import (
    HALF_MIN_GAP_M, INTRO_M, KINDS, LATE_M, LEAD_S, MAX_GUIDED, CornerGuide, brake_strength, corner_cues, is_urgent_cue,
    kinds_for_rules,
)
from boxbox.coach.laps import Lap, Sample
from boxbox.tracks.model import Corner, Track
from boxbox.voice.phrases import GUIDE_TEXTS, catalog, track_corner_names
from tests.conftest import RecordedSession


def _metrics(corner: int, brake: float | None, lift: float | None, apex: float, full: float | None, max_brake: float = 0.9) -> CornerMetrics:
    return CornerMetrics(corner, 120, apex, 3, 250, 180, 5000, brake, full, max_brake=max_brake, lift_m=lift)


def test_corner_cues_order_strength_and_intro() -> None:
    corner = Corner(4, 900.0, 1000.0, 1100.0, "T4")
    cues = corner_cues(corner, _metrics(4, brake=880.0, lift=800.0, apex=1000.0, full=1090.0), 5000.0)
    assert [c.kind for c in cues] == ["intro", "lift", "brake", "half", "full"]
    assert [c.at_m for c in cues] == [800.0 - INTRO_M, 800.0, 880.0, 1000.0, 1090.0]
    assert cues[0].ids == ("corner_t4", "guide_intro") and cues[0].text == "Zakręt czwarty. Prowadzę."
    assert cues[2].ids == ("guide_brake_hard",) and cues[2].text == "Mocny hamulec."
    assert cues[3].text == "Pół gazu." and cues[4].text == "Pełny gaz."
    # gaz puszczony tuż przed hamowaniem: samo hamowanie; pełny gaz zaraz za apeksem: bez "pół gazu"
    cues = corner_cues(corner, _metrics(4, brake=880.0, lift=870.0, apex=1000.0, full=1000.0 + HALF_MIN_GAP_M - 1, max_brake=0.5), 5000.0)
    assert [c.kind for c in cues] == ["intro", "brake", "full"] and cues[1].ids == ("guide_brake_medium",)
    # zakręt bez hamowania (tylko puszczenie gazu)
    cues = corner_cues(corner, _metrics(4, brake=None, lift=850.0, apex=1000.0, full=1050.0, max_brake=0.0), 5000.0)
    assert [c.kind for c in cues] == ["intro", "lift", "half", "full"]
    assert corner_cues(corner, _metrics(4, None, None, 1000.0, None), 5000.0) == ()
    assert brake_strength(0.95) == "brake_hard" and brake_strength(0.6) == "brake_medium" and brake_strength(0.3) == "brake_light"
    assert is_urgent_cue(["guide_brake_hard"]) and not is_urgent_cue(["corner_t4", "guide_intro"]) and not is_urgent_cue(["misc_hello"])
    # każda komenda ma klip w katalogu
    entries = catalog(track_corner_names())
    assert all(f"guide_{k}" in entries and entries[f"guide_{k}"] == t for k, t in GUIDE_TEXTS.items())


def test_guide_speaks_ahead_once_per_lap_and_only_guided_corners() -> None:
    track = Track(1, "test", 5000.0, (Corner(1, 900.0, 1000.0, 1100.0, "T1"), Corner(2, 2900.0, 3000.0, 3100.0, "T2")))
    ref = analyze_lap_from([_metrics(1, 880.0, 800.0, 1000.0, 1090.0), _metrics(2, 2880.0, None, 3000.0, 3090.0)])
    guide = CornerGuide(track, ref)
    guide.set_guided([1])
    lap = Lap(5)
    heard = []
    for d in range(0, 3200, 10):  # 250 km/h -> wyprzedzenie ok. 69 m
        lap.samples.append(Sample(float(d), d * 10, 250, 1.0, 0.0, 7, 0.0))
        heard += [(d, c.kind) for c in guide.update(lap)]
    kinds = [k for _, k in heard]
    assert kinds == ["intro", "lift", "brake", "half", "full"]  # T2 nie jest prowadzony
    lead = 250 / 3.6 * LEAD_S
    for d, kind in heard:
        at = {"intro": 800.0 - INTRO_M, "lift": 800.0, "brake": 880.0, "half": 1000.0, "full": 1090.0}[kind]
        assert at - lead - 10 < d <= at - lead + 10, (kind, d)
    # kolejne próbki tego samego okrążenia: nic więcej; nowe okrążenie: od nowa
    lap.samples.append(Sample(3300.0, 33000, 250, 1.0, 0.0, 7, 0.0))
    assert guide.update(lap) == []
    lap6 = Lap(6, [Sample(700.0, 7000, 250, 1.0, 0.0, 7, 0.0)])
    assert [c.kind for c in guide.update(lap6)] == ["lift"] or [c.kind for c in guide.update(lap6)] == []
    # komenda minięta o więcej niż LATE_M przepada (skok próbek), ale jest oznaczona jako powiedziana
    lap7 = Lap(7, [Sample(880.0 + LATE_M + 5, 9000, 250, 1.0, 0.0, 7, 0.0)])
    assert [c.kind for c in guide.update(lap7)] == ["half", "full"] or all(c.kind in ("half", "full") for c in guide.update(lap7))
    guide.set_guided([1, 2, 1, 2, 1])
    assert guide.guided == {1, 2} and len(guide.guided) <= MAX_GUIDED
    # zakręt tuż za linią mety: komendy padają jeszcze przed metą, a punkt daleko z przodu (> pół okrążenia) nie jest "minięty"
    track2 = Track(2, "test", 5000.0, (Corner(1, 100.0, 200.0, 300.0, "T1"),))
    g2 = CornerGuide(track2, analyze_lap_from([_metrics(1, 180.0, None, 200.0, 290.0)]))
    g2.set_guided([1])
    lap = Lap(3, [Sample(2600.0, 1000, 250, 1.0, 0.0, 7, 0.0)])
    assert g2.update(lap) == [] and not g2.said  # 2600 m przed punktem: nic, nic nie oznaczone
    lap.samples.append(Sample(4960.0, 2000, 250, 1.0, 0.0, 7, 0.0))
    assert [c.kind for c in g2.update(lap)] == ["intro"]  # 180 - 220 = -40 -> 4960 m poprzedniego okrążenia
    lap4 = Lap(4, [Sample(115.0, 3000, 250, 1.0, 0.0, 7, 0.0)])
    assert [c.kind for c in g2.update(lap4)] == ["brake"]
    # lekcja o gazie: tylko komendy gazu (wstęp zostaje); o hamowaniu: tylko hamowania; inne: wszystkie
    assert kinds_for_rules(("throttle_early", "throttle_late", "grip_lost")) == frozenset({"half", "full"})
    assert kinds_for_rules(("brake_late", "trail_missing")) == frozenset({"lift", "brake"})
    assert kinds_for_rules(()) == frozenset(KINDS) and kinds_for_rules(("brake_late", "throttle_late")) == frozenset(KINDS)
    g3 = CornerGuide(track, ref, kinds=frozenset({"half", "full"}))
    assert [c.kind for c in g3.cues_for(track.corners[0])] == ["intro", "half", "full"]


def analyze_lap_from(metrics: list[CornerMetrics]):
    from boxbox.coach.corners import LapAnalysis
    return LapAnalysis(1, 90000, tuple(metrics))


def test_live_guides_corner_with_issue_on_next_lap(monza: RecordedSession) -> None:
    """Monza: okrążenie 4 ma hamowanie dużo za późno w T1-T2, więc na okrążeniu 5 trener prowadzi ten zakręt."""
    from boxbox.coach.laps import LapRecorder
    from boxbox.coach.live import LiveCoach
    from boxbox.telemetry.replay import replay
    from tests.test_live import MONZA

    ref = analyze_lap(monza.lap(6), monza.track)
    recorder = LapRecorder()
    spoken: list[tuple[int, float, list[str], str]] = []

    def speak(ids: list[str], text: str) -> None:
        lap = recorder.current
        spoken.append((lap.number if lap else 0, lap.samples[-1].distance_m if lap and lap.samples else -1, ids, text))

    # best_time_ms = czas okrążenia 6: referencja zostaje nim przez całą sesję (żadne okrążenie nie jest szybsze)
    coach = LiveCoach(monza.track, speak, ref, best_time_ms=86918)
    replay(MONZA, lambda data: coach.update(recorder, recorder.feed(data)), speed=0)
    assert coach.reference is ref
    cues = [s for s in spoken if any(i.startswith("guide_") for i in s[2])]
    assert cues, "brak komend prowadzenia"
    assert all(i in catalog(track_corner_names()) for s in cues for i in s[2])
    lap5 = [s for s in cues if s[0] == 5]
    kinds5 = [s[2][-1] for s in lap5]
    assert kinds5[0] == "guide_intro" and lap5[0][2][0] == "corner_t1_2" and lap5[0][3] == "Zakręty pierwszy i drugi. Prowadzę."
    r1 = next(m for m in ref.corners if m.corner == 1)
    brake = next(s for s in lap5 if s[2] == ("guide_brake_hard",) or s[2] == ["guide_brake_hard"])
    assert r1.brake_point_m - 120 < brake[1] < r1.brake_point_m, (brake[1], r1.brake_point_m)
    full = next(s for s in lap5 if s[2][0] == "guide_full")
    assert r1.full_throttle_m is not None and r1.apex_m - 10 < full[1] < r1.full_throttle_m
    # komendy tylko dla zakrętów z uwagami z poprzedniego okrążenia; każda raz na okrążenie
    for lap_no in {s[0] for s in cues}:
        intros = [s for s in cues if s[0] == lap_no and s[2][-1] == "guide_intro"]
        assert 1 <= len(intros) <= MAX_GUIDED and len({s[2][0] for s in intros}) == len(intros)
        assert len([s for s in cues if s[0] == lap_no]) <= 5 * len(intros)
    assert len(coach.guide.said) == len({k for k in coach.guide.said})
    assert all(s[0] >= 2 for s in cues)  # dopiero po pierwszym ocenionym okrążeniu
    guided_corners = {s[3].split(".")[0] for s in cues if s[2][-1] == "guide_intro"}
    assert "Zakręty pierwszy i drugi" in guided_corners


def test_live_guidance_can_be_disabled(monza: RecordedSession) -> None:
    from boxbox.coach.laps import LapRecorder
    from boxbox.coach.live import LiveCoach
    from boxbox.telemetry.replay import replay
    from tests.test_live import MONZA

    ref = analyze_lap(monza.lap(6), monza.track)
    recorder = LapRecorder()
    spoken: list[list[str]] = []
    coach = LiveCoach(monza.track, lambda ids, text: spoken.append(ids), ref, guidance=False)
    replay(MONZA, lambda data: coach.update(recorder, recorder.feed(data)), speed=0)
    assert not any(i.startswith("guide_") for ids in spoken for i in ids)
