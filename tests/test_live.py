from pathlib import Path

from boxbox.coach.corners import analyze_lap
from boxbox.coach.laps import LapRecorder
from boxbox.coach.live import LiveCoach
from boxbox.telemetry.replay import replay
from boxbox.voice.phrases import catalog, track_corner_names
from tests.conftest import RECORDINGS, RecordedSession

MONZA = RECORDINGS / "monza-trening_2026-10-26_153411.bin.xz"


def run_live(track, reference, corner_messages=True):
    recorder = LapRecorder()
    spoken: list[tuple[int, float, list[str], str]] = []

    def speak(ids: list[str], text: str) -> None:
        lap = recorder.current
        spoken.append((lap.number if lap else 0, lap.samples[-1].distance_m if lap and lap.samples else -1, ids, text))

    coach = LiveCoach(track, speak, reference, corner_messages=corner_messages)

    def handle(data: bytes) -> None:
        coach.update(recorder, recorder.feed(data))

    replay(MONZA, handle, speed=0)
    coach.finish()
    return spoken, coach


def test_live_corner_and_lap_messages_with_reference(monza: RecordedSession) -> None:
    ref = analyze_lap(monza.lap(6), monza.track)
    spoken, coach = run_live(monza.track, ref)
    texts = [s[3] for s in spoken]
    assert texts[0].startswith("Mechanik na radiu") and texts[1].startswith("Mam twoje najlepsze")
    # okrążenie 4: komunikat po Z1 (T1-T2) zanim auto dojedzie do Z2 (wejście 2008 m)
    z1 = [s for s in spoken if s[0] == 4 and "T1-T2: Hamowanie" in s[3] and "Zacznij" not in s[3]]
    assert z1 and monza.track.corners[0].exit_m < z1[0][1] < monza.track.corners[1].entry_m
    assert z1[0][2][0] == "corner_t1_2" and z1[0][2][1].startswith("rule_brake_late")
    # podsumowanie okrążenia 4 po mecie (na początku okrążenia 5), ze wskazówkami
    summary = [s for s in spoken if s[0] == 5 and s[2] == ["misc_lap_summary"]]
    assert summary and summary[0][1] < 50
    after = [s for s in spoken if s[0] == 5 and s[1] < 50 and "Zacznij" in s[3]]
    assert after
    # okrążenie 3 (czyste, 1:28.0): "najwięcej do zyskania" albo czyste - ale nie pełne podsumowanie
    lap3 = [s for s in spoken if s[0] == 4 and s[1] < 50]
    assert lap3 and (lap3[0][2][0] in ("misc_lap_clean", "misc_biggest_loss") or lap3[0][2] == ["misc_lap_summary"])
    assert texts[-1].startswith("Koniec sesji")
    # każdy użyty klip istnieje w katalogu
    entries = catalog(track_corner_names())
    assert all(i in entries for s in spoken for i in s[2])
    # krótki komunikat po zakręcie (bez wskazówki "_b") najwyżej raz na zakręt na okrążenie
    keys = [(s[0], s[2][0]) for s in spoken if s[2][0].startswith("corner_") and not any(i.endswith("_b") for i in s[2])]
    assert keys and len(keys) == len(set(keys))


def test_live_without_reference_learns_first_valid_lap(monza: RecordedSession) -> None:
    spoken, coach = run_live(monza.track, None)
    texts = [s[3] for s in spoken]
    assert any(t.startswith("Pierwsze okrążenie zapisane") for t in texts)
    assert coach.reference is not None and coach.best_time_ms == 86918  # najlepsze z sesji (okr. 6)
    assert sum(1 for t in texts if t.startswith("Nowe najlepsze")) >= 1
    # przed pierwszą referencją (okrążenie 1) żadnych komunikatów o zakrętach
    assert not any(s[0] == 1 and s[2][0].startswith("corner_") for s in spoken)
    assert not any(t.startswith("Mam twoje najlepsze") for t in texts)


def test_live_corner_messages_can_be_disabled(monza: RecordedSession) -> None:
    ref = analyze_lap(monza.lap(6), monza.track)
    spoken, _ = run_live(monza.track, ref, corner_messages=False)
    # bez krótkich komunikatów po zakręcie (klip zakrętu na początku, bez wskazówki "_b")
    assert not any(s[2][0].startswith("corner_") and not any(i.endswith("_b") for i in s[2]) for s in spoken)
    assert any(s[2] == ["misc_lap_summary"] for s in spoken)
