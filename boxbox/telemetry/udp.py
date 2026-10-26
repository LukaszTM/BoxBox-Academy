"""Nasłuch pakietów UDP z gry."""
import socket
import threading
import time
from collections.abc import Iterator

DEFAULT_PORT = 20777
MAX_PACKET = 2048


def listen(
    port: int = DEFAULT_PORT,
    host: str = "0.0.0.0",
    duration: float | None = None,
    stop: threading.Event | None = None,
) -> Iterator[bytes]:
    """Zwraca kolejne pakiety do Ctrl+C, upływu `duration` sekund albo ustawienia `stop`."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((host, port))
    sock.settimeout(0.5)
    start = time.monotonic()
    try:
        while (duration is None or time.monotonic() - start < duration) and not (stop and stop.is_set()):
            try:
                data, _ = sock.recvfrom(MAX_PACKET)
            except TimeoutError:
                continue
            yield data
    except KeyboardInterrupt:
        return
    finally:
        sock.close()
