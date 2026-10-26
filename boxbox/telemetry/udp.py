"""Nasłuch pakietów UDP z gry."""
import socket
import time
from collections.abc import Iterator

DEFAULT_PORT = 20777
MAX_PACKET = 2048


def listen(
    port: int = DEFAULT_PORT,
    host: str = "0.0.0.0",
    duration: float | None = None,
) -> Iterator[bytes]:
    """Zwraca kolejne pakiety do Ctrl+C lub upływu `duration` sekund."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((host, port))
    sock.settimeout(0.5)
    start = time.monotonic()
    try:
        while duration is None or time.monotonic() - start < duration:
            try:
                data, _ = sock.recvfrom(MAX_PACKET)
            except TimeoutError:
                continue
            yield data
    except KeyboardInterrupt:
        return
    finally:
        sock.close()
