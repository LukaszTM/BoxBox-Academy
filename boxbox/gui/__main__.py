"""python -m boxbox.gui  ->  okno BoxBox Academy."""
import sys
from pathlib import Path

if getattr(sys, "frozen", False):  # .exe: dane obok programu (data/, recordings/, assets/)
    import os

    os.chdir(Path(sys.executable).resolve().parent)

from boxbox.app import setup_log  # noqa: E402
from boxbox.gui.webapp import run  # noqa: E402

setup_log(Path("data") / "boxbox.log")
raise SystemExit(run())
