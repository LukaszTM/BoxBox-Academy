@echo off
rem Okno BoxBox Academy (trener, kreator, karta kierowcy, postep, ustawienia). Wymaga: py -3 -m pip install PySide6
cd /d "%~dp0"
if not exist "boxbox\app.py" cd /d "%~dp0..\.."
py -3 -c "import PySide6" 2>nul || py -3 -m pip install PySide6
py -3 -m boxbox.gui
