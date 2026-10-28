"""Nagrania bez danych osobowych: nazwy graczy w pakiecie Participants zamienione na GRACZ-NN, nazwiska AI zostają."""
import lzma
import struct
from pathlib import Path

from boxbox.telemetry.header import PacketId
from boxbox.telemetry.participants import ANON_PREFIX, anonymize_participants, is_ai_name, parse_participants
from boxbox.telemetry.recording import MAGIC, RecordingWriter, _RECORD_HEADER, read_recording
from tests.builders import header_bytes


def _participants_packet(fmt: int, names: list[tuple[str, bool]]) -> bytes:
    from boxbox.telemetry import participants as pp

    layout = pp._CAR[fmt]
    buf = bytearray(pp.PACKET_SIZE[fmt])
    h = header_bytes(PacketId.PARTICIPANTS, fmt)
    buf[: len(h)] = h
    struct.pack_into("<B", buf, pp.HEADER_SIZE, len(names))
    base = pp.HEADER_SIZE + 1
    for i, (name, ai) in enumerate(names):
        car = base + i * layout.size
        fields = [int(ai), 1, 2, 3, 0, 44, 1, name.encode("utf-8").ljust(32, b"\x00"), 1, 1, 0, 1, 0] + [0] * 12
        layout.pack_into(buf, car, *fields)
    return bytes(buf)


def test_anonymize_keeps_ai_surnames_and_hides_people() -> None:
    for fmt in (2025, 2026):
        pkt = _participants_packet(fmt, [("Kowalski-77", False), ("HAMILTON", True), ("duch01", True), ("DE VRIES", True), ("", False)])
        out = anonymize_participants(pkt)
        names = [c.name for c in parse_participants(out).cars[:5]]
        assert names == [f"{ANON_PREFIX}00", "HAMILTON", f"{ANON_PREFIX}02", "DE VRIES", ""]
        assert len(out) == len(pkt) and anonymize_participants(out) == out  # idempotentne, rozmiar bez zmian
    assert is_ai_name("VERSTAPPEN") and not is_ai_name("Yoltbox") and not is_ai_name("5LECLERC")
    other = header_bytes(PacketId.SESSION, 2025) + b"\x00" * 10
    assert anonymize_participants(other) == other


def test_recording_writer_anonymizes_by_default(tmp_path: Path) -> None:
    pkt = _participants_packet(2025, [("MojNick", False), ("NORRIS", True)])
    with RecordingWriter(tmp_path / "a.bin") as w:
        w.write(0.0, pkt)
    with RecordingWriter(tmp_path / "b.bin", anonymize=False) as w:
        w.write(0.0, pkt)
    a = next(read_recording(tmp_path / "a.bin")).data
    b = next(read_recording(tmp_path / "b.bin")).data
    assert parse_participants(a).cars[0].name == f"{ANON_PREFIX}00" and parse_participants(a).cars[1].name == "NORRIS"
    assert parse_participants(b).cars[0].name == "MojNick"


def test_scrub_drops_truncated_last_record_and_reader_skips_empty(tmp_path: Path) -> None:
    """Przerwane nagranie kończy się urwanym rekordem: anonimizacja go pomija, a czytnik pomija pusty rekord ze starszych plików."""
    from tools.anonimizuj_nagrania import scrub_bytes

    pkt = _participants_packet(2025, [("Ktoś", False)])
    raw = MAGIC + _RECORD_HEADER.pack(0.0, len(pkt)) + pkt + _RECORD_HEADER.pack(1.0, len(pkt)) + pkt[:10]
    out, changed = scrub_bytes(raw)
    assert changed == 1 and out.count(_RECORD_HEADER.pack(0.0, len(pkt))) == 1 and len(out) == len(MAGIC) + _RECORD_HEADER.size + len(pkt)
    legacy = tmp_path / "stare.bin"
    legacy.write_bytes(MAGIC + _RECORD_HEADER.pack(0.0, len(pkt)) + pkt + _RECORD_HEADER.pack(1.0, 0))
    assert [len(p.data) for p in read_recording(legacy)] == [len(pkt)]


def test_repo_recordings_carry_no_player_names() -> None:
    """Każde nagranie w recordings/ ma tylko GRACZ-NN albo nazwiska AI; nowe nagrania przechodzą przez tools/anonimizuj_nagrania.py."""
    for path in sorted(Path("recordings").glob("*.bin.xz")):
        raw = lzma.open(path).read()
        assert raw.startswith(MAGIC)
        pos = len(MAGIC)
        checked = 0
        while pos + _RECORD_HEADER.size <= len(raw) and checked < 5:
            _, n = _RECORD_HEADER.unpack_from(raw, pos)
            pos += _RECORD_HEADER.size
            data = raw[pos:pos + n]
            pos += n
            if len(data) > 6 and data[6] == PacketId.PARTICIPANTS:
                checked += 1
                for c in parse_participants(data).cars:
                    assert not c.name or c.name.startswith(ANON_PREFIX) or is_ai_name(c.name), (path.name, c.name)
