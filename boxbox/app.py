"""Punkt wejścia aplikacji: wybór trybu i spięcie warstw."""
import argparse
from collections import Counter
from collections.abc import Sequence
from pathlib import Path

from boxbox.telemetry.header import parse_header
from boxbox.telemetry.replay import replay

NO_DATA_MESSAGE = "brak danych"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="boxbox", description="BoxBox Academy")
    parser.add_argument("--mode", choices=["coach", "race"], default="coach")
    parser.add_argument("--replay", type=Path, help="plik nagrania zamiast żywej gry")
    parser.add_argument(
        "--speed", type=float, default=1.0, help="prędkość odtwarzania, 0 = bez czekania"
    )
    return parser


def _replay_summary(path: Path, speed: float) -> None:
    kinds: Counter[str] = Counter()

    def handle(data: bytes) -> None:
        header = parse_header(data)
        kinds[header.kind.name if header.kind else f"NIEZNANY_{header.packet_id}"] += 1

    total = replay(path, handle, speed=speed)
    print(f"Odtworzono {total} pakietów:")
    for name, n in sorted(kinds.items()):
        print(f"  {name}: {n}")


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.replay:
        _replay_summary(args.replay, args.speed)
        return 0
    print(NO_DATA_MESSAGE)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
