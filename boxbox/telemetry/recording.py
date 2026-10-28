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

from boxbox.telemetry.header import PacketId
from boxbox.telemetry.participants import anonymize_participants

MAGIC = b"BBXREC01"
_RECORD_HEADER = struct.Struct("<dH")

# Typy pakietów pomijane przy nagrywaniu (id z nagłówka): duże i częste, nieużywane przez aplikację.
# Motion (0), Car Setups (5), Session History (11), Tyre Sets (12), Motion Ex (13), Lap Positions (15).
SKIPPED_PACKET_IDS = frozenset({0, 5, 11, 12, 13, 15})
PACKET_ID_OFFSET = 6  # bajt id pakietu w nagłówku


def is_needed(data: bytes, skipped: frozenset[int] = SKIPPED_PACKET_IDS) -> bool:
    return len(data) <= PACKET_ID_OFFSET or data[PACKET_ID_OFFSET] not in skipped


SKIPPED_FOR_SHAPE = SKIPPED_PACKET_IDS - {0}  # recorder kształtu toru zachowuje pakiet Motion (pozycja auta)


@dataclass(frozen=True)
class RecordedPacket:
    timestamp: float
    data: bytes


class RecordingWriter:
    """Zapis pakietów; nazwy graczy (własna i innych online) są zamieniane na GRACZ-NN, żeby nagranie nie niosło danych osobowych."""

    def __init__(self, path: Path, anonymize: bool = True) -> None:
        self._file: BinaryIO = open(path, "wb")
        self._file.write(MAGIC)
        self.count = 0
        self.size = 0
        self.anonymize = anonymize

    def write(self, timestamp: float, data: bytes) -> None:
        if self.anonymize and len(data) > 6 and data[6] == PacketId.PARTICIPANTS:
            data = anonymize_participants(data)
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
            if not data:
                continue  # pusty rekord (ślad po urwanym nagraniu w starszych plikach), nie pakiet
            yield RecordedPacket(timestamp, data)
