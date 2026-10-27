"""Recorder: nagrywa sesję z pozycją auta, wyznacza realny kształt toru i pakuje wszystko do ZIP.

Jeden program, bez parametrów, także jako BoxBoxRecorder.exe. Przebieg:
  1. czeka na telemetrię z gry (port 20777), nagrywa pakiety razem z Motion (pozycja auta),
  2. Enter albo Ctrl+C kończy; nagranie trafia do recordings/ i jest kompresowane xz,
  3. z najlepszego pełnego okrążenia liczy kształt toru (JSON + SVG), zapisuje też do boxbox/tracks/shape/,
  4. zbiera do recorder/nagranie-<tor>-<data>.zip: nagranie, kształt, plik toru i przewodnik (jeśli są),
     bazę i dziennik z data/, notatki i podsumowanie; ZIP ponad 24 MB dzieli na części.
Użycie: python -m boxbox.recorder [--replay nagranie.bin[.xz]] [--port N] [--dir recordings] [--out recorder]
"""
import argparse
import json
import lzma
import shutil
import sys
import threading
import time
import zipfile
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path

from boxbox.coach.laps import LapRecorder
from boxbox.telemetry.record import recording_path
from boxbox.telemetry.recording import SKIPPED_FOR_SHAPE, RecordingWriter, is_needed
from boxbox.telemetry.replay import replay
from boxbox.telemetry.udp import DEFAULT_PORT, listen
from boxbox.tools.pack import LIMIT_MB, split
from boxbox.tracks.model import load_track, track_path
from boxbox.tracks.shape import SHAPE_DIR, TrackShape, build_shape, save_shape, shape_path, to_svg
from boxbox.ui.overlay_model import GUIDE_DIR

MIN_MOTION_SAMPLES = 200


class ShapeCollector:
    """Łączy pozycję z Motion z dystansem z Lap Data: (okrążenie, dystans, x, z)."""

    def __init__(self) -> None:
        self.recorder = LapRecorder()
        self.state = self.recorder.state
        self.samples: dict[int, list[tuple[float, float, float]]] = {}
        self.packets = 0

    def feed(self, data: bytes) -> None:
        self.recorder.feed(data)
        self.packets += 1
        st = self.state
        if st.motion is not None and st.lap is not None and st.motion.header.frame_identifier == st.lap.header.frame_identifier:
            lap = st.lap.player
            if lap.lap_distance >= 0 and not lap.pit_status:
                pos = st.motion.player
                self.samples.setdefault(lap.current_lap_num, []).append((lap.lap_distance, pos.x, pos.z))

    def best_lap_samples(self, length_m: float) -> tuple[int, list[tuple[float, float, float]]] | None:
        best = None
        for num, pts in self.samples.items():
            if len(pts) < MIN_MOTION_SAMPLES:
                continue
            ds = [d for d, _, _ in pts]
            coverage = (max(ds) - min(ds)) / length_m
            if coverage >= 0.95 and (best is None or len(pts) > len(best[1])):
                best = (num, pts)
        return best


def _wait_for_enter(stop: threading.Event) -> None:
    try:
        input()
    except (EOFError, OSError):
        return
    stop.set()


def record_session(port: int, directory: Path, name: str, collector: ShapeCollector) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = recording_path(directory, name, datetime.now())
    stop = threading.Event()
    threading.Thread(target=_wait_for_enter, args=(stop,), daemon=True).start()
    print(f"Nasłuch na porcie {port}. Jedź co najmniej 2 pełne okrążenia, potem Enter (albo Ctrl+C).")
    start = time.monotonic()
    last_note = 0.0
    with RecordingWriter(path) as writer:
        try:
            for data in listen(port, stop=stop):
                if is_needed(data, SKIPPED_FOR_SHAPE):
                    if writer.count == 0:
                        start = time.monotonic()
                        print("Telemetria dotarła, nagrywam...")
                    writer.write(time.monotonic() - start, data)
                collector.feed(data)
                now = time.monotonic()
                if now - last_note > 5 and collector.state.lap is not None:
                    last_note = now
                    lap = collector.state.lap.player
                    laps = len([n for n, p in collector.samples.items() if len(p) >= MIN_MOTION_SAMPLES])
                    print(f"\r  okrążenie {lap.current_lap_num}, {lap.lap_distance:6.0f} m, okrążeń z pozycją: {laps}   ", end="", flush=True)
        except KeyboardInterrupt:
            pass
    print()
    return path


def compress(path: Path) -> Path:
    dst = path.with_name(path.name + ".xz")
    with open(path, "rb") as f_in, lzma.open(dst, "wb", preset=6) as f_out:
        shutil.copyfileobj(f_in, f_out, 1 << 20)
    path.unlink()
    return dst


