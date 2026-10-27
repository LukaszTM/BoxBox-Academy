@echo off
rem Buduje BoxBoxReporter.exe (PyInstaller, jeden plik, bez potrzeby Pythona u odbiorcy).
rem Wynik: dist\BoxBoxReporter.exe. Pierwsze uruchomienie instaluje PyInstaller (py -3 -m pip).
cd /d "%~dp0"
if not exist "boxbox\app.py" cd /d "%~dp0..\.."
py -3 -m pip show pyinstaller >nul 2>&1 || py -3 -m pip install pyinstaller
py -3 tools\build_exe.py
pause
