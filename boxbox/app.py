"""Punkt wejścia aplikacji: wybór trybu i spięcie warstw."""
import argparse
from collections.abc import Sequence

NO_DATA_MESSAGE = "brak danych"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="boxbox", description="BoxBox Academy")
    parser.add_argument("--mode", choices=["coach", "race"], default="coach")
    parser.add_argument("--replay", help="plik nagrania zamiast żywej gry")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    build_parser().parse_args(argv)
    print(NO_DATA_MESSAGE)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
