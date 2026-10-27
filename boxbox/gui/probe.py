"""Sonda telemetrii: krótki nasłuch na porcie, żeby okno wiedziało, czy gra jest połączona."""
import socket
import threading
import time
from dataclasses import dataclass

from boxbox.telemetry.header import SUPPORTED_FORMATS
from boxbox.telemetry.state import TelemetryState
from boxbox.telemetry.udp import DEFAULT_PORT, MAX_PACKET


@dataclass(frozen=True)
class ProbeResult:
    packets: int = 0
    seconds: float = 0.0
    busy: bool = False
    fmt: int | None = None
    track: str = ""
    supported: bool = True

    @property
    def rate(self) -> float:
        return self.packets / self.seconds if self.seconds > 0 else 0.0

    @property
    def connected(self) -> bool:
        return self.packets > 0 and not self.busy


def probe(port: int = DEFAULT_PORT, seconds: float = 1.0, stop: threading.Event | None = None) -> ProbeResult:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.bind(("0.0.0.0", port))
    except OSError:
        sock.close()
        return ProbeResult(busy=True)
    sock.settimeout(0.2)
    state = TelemetryState()
    start = time.monotonic()
    n = 0
    try:
        while time.monotonic() - start < seconds and not (stop and stop.is_set()):
            try:
                data, _ = sock.recvfrom(MAX_PACKET)
            except TimeoutError:
                continue
            n += 1
            state.feed(data)
    finally:
        sock.close()
    fmt = max(state.formats, key=state.formats.get) if state.formats else None
    track = state.session.track_name if state.session else ""
    return ProbeResult(n, time.monotonic() - start, False, fmt, track, fmt is None or fmt in SUPPORTED_FORMATS)


class ProbeWorker(threading.Thread):
    """Co kilka sekund sonduje port, dopóki sesja nie potrzebuje gniazda."""

    def __init__(self, port: int, interval: float = 2.0, listen_s: float = 1.0) -> None:
        super().__init__(daemon=True, name="boxbox-sonda")
        self.port = port
        self.interval = interval
        self.listen_s = listen_s
        self.result = ProbeResult()
        self.stop = threading.Event()
        self.paused = threading.Event()

    def run(self) -> None:
        while not self.stop.is_set():
            if self.paused.is_set():
                self.stop.wait(0.3)
                continue
            self.result = probe(self.port, self.listen_s, self.stop)
            self.stop.wait(self.interval)
