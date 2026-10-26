"""Punkt wejścia aplikacji: wybór trybu i spięcie warstw."""
import argparse
from collections.abc import Sequence
from pathlib import Path

from boxbox.telemetry.replay import replay
from boxbox.telemetry.state import TelemetryState
from boxbox.telemetry.udp import DEFAULT_PORT, listen
from boxbox.ui.console import NO_DATA_MESSAGE, Console

__all__ = ["NO_DATA_MESSAGE", "main"]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="boxbox", description="BoxBox Academy")
    parser.add_argument("--mode", choices=["coach", "race"], default="coach")
    parser.add_argument("--replay", type=Path, help="plik nagrania zamiast żywej gry")
    parser.add_argument(
        "--speed", type=float, default=1.0, help="prędkość odtwarzania, 0 = bez czekania"
    )
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="port UDP z gry")
    parser.add_argument("--duration", type=float, help="limit nasłuchu w sekundach")
    return parser


def _print_summary(state: TelemetryState) -> None:
    total = sum(state.packets.values())
    print(f"Odebrano {total} pakietów:")
    for name, n in sorted(state.packets.items()):
        errors = f" (błędy parsera: {state.errors[name]})" if state.errors[name] else ""
        print(f"  {name}: {n}{errors}")
    if state.errors["nagłówek"]:
        print(f"  pakiety bez poprawnego nagłówka: {state.errors['nagłówek']}")
    for fmt, n in sorted(state.unsupported_formats.items()):
        print(
            f"  UWAGA: {n} pakietów w formacie {fmt} - obsługiwany jest tylko 2025. "
            "Ustaw w grze UDP Format: 2025 (2026 Season Pack wysyła format 2026)."
        )


def run(args: argparse.Namespace) -> TelemetryState:
    state = TelemetryState()
    console = Console()
    console.update(state, force=True)  # od razu "brak danych", dopóki nic nie przyjdzie

    def handle(data: bytes) -> None:
        state.feed(data)
        console.update(state)

    if args.replay:
        replay(args.replay, handle, speed=args.speed)
    else:
        for data in listen(args.port, duration=args.duration):
            handle(data)
    console.update(state, force=True)
    console.finish()
    return state


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    state = run(args)
    if state.empty:
        return 0
    _print_summary(state)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
