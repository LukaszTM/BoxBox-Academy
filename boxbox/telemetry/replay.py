"""Odtwarzanie nagrania z zachowaniem czasu - zamiast żywej gry."""
import time
from collections.abc import Callable
from pathlib import Path

from boxbox.telemetry.recording import RecordedPacket, read_recording


def replay(
    path: Path,
    handler: Callable[[bytes], None],
    speed: float = 1.0,
    sleep: Callable[[float], None] = time.sleep,
    clock: Callable[[], float] = time.monotonic,
) -> int:
    """Wywołuje `handler` dla każdego pakietu w momencie z nagrania / `speed`.

    speed <= 0 oznacza odtwarzanie bez czekania. Zwraca liczbę pakietów.
    """
    start = clock()
    count = 0
    packet: RecordedPacket
    for packet in read_recording(path):
        if speed > 0:
            wait = packet.timestamp / speed - (clock() - start)
            if wait > 0:
                sleep(wait)
        handler(packet.data)
        count += 1
    return count
