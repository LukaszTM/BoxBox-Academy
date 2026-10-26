"""Punkt wejścia aplikacji: wybór trybu i spięcie warstw."""
import argparse
from collections.abc import Sequence
from pathlib import Path

from boxbox.coach.analyze import report_laps
from boxbox.coach.laps import LapRecorder
from boxbox.telemetry.header import SUPPORTED_FORMATS
from boxbox.telemetry.replay import replay
from boxbox.telemetry.state import TelemetryState
from boxbox.telemetry.udp import DEFAULT_PORT, listen
from boxbox.ui.console import NO_DATA_MESSAGE, Console

__all__ = ["NO_DATA_MESSAGE", "main"]

DEFAULT_DB = Path("data") / "boxbox.sqlite"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="boxbox", description="BoxBox Academy")
    parser.add_argument("--mode", choices=["coach", "race"], default="coach")
    parser.add_argument("--replay", type=Path, help="plik nagrania zamiast żywej gry")
    parser.add_argument(
        "--speed", type=float, default=1.0, help="prędkość odtwarzania, 0 = bez czekania"
    )
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="port UDP z gry")
    parser.add_argument("--duration", type=float, help="limit nasłuchu w sekundach")
    parser.add_argument("--track", type=Path, help="plik JSON toru; domyślnie boxbox/tracks/data/<track_id>.json")
    parser.add_argument(
        "--db", type=Path, default=DEFAULT_DB, help=f"baza okrążeń SQLite (domyślnie {DEFAULT_DB})"
    )
    parser.add_argument(
        "--reference", choices=["best", "rival", "pb"], default="best",
        help="z czym porównać zakręty: własne najlepsze okrążenie albo duch z Time Trial (tylko --replay)",
    )
    return parser


def _print_summary(state: TelemetryState) -> None:
    total = sum(state.packets.values())
    print(f"Odebrano {total} pakietów:")
    for name, n in sorted(state.packets.items()):
        errors = f" (błędy parsera: {state.errors[name]})" if state.errors[name] else ""
        print(f"  {name}: {n}{errors}")
    if state.errors["nagłówek"]:
        print(f"  pakiety bez poprawnego nagłówka: {state.errors['nagłówek']}")
    formats = ", ".join(f"{fmt}: {n}" for fmt, n in sorted(state.formats.items()))
    print(f"  format pakietów -> {formats}")
    for fmt, n in sorted(state.unsupported_formats.items()):
        print(
            f"  UWAGA: {n} pakietów w nieobsługiwanym formacie {fmt}; obsługiwane: "
            + ", ".join(str(f) for f in SUPPORTED_FORMATS)
            + ". Sprawdź w grze ustawienie UDP Format."
        )


def run(args: argparse.Namespace) -> tuple[TelemetryState, LapRecorder]:
    recorder = LapRecorder()
    state = recorder.state
    console = Console()
    console.update(state, force=True)  # od razu "brak danych", dopóki nic nie przyjdzie

    def handle(data: bytes) -> None:
        recorder.feed(data)
        console.update(state)

    if args.replay:
        replay(args.replay, handle, speed=args.speed)
    else:
        for data in listen(args.port, duration=args.duration):
            handle(data)
    console.update(state, force=True)
    console.finish()
    return state, recorder


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    state, recorder = run(args)
    if state.empty:
        return 0
    _print_summary(state)
    if args.mode == "coach":
        source = str(args.replay) if args.replay else f"live {state.session.header.session_uid if state.session else ''}".strip()
        print()
        print(report_laps(recorder, args.track, args.db, source, args.reference, args.replay))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
