"""Raport błędu jednym poleceniem: dziennik, baza, ustawienia, ostatnie nagranie -> ZIP do wysłania.

Użycie: python -m boxbox.tools.bugreport ["co się stało"] [--data data] [--recordings recordings] [--out raporty-bledow]
"""
import argparse
import json
import platform
import sys
import zipfile
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path

from boxbox.gui.texts import VERSION
from boxbox.tools.pack import LIMIT_MB, split


def build_bug_report(
    description: str, data_dir: Path = Path("data"), recordings_dir: Path = Path("recordings"),
    out_dir: Path = Path("raporty-bledow"), include_recording: bool = True,
) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    zip_path = out_dir / f"blad-{stamp}.zip"
    info = {
        "opis": description, "wersja": VERSION, "czas": stamp, "python": sys.version.split()[0],
        "system": f"{platform.system()} {platform.release()}",
    }
    files: list[tuple[Path, str]] = []
    for name in ("boxbox.log", "boxbox.sqlite", "settings.json"):
        p = data_dir / name
        if p.exists():
            files.append((p, f"data/{name}"))
    if include_recording and recordings_dir.exists():
        recs = sorted(recordings_dir.glob("*.bin*"), key=lambda p: p.stat().st_mtime)
        if recs:
            files.append((recs[-1], f"recordings/{recs[-1].name}"))
            info["nagranie"] = recs[-1].name
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("opis.json", json.dumps(info, ensure_ascii=False, indent=1))
        for src, arc in files:
            z.write(src, arc)
    if zip_path.stat().st_size / (1 << 20) > LIMIT_MB:
        parts = split(zip_path)
        zip_path.unlink()
        return parts
    return [zip_path]


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Raport błędu BoxBox Academy")
    parser.add_argument("description", nargs="?", default="", help="co się stało (jedno zdanie)")
    parser.add_argument("--data", type=Path, default=Path("data"))
    parser.add_argument("--recordings", type=Path, default=Path("recordings"))
    parser.add_argument("--out", type=Path, default=Path("raporty-bledow"))
    parser.add_argument("--no-recording", action="store_true")
    args = parser.parse_args(argv)
    files = build_bug_report(args.description, args.data, args.recordings, args.out, not args.no_recording)
    print("Raport błędu gotowy, wyślij:")
    for f in files:
        print(f"  {f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
