@echo off
rem Buduje BoxBoxAcademy.exe (okno, jeden plik, bez Pythona u odbiorcy). Wynik: dist\BoxBoxAcademy.exe
cd /d "%~dp0"
if not exist "boxbox\app.py" cd /d "%~dp0..\.."
py -3 -m pip show pyinstaller >nul 2>&1 || py -3 -m pip install pyinstaller
py -3 -c "import PySide6" 2>nul || py -3 -m pip install PySide6
py -3 tools\build_exe.py gui
pause
