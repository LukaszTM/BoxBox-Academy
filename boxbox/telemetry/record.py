"""Nagrywanie surowych pakietów UDP z gry do pliku.

Użycie: python -m boxbox.telemetry.record --name bahrain
"""
import argparse
import time
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path

from boxbox.telemetry.recording import RecordingWriter
from boxbox.telemetry.udp import DEFAULT_PORT, listen


def recording_path(directory: Path, name: str, now: datetime) -> Path:
    return directory / f"{name}_{now:%Y-%m-%d_%H%M%S}.bin"


def record(
    path: Path,
    port: int = DEFAULT_PORT,
    host: str = "0.0.0.0",
    duration: float | None = None,
) -> tuple[int, int]:
    """Nagrywa do `path` do Ctrl+C lub upływu `duration`. Zwraca (pakiety, bajty)."""
    start = time.monotonic()
    with RecordingWriter(path) as writer:
        for data in listen(port, host, duration):
            if writer.count == 0:
                start = time.monotonic()  # czas liczony od pierwszego pakietu
                print("Odbieram dane z gry, nagrywam...")
            writer.write(time.monotonic() - start, data)
    return writer.count, writer.size


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Nagrywanie telemetrii F1 25")
    parser.add_argument("--name", required=True, help="np. bahrain-bledy")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--dir", type=Path, default=Path("recordings"))
    parser.add_argument("--duration", type=float, help="limit w sekundach")
    args = parser.parse_args(argv)

    args.dir.mkdir(parents=True, exist_ok=True)
    path = recording_path(args.dir, args.name, datetime.now())
    notes = path.with_suffix(".txt")
    notes.write_text(
        "Tor:\nAsysty (skrzynia / TC / ABS):\nOkrążenia i błędy (numer okrążenia, zakręt, błąd):\n",
        encoding="utf-8",
    )
    print(f"Nasłuchuję na porcie {args.port}. Plik: {path}. Zatrzymanie: Ctrl+C.")
    count, size = record(path, args.port, duration=args.duration)
    if count == 0:
        path.unlink(missing_ok=True)
        notes.unlink(missing_ok=True)
        print("Nie odebrano żadnego pakietu - sprawdź ustawienia telemetrii w grze.")
        return 1
    print(f"Zapisano {count} pakietów ({size} B). Uzupełnij notatki: {notes}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
