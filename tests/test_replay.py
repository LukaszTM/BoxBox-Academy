from pathlib import Path

from boxbox.app import main
from boxbox.telemetry.header import PacketHeader, pack_header
from boxbox.telemetry.recording import RecordingWriter
from boxbox.telemetry.replay import replay


def make_recording(path: Path) -> None:
    with RecordingWriter(path) as w:
        for t, pid in [(0.0, 6), (0.5, 2), (1.5, 6)]:
            w.write(t, pack_header(PacketHeader(2025, 25, 1, 0, 1, pid, 1, t, 0, 0, 0, 255)))


def test_replay_keeps_timing(tmp_path: Path) -> None:
    path = tmp_path / "r.bin"
    make_recording(path)
    now = 0.0
    events: list[tuple[float, int]] = []

    def sleep(seconds: float) -> None:
        nonlocal now
        now += seconds

    count = replay(path, lambda d: events.append((now, len(d))), speed=2.0, sleep=sleep, clock=lambda: now)
    assert count == 3
    assert [t for t, _ in events] == [0.0, 0.25, 0.75]


def test_replay_speed_zero_does_not_sleep(tmp_path: Path) -> None:
    path = tmp_path / "r.bin"
    make_recording(path)

    def fail(_: float) -> None:
        raise AssertionError("nie powinno czekać")

    assert replay(path, lambda d: None, speed=0, sleep=fail) == 3


def test_app_replay_summary(tmp_path: Path, capsys) -> None:
    path = tmp_path / "r.bin"
    make_recording(path)
    assert main(["--replay", str(path), "--speed", "0"]) == 0
    out = capsys.readouterr().out
    assert "Odebrano 3 pakietów" in out
    # nagranie ma same nagłówki, więc parsery pakietów zgłaszają złą długość
    assert "CAR_TELEMETRY: 2 (błędy parsera: 2)" in out
    assert "LAP_DATA: 1 (błędy parsera: 1)" in out