def make_shape(collector: ShapeCollector) -> TrackShape | None:
    st = collector.state
    if st.session is None:
        print("Brak pakietu Session: nie wiem, jaki to tor.")
        return None
    length = float(st.session.track_length_m)
    best = collector.best_lap_samples(length)
    if best is None:
        got = {n: len(p) for n, p in collector.samples.items()}
        print(f"Za mało pozycji na pełne okrążenie (próbki per okrążenie: {got}). Potrzebny pakiet Motion z gry i pełne okrążenie.")
        return None
    track = None
    try:
        track = load_track(track_path(st.session.track_id))
    except FileNotFoundError:
        pass
    shape = build_shape(best[1], st.session.track_id, st.session.track_name, length, track)
    print(f"Kształt toru z okrążenia {best[0]}: {len(shape.points)} punktów co {shape.step_m:.0f} m, {len(shape.corners)} zakrętów.")
    return shape


def build_report(
    recording: Path | None, shape: TrackShape | None, collector: ShapeCollector, out_dir: Path,
    data_dir: Path = Path("data"), shape_dir: Path = SHAPE_DIR, guide_dir: Path = GUIDE_DIR,
) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    st = collector.state
    track_id = st.session.track_id if st.session else None
    track_name = (st.session.track_name if st.session else "nieznany").lower().replace(" ", "-")
    stamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    zip_path = out_dir / f"nagranie-{track_name}-{stamp}.zip"
    files: list[tuple[Path, str]] = []
    if recording is not None and recording.exists():
        files.append((recording, f"recordings/{recording.name}"))
    if shape is not None:
        shape_json = out_dir / f"{track_name}-ksztalt.json"
        save_shape(shape, shape_json)
        svg = out_dir / f"{track_name}-ksztalt.svg"
        svg.write_text(to_svg(shape), encoding="utf-8")
        files += [(shape_json, f"shape/{shape.track_id}.json"), (svg, f"shape/{shape.track_id}.svg")]
        try:
            save_shape(shape, shape_path(shape.track_id, shape_dir))
        except OSError:
            pass
    if track_id is not None:
        for p, arc in ((track_path(track_id), f"tracks/data/{track_id}.json"), (guide_dir / f"{track_id}.json", f"tracks/guide/{track_id}.json")):
            if p.exists():
                files.append((p, arc))
    for name in ("boxbox.sqlite", "boxbox.log"):
        if (data_dir / name).exists():
            files.append((data_dir / name, f"data/{name}"))
    notes = out_dir / f"nagranie-{track_name}-{stamp}.txt"
    laps = [(n, len(p)) for n, p in sorted(collector.samples.items())]
    summary = {
        "tor": st.session.track_name if st.session else None, "track_id": track_id,
        "dlugosc_m": float(st.session.track_length_m) if st.session else None,
        "format": sorted(st.formats), "pakiety": dict(st.packets), "bledy": {k: v for k, v in st.errors.items() if v},
        "okrazenia_z_pozycja": laps, "ksztalt": shape is not None, "nagranie": recording.name if recording else None,
    }
    notes.write_text(
        "BoxBox Academy - recorder, podsumowanie sesji\n" + json.dumps(summary, ensure_ascii=False, indent=1)
        + "\n\nNotatki (uzupełnij): tor, asysty, co się działo:\n", encoding="utf-8",
    )
    files.append((notes, notes.name))
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for src, arc in files:
            z.write(src, arc)
    size_mb = zip_path.stat().st_size / (1 << 20)
    print(f"Paczka: {zip_path} ({size_mb:.1f} MB), plików: {len(files)}")
    if size_mb > LIMIT_MB:
        parts = split(zip_path)
        zip_path.unlink()
        print(f"Za duży na GitHub: podzielony na {len(parts)} części. Wyślij wszystkie.")
        return parts
    return [zip_path]


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Recorder kształtu toru BoxBox Academy")
    parser.add_argument("--replay", type=Path, help="zamiast nagrywać: policz kształt z istniejącego nagrania (musi mieć pakiety Motion)")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--dir", type=Path, default=Path("recordings"))
    parser.add_argument("--out", type=Path, default=Path("recorder"))
    parser.add_argument("--name", default="ksztalt")
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument("--shape-dir", type=Path, default=SHAPE_DIR, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    print("BoxBox Academy - recorder kształtu toru")
    collector = ShapeCollector()
    if args.replay:
        replay(args.replay, collector.feed, speed=0)
        recording = args.replay
    else:
        try:
            raw = record_session(args.port, args.dir, args.name, collector)
        except OSError as exc:
            print(f"Nie mogę otworzyć portu {args.port}: {exc}. Zamknij inne programy z telemetrią (trener, nakładka).")
            return 1
        if collector.packets == 0:
            raw.unlink(missing_ok=True)
            print("Nie dotarł żaden pakiet. Sprawdź w grze: telemetria UDP wł., port 20777, IP 127.0.0.1.")
            return 1
        print(f"Pakietów: {collector.packets}. Kompresuję nagranie...")
        recording = compress(raw)
    shape = make_shape(collector)
    files = build_report(recording, shape, collector, args.out, data_dir=args.data_dir, shape_dir=args.shape_dir)
    print("Do wysłania (GitHub, gałąź claude/new-session-t6gmj8, folder recordings):")
    for f in files:
        print(f"  {f}")
    return 0 if shape is not None else 2


if __name__ == "__main__":
    code = main()
    if sys.stdin and sys.stdin.isatty():
        input("Enter zamyka okno...")
    raise SystemExit(code)
