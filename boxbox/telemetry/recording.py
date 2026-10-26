"""Format pliku nagrania: surowe pakiety UDP z czasem odbioru.

Plik: nagłówek MAGIC, potem rekordy (czas w sekundach od startu nagrania
jako float64, długość pakietu jako uint16, bajty pakietu).
Nagranie z rozszerzeniem .xz jest czytane przez lzma (w repozytorium trzymamy
skompresowane: surowa sesja ma ~170 MB, po xz ~10 MB).
"""
import lzma
import struct
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO

MAGIC = b"BBXREC01"
_RECORD_HEADER = struct.Struct("<dH")


@dataclass(frozen=True)
class RecordedPacket:
    timestamp: float
    data: bytes


class RecordingWriter:
    def __init__(self, path: Path) -> None:
        self._file: BinaryIO = open(path, "wb")
        self._file.write(MAGIC)
        self.count = 0
        self.size = 0

    def write(self, timestamp: float, data: bytes) -> None:
        self._file.write(_RECORD_HEADER.pack(timestamp, len(data)))
        self._file.write(data)
        self.count += 1
        self.size += len(data)

    def close(self) -> None:
        self._file.close()

    def __enter__(self) -> "RecordingWriter":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()


def open_recording(path: Path) -> BinaryIO:
    if path.suffix == ".xz":
        return lzma.open(path, "rb")  # type: ignore[return-value]
    return open(path, "rb")


def read_recording(path: Path) -> Iterator[RecordedPacket]:
    with open_recording(path) as f:
        if f.read(len(MAGIC)) != MAGIC:
            raise ValueError(f"{path}: to nie jest nagranie BoxBox")
        while header := f.read(_RECORD_HEADER.size):
            if len(header) < _RECORD_HEADER.size:
                return  # urwany ostatni rekord (np. przerwane nagrywanie)
            timestamp, length = _RECORD_HEADER.unpack(header)
            data = f.read(length)
            if len(data) < length:
                return
            yield RecordedPacket(timestamp, data)
