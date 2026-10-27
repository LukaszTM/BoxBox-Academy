"""Pakowanie nagrań do wysyłki: xz + podział na części, które mieszczą się w limicie GitHuba.

Użycie:
  python -m boxbox.tools.pack spakuj recordings/plik.bin        -> plik.bin.xz (+ .part001... gdy > 24 MB)
  python -m boxbox.tools.pack spakuj assets/voice/raw           -> folder: raw.tar.xz (+ części)
  python -m boxbox.tools.pack sklej recordings/plik.bin.xz.part001  -> plik.bin.xz
"""
import argparse
import lzma
import shutil
import tarfile
from collections.abc import Sequence
from pathlib import Path

PART_MB = 20
LIMIT_MB = 24  # limit przeglądarki GitHub to 25 MB na plik


def pack_dir(src: Path) -> Path:
    """Folder -> jeden plik .tar obok niego (bez kompresji; tę robi compress)."""
    dst = src.with_name(src.name + ".tar")
    with tarfile.open(dst, "w") as tar:
        for path in sorted(src.rglob("*")):
            if path.is_file():
                tar.add(path, arcname=path.relative_to(src.parent).as_posix())
    return dst


def compress(src: Path) -> Path:
    dst = src.with_name(src.name + ".xz")
    with open(src, "rb") as f_in, lzma.open(dst, "wb", preset=6) as f_out:
        shutil.copyfileobj(f_in, f_out, 1 << 20)
    return dst


def split(src: Path, part_mb: int = PART_MB) -> list[Path]:
    parts = []
    with open(src, "rb") as f:
        n = 1
        while chunk := f.read(part_mb << 20):
            part = src.with_name(f"{src.name}.part{n:03d}")
            part.write_bytes(chunk)
            parts.append(part)
            n += 1
    return parts


def join(first_part: Path) -> Path:
    stem = first_part.name.rsplit(".part", 1)[0]
    parts = sorted(first_part.parent.glob(f"{stem}.part*"))
    dst = first_part.with_name(stem)
    with open(dst, "wb") as out:
        for part in parts:
            out.write(part.read_bytes())
    return dst


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Pakowanie nagrań do wysyłki")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p1 = sub.add_parser("spakuj")
    p1.add_argument("recording", type=Path)
    p1.add_argument("--limit-mb", type=int, default=LIMIT_MB)
    p2 = sub.add_parser("sklej")
    p2.add_argument("first_part", type=Path)
    args = parser.parse_args(argv)

    if args.cmd == "spakuj":
        src: Path = args.recording
        if not src.exists():
            print(f"Nie ma pliku {src}")
            return 1
        if src.is_dir():
            src = pack_dir(src)
            print(f"Folder spakowany do {src.name}")
        print(f"Kompresuję {src.name} ({src.stat().st_size >> 20} MB)...")
        xz = compress(src)
        if src.suffix == ".tar":
            src.unlink()
        size_mb = xz.stat().st_size / (1 << 20)
        print(f"Gotowe: {xz.name} ({size_mb:.1f} MB)")
        if size_mb > args.limit_mb:
            parts = split(xz)
            xz.unlink()
            print(f"Za duże na GitHub: podzielone na {len(parts)} części po {PART_MB} MB. Wyślij wszystkie:")
            for p in parts:
                print(f"  {p.name}")
        else:
            print("Mieści się w limicie: wyślij ten plik.")
        return 0
    dst = join(args.first_part)
    print(f"Sklejone: {dst}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
