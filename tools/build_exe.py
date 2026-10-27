"""Buduje BoxBoxRecorder (jeden plik) przez PyInstaller.

Użycie: python tools/build_exe.py  ->  dist/BoxBoxRecorder(.exe)
Plik .exe powstaje tylko na Windows (PyInstaller nie buduje krzyżowo); na Linux/macOS powstaje
binarka dla tego systemu, co wystarcza do sprawdzenia, czy pakowanie działa.
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENTRY = ROOT / "boxbox" / "recorder.py"
NAME = "BoxBoxRecorder"
sep = ";" if sys.platform.startswith("win") else ":"


def main() -> int:
    cmd = [
        sys.executable, "-m", "PyInstaller", "--onefile", "--console", "--clean", "--noconfirm",
        "--name", NAME,
        "--paths", str(ROOT),
        "--add-data", f"{ROOT / 'boxbox' / 'tracks' / 'data'}{sep}boxbox/tracks/data",
        "--add-data", f"{ROOT / 'boxbox' / 'tracks' / 'guide'}{sep}boxbox/tracks/guide",
        "--hidden-import", "boxbox.telemetry.motion",
        "--distpath", str(ROOT / "dist"), "--workpath", str(ROOT / "build" / "pyinstaller"),
        "--specpath", str(ROOT / "build"),
        str(ENTRY),
    ]
    print(" ".join(cmd))
    rc = subprocess.call(cmd)
    if rc == 0:
        out = ROOT / "dist" / (NAME + (".exe" if sys.platform.startswith("win") else ""))
        print(f"Gotowe: {out} ({out.stat().st_size >> 20} MB)")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
