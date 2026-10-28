"""Usuwa nazwy graczy z istniejących nagrań (recordings/*.bin, *.bin.xz, ZIP z .bin): GRACZ-NN zamiast nazw ludzi.

Nowe nagrania są anonimizowane w locie (RecordingWriter); to narzędzie czyści starsze pliki.
Użycie: python tools/anonimizuj_nagrania.py [recordings]
"""
import lzma
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from boxbox.telemetry.header import PacketId  # noqa: E402
from boxbox.telemetry.participants import anonymize_participants, parse_participants  # noqa: E402
from boxbox.telemetry.recording import MAGIC, _RECORD_HEADER  # noqa: E402


def scrub_bytes(raw: bytes) -> tuple[bytes, int]:
    if not raw.startswith(MAGIC):
        raise ValueError("to nie jest nagranie BoxBox")
    out = bytearray(raw[: len(MAGIC)])
    pos, changed = len(MAGIC), 0
    while pos + _RECORD_HEADER.size <= len(raw):
        ts, n = _RECORD_HEADER.unpack_from(raw, pos)
        pos += _RECORD_HEADER.size
        data = raw[pos:pos + n]
        pos += n
        if len(data) < n:
            break  # urwany ostatni rekord (przerwane nagrywanie): pomijamy, jak czytnik
        if len(data) > 6 and data[6] == PacketId.PARTICIPANTS:
            new = anonymize_participants(data)
            changed += new != data
            data = new
        out += _RECORD_HEADER.pack(ts, len(data)) + data
    return bytes(out), changed


def human_names(raw: bytes) -> set[str]:
    names: set[str] = set()
    pos = len(MAGIC)
    while pos + _RECORD_HEADER.size <= len(raw):
        _, n = _RECORD_HEADER.unpack_from(raw, pos)
        pos += _RECORD_HEADER.size
        data = raw[pos:pos + n]
        pos += n
        if len(data) > 6 and data[6] == PacketId.PARTICIPANTS:
            try:
                for c in parse_participants(data).cars:
                    if not c.ai_controlled and c.name:
                        names.add(c.name)
            except ValueError:
                pass
    return names


def scrub_file(path: Path) -> int:
    if path.suffix == ".zip":
        total = 0
        tmp = path.with_suffix(".tmp.zip")
        with zipfile.ZipFile(path) as src, zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as dst:
            for info in src.infolist():
                data = src.read(info)
                if info.filename.endswith(".bin"):
                    data, n = scrub_bytes(data)
                    total += n
                dst.writestr(info, data)
        tmp.replace(path)
        return total
    if path.name.endswith(".bin.xz"):
        raw = lzma.open(path).read()
        out, n = scrub_bytes(raw)
        if n:
            with lzma.open(path, "wb", preset=6) as f:
                f.write(out)
        return n
    if path.suffix == ".bin":
        out, n = scrub_bytes(path.read_bytes())
        if n:
            path.write_bytes(out)
        return n
    return 0


def main(folder: Path) -> None:
    for path in sorted(folder.iterdir()):
        if path.suffix in (".bin", ".zip") or path.name.endswith(".bin.xz"):
            print(f"{path.name}: {scrub_file(path)} pakietów zmienionych")


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else Path("recordings"))
