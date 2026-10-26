import socket
import threading
import time
from datetime import datetime
from pathlib import Path

import pytest

from boxbox.telemetry.record import main, record, recording_path
from boxbox.telemetry.recording import MAGIC, RecordingWriter, read_recording


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def test_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "a.bin"
    with RecordingWriter(path) as w:
        w.write(0.0, b"abc")
        w.write(0.5, b"")
        w.write(1.25, b"\x00" * 1400)
    packets = list(read_recording(path))
    assert [(p.timestamp, len(p.data)) for p in packets] == [(0.0, 3), (0.5, 0), (1.25, 1400)]


def test_truncated_last_record_is_ignored(tmp_path: Path) -> None:
    path = tmp_path / "a.bin"
    with RecordingWriter(path) as w:
        w.write(0.0, b"abc")
        w.write(1.0, b"defgh")
    path.write_bytes(path.read_bytes()[:-2])
    assert [p.data for p in read_recording(path)] == [b"abc"]


def test_wrong_file_rejected(tmp_path: Path) -> None:
    path = tmp_path / "x.bin"
    path.write_bytes(b"not a recording")
    with pytest.raises(ValueError):
        list(read_recording(path))


def test_record_captures_udp(tmp_path: Path) -> None:
    port = _free_port()
    path = tmp_path / "live.bin"

    def send() -> None:
        time.sleep(0.3)
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            for i in range(1, 4):  # od 1: bajt 0 to id Motion, który recorder pomija
                s.sendto(bytes([i]) * 10, ("127.0.0.1", port))
                time.sleep(0.05)

    t = threading.Thread(target=send)
    t.start()
    count, size = record(path, port, host="127.0.0.1", duration=1.2)
    t.join()
    assert (count, size) == (3, 30)
    packets = list(read_recording(path))
    assert [p.data[0] for p in packets] == [1, 2, 3]
    assert packets[0].timestamp == pytest.approx(0, abs=0.01)
    assert packets[-1].timestamp > packets[0].timestamp
    assert path.read_bytes().startswith(MAGIC)


def test_recording_path_contains_name_and_date(tmp_path: Path) -> None:
    p = recording_path(tmp_path, "bahrain", datetime(2026, 10, 26, 18, 5, 9))
    assert p.name == "bahrain_2026-10-26_180509.bin"


def test_main_without_packets_reports_error(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    code = main(["--name", "x", "--dir", str(tmp_path), "--port", str(_free_port()), "--duration", "0.6"])
    assert code == 1
    assert "Nie odebrano" in capsys.readouterr().out
    assert list(tmp_path.iterdir()) == []


def test_record_skips_big_unused_packets(tmp_path: Path) -> None:
    from boxbox.telemetry.header import PacketHeader, PacketId, pack_header
    from boxbox.telemetry.recording import is_needed

    def packet(pid: int) -> bytes:
        return pack_header(PacketHeader(2025, 25, 1, 0, 1, pid, 1, 0.0, 0, 0, 0, 255)) + b"\x00" * 20

    assert not is_needed(packet(int(PacketId.MOTION))) and not is_needed(packet(int(PacketId.SESSION_HISTORY)))
    assert is_needed(packet(int(PacketId.CAR_TELEMETRY))) and is_needed(packet(int(PacketId.EVENT)))
    assert is_needed(b"abc")  # za krótki na nagłówek: zostaje, parser go policzy jako błąd

    port = _free_port()
    path = tmp_path / "f.bin"

    def send() -> None:
        time.sleep(0.3)
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            for pid in (0, 6, 11, 2):
                s.sendto(packet(pid), ("127.0.0.1", port))
                time.sleep(0.05)

    t = threading.Thread(target=send)
    t.start()
    count, _ = record(path, port, host="127.0.0.1", duration=1.2)
    t.join()
    assert count == 2
    assert [p.data[6] for p in read_recording(path)] == [6, 2]
