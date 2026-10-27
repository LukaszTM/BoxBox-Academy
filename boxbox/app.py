"""Punkt wejścia aplikacji: wybór trybu i spięcie warstw."""
import argparse
import logging
import sys
import traceback
from collections.abc import Sequence
from pathlib import Path

from boxbox.coach.analyze import report_laps
from boxbox.coach.laps import LapRecorder
from boxbox.session import DEFAULT_DB, DEFAULT_VOICE, CoachSession, SessionConfig, focus_line, progress_line
from boxbox.storage.db import Database
from boxbox.telemetry.header import SUPPORTED_FORMATS
from boxbox.telemetry.state import TelemetryState
from boxbox.telemetry.udp import DEFAULT_PORT
from boxbox.ui.console import NO_DATA_MESSAGE, Console
from boxbox.ui.overlay_model import SharedCoachState

log = logging.getLogger("boxbox")
__all__ = ["NO_DATA_MESSAGE", "main", "focus_line", "progress_line"]


def setup_log(path: Path) -> None:
    """Dziennik sesji obok bazy: co uruchomiono, co powiedział mechanik, każdy błąd. Do diagnozy bez nagrania."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        handler = logging.FileHandler(path, encoding="utf-8")
    except OSError:
        return
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    log.addHandler(handler)
    log.setLevel(logging.INFO)


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
    parser.add_argument("--progress", action="store_true", help="pokaż postęp (kroki asyst, zakręty opanowane) i wyjdź")
    parser.add_argument("--voice", type=Path, default=DEFAULT_VOICE, help="folder z klipami WAV mechanika")
    parser.add_argument("--no-voice", action="store_true", help="bez dźwięku (komunikaty tylko w konsoli)")
    parser.add_argument("--volume", type=float, default=1.0, help="głośność mechanika, np. 1.5 (ponad 1 = wzmocnienie)")
    parser.add_argument(
        "--corner-messages", choices=["on", "off"], default="on", help="krótki komunikat tuż po zakręcie"
    )
    parser.add_argument("--overlay", action="store_true", help="okno nakładki na grę (zakręt, słowa mechanika)")
    parser.add_argument("--lesson", help="lekcja: trener mówi tylko o jej regułach (np. braking_one_corner)")
    parser.add_argument("--lesson-corner", type=int, help="numer zakrętu do lekcji „jeden zakręt”")
    parser.add_argument("--explain", action="store_true", help="tryb „wytłumacz mi”: dłuższe wyjaśnienie przy pierwszej uwadze")
    parser.add_argument("--scale", type=float, default=1.0, help="nakładka: mnożnik wielkości napisów")
    parser.add_argument("--alpha", type=float, default=0.97, help="nakładka: krycie okna 0.5-1.0")
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


def _run_overlay(shared: SharedCoachState, args: argparse.Namespace) -> None:
    """Okno nakładki w wątku głównym (tkinter tego wymaga); telemetria chodzi obok."""
    try:
        from boxbox.ui.coach_overlay import CoachOverlayWindow

        CoachOverlayWindow(shared, scale=args.scale, alpha=args.alpha).run()
    except Exception:
        log.error("nakładka: %s", traceback.format_exc())
        print("Nakładka nie działa (szczegóły w dzienniku); trener pracuje dalej bez okna. Ctrl+C kończy.")
        shared.stop.wait()


def config_from_args(args: argparse.Namespace) -> SessionConfig:
    return SessionConfig(
        mode=args.mode, replay=args.replay, speed=args.speed, port=args.port, duration=args.duration,
        track=args.track, db=args.db, record=args.record, voice=args.voice, no_voice=args.no_voice,
        volume=args.volume, corner_messages=args.corner_messages == "on",
        lesson=args.lesson, lesson_corner=args.lesson_corner, explain_mode=args.explain,
    )


def run(args: argparse.Namespace) -> tuple[TelemetryState, LapRecorder]:
    console = Console()
    session = CoachSession(
        config_from_args(args),
        on_message=lambda ids, text: console.note(f"Mechanik: {text}"),
        on_note=console.note,
        on_packet=console.update,
    )
    console.update(session.state, force=True)  # od razu "brak danych", dopóki nic nie przyjdzie
    if args.overlay:
        session.start_background()
        try:
            _run_overlay(session.shared, args)
        except KeyboardInterrupt:
            pass
        finally:
            session.stop()
    else:
        session.start()
        session.loop()
    result = session.finish()
    console.update(session.state, force=True)
    console.finish()
    if not args.replay and result.wall_s > 1:
        print(f"Obciążenie: {result.cpu_percent:.1f}% jednego rdzenia średnio przez {result.wall_s:.0f} s")
    if result.player_errors:
        print(f"Głos: {len(result.player_errors)} błędów odtwarzania, pierwszy: {result.player_errors[0]}")
    if result.summary is not None:
        print(f"Dobrze:   {result.summary.good}")
        print(f"Do pracy: {result.summary.to_work}")
    if result.lesson_result is not None:
        ok, best, needed = result.lesson_result
        print(f"Lekcja: {'zaliczona' if ok else 'jeszcze nie'}, najlepsza seria {best}/{needed}")
    return session.state, session.recorder


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.progress:
        from boxbox.coach.analyze import render_progress

        db = Database(args.db)
        print(render_progress(db))
        db.close()
        return 0
    setup_log(args.db.parent / "boxbox.log")
    log.info("start: %s | cwd %s | python %s | %s", " ".join(argv if argv is not None else sys.argv[1:]),
             Path.cwd(), sys.version.split()[0], sys.platform)
    try:
        state, recorder = run(args)
    except Exception:
        log.error("aplikacja: %s", traceback.format_exc())
        raise
    if state.empty:
        log.info("koniec: brak danych z gry")
        return 0
    _print_summary(state)
    if args.mode == "coach":
        source = str(args.replay) if args.replay else f"live {state.session.header.session_uid if state.session else ''}".strip()
        print()
        print(report_laps(recorder, args.track, args.db, source, args.reference, args.replay))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
