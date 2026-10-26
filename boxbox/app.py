"""Punkt wejścia aplikacji: wybór trybu i spięcie warstw."""
import argparse
import os
import time
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path

from boxbox.coach.analyze import report_laps
from boxbox.coach.laps import LapRecorder
from boxbox.coach.live import LiveCoach
from boxbox.storage.db import Database
from boxbox.tracks.model import load_track, track_path
from boxbox.voice.player import ClipLibrary, NullBackend, VoicePlayer
from boxbox.telemetry.header import SUPPORTED_FORMATS
from boxbox.telemetry.record import recording_path
from boxbox.telemetry.recording import RecordingWriter, is_needed
from boxbox.telemetry.replay import replay
from boxbox.telemetry.state import TelemetryState
from boxbox.telemetry.udp import DEFAULT_PORT, listen
from boxbox.ui.console import NO_DATA_MESSAGE, Console

__all__ = ["NO_DATA_MESSAGE", "main"]

DEFAULT_DB = Path("data") / "boxbox.sqlite"
DEFAULT_VOICE = Path("assets") / "voice"


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
    parser.add_argument("--record", help="na żywo: zapisz też nagranie sesji pod tą nazwą do recordings/")
    parser.add_argument("--voice", type=Path, default=DEFAULT_VOICE, help="folder z klipami WAV mechanika")
    parser.add_argument("--no-voice", action="store_true", help="bez dźwięku (komunikaty tylko w konsoli)")
    parser.add_argument("--volume", type=float, default=1.0, help="głośność mechanika, np. 1.5 (ponad 1 = wzmocnienie)")
    parser.add_argument(
        "--corner-messages", choices=["on", "off"], default="on", help="krótki komunikat tuż po zakręcie"
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


def _make_player(args: argparse.Namespace) -> VoicePlayer | None:
    """Odtwarzacz, gdy są klipy i dźwięk nie jest wyłączony; przy replayu bez czekania tylko konsola."""
    if args.no_voice or (args.replay and args.speed <= 0):
        return None
    library = ClipLibrary(args.voice)
    if len(library) == 0:
        print(f"Brak klipów głosu w {args.voice}; komunikaty tylko w konsoli.")
        return None
    player = VoicePlayer(library, volume=max(0.1, args.volume)).start()
    player.say(["misc_hello"], "test dźwięku")  # od razu po starcie: słychać, zanim wyjedziesz na tor
    print(f"Głos: {len(library)} klipów, backend {player.backend.name}. Powinieneś teraz słyszeć powitanie.")
    return player


def run(args: argparse.Namespace) -> tuple[TelemetryState, LapRecorder]:
    recorder = LapRecorder()
    state = recorder.state
    console = Console()
    console.update(state, force=True)  # od razu "brak danych", dopóki nic nie przyjdzie
    player = _make_player(args) if args.mode == "coach" else None
    coach: LiveCoach | None = None
    coach_failed = False

    def speak(ids: list[str], text: str) -> None:
        console.note(f"Mechanik: {text}")
        if player is not None:
            player.say(ids, text)

    def ensure_coach() -> None:
        """Trener startuje, gdy znamy tor (pakiet Session): plik toru + referencja z bazy."""
        nonlocal coach, coach_failed
        if coach is not None or coach_failed or state.session is None:
            return
        path = args.track or track_path(state.session.track_id)
        try:
            track = load_track(path)
        except FileNotFoundError:
            coach_failed = True
            console.note(f"Brak pliku toru {path}: trener na żywo wyłączony (tabela po sesji nadal będzie).")
            return
        reference = None
        best_time = None
        if args.db is not None:
            db = Database(args.db)
            ref = db.reference(track.track_id)
            db.close()
            if ref is not None:
                reference, best_time = ref.analysis, ref.lap.lap_time_ms
        coach = LiveCoach(
            track, speak, reference, corner_messages=args.corner_messages == "on", best_time_ms=best_time,
            said_hello=player is not None,  # powitanie poszło już na starcie aplikacji
            available=(lambda i: i in player.library) if player is not None else None,
        )

    writer: RecordingWriter | None = None
    rec_start = time.monotonic()
    if args.record and not args.replay:
        path = recording_path(Path("recordings"), args.record.replace(" ", "-"), datetime.now())
        path.parent.mkdir(parents=True, exist_ok=True)
        writer = RecordingWriter(path)
        console.note(f"Nagrywam sesję do {path}")

    def handle(data: bytes) -> None:
        nonlocal rec_start
        if writer is not None and is_needed(data):
            if writer.count == 0:
                rec_start = time.monotonic()
            writer.write(time.monotonic() - rec_start, data)
        finished = recorder.feed(data)
        if args.mode == "coach":
            ensure_coach()
            if coach is not None:
                coach.update(recorder, finished)
        console.update(state)

    wall0, cpu0 = time.monotonic(), sum(os.times()[:2])
    try:
        if args.replay:
            replay(args.replay, handle, speed=args.speed)
        else:
            for data in listen(args.port, duration=args.duration):
                handle(data)
    finally:
        if writer is not None:
            writer.close()
    wall, cpu = time.monotonic() - wall0, sum(os.times()[:2]) - cpu0
    console.update(state, force=True)
    console.finish()
    if not args.replay and wall > 1:
        print(f"Obciążenie: {100 * cpu / wall:.1f}% jednego rdzenia średnio przez {wall:.0f} s")
    if coach is not None:
        coach.finish()
    if player is not None:
        player.close()
        if player.errors:
            print(f"Głos: {len(player.errors)} błędów odtwarzania, pierwszy: {player.errors[0]}")
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
