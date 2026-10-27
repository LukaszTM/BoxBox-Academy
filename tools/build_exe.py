"""Buduje BoxBoxRecorder albo BoxBoxAcademy (jeden plik) przez PyInstaller.

Użycie: python tools/build_exe.py [recorder|gui]  ->  dist/BoxBoxRecorder(.exe) / dist/BoxBoxAcademy(.exe)
Plik .exe powstaje tylko na Windows (PyInstaller nie buduje krzyżowo); na Linux/macOS powstaje
binarka dla tego systemu, co wystarcza do sprawdzenia, czy pakowanie działa.
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TARGETS = {
    "recorder": (ROOT / "boxbox" / "recorder.py", "BoxBoxRecorder", "--console"),
    "gui": (ROOT / "boxbox" / "gui" / "__main__.py", "BoxBoxAcademy", "--windowed"),
}
sep = ";" if sys.platform.startswith("win") else ":"


def main(target: str = "recorder") -> int:
    entry, name, console = TARGETS[target]
    cmd = [
        sys.executable, "-m", "PyInstaller", "--onefile", console, "--clean", "--noconfirm",
        "--name", name,
        "--paths", str(ROOT),
        "--add-data", f"{ROOT / 'boxbox' / 'tracks' / 'data'}{sep}boxbox/tracks/data",
        "--add-data", f"{ROOT / 'boxbox' / 'tracks' / 'guide'}{sep}boxbox/tracks/guide",
        "--add-data", f"{ROOT / 'boxbox' / 'tracks' / 'shape'}{sep}boxbox/tracks/shape",
        "--hidden-import", "boxbox.telemetry.motion",
        "--distpath", str(ROOT / "dist"), "--workpath", str(ROOT / "build" / "pyinstaller"),
        "--specpath", str(ROOT / "build"),
    ]
    if target == "gui":
        # klipy głosu i logo obok .exe (nie w środku): użytkownik może je podmienić, a .exe zostaje mniejszy
        cmd += ["--add-data", f"{ROOT / 'assets' / 'logo.png'}{sep}assets"]
        if (ROOT / "assets" / "logo.ico").exists():
            cmd += ["--icon", str(ROOT / "assets" / "logo.ico")]
    cmd.append(str(entry))
    print(" ".join(cmd))
    rc = subprocess.call(cmd)
    if rc == 0:
        out = ROOT / "dist" / (name + (".exe" if sys.platform.startswith("win") else ""))
        print(f"Gotowe: {out} ({out.stat().st_size >> 20} MB)")
        if target == "gui":
            print("Obok .exe skopiuj folder assets\\voice (klipy glosu); data\\ i recordings\\ powstana same.")
    return rc


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1] if len(sys.argv) > 1 else "recorder"))
