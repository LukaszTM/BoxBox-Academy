@echo off
rem Szybkie sprawdzenie nagrania. Uzycie: sprawdz.bat recordings\plik.bin
if "%~1"=="" (
  echo Podaj plik nagrania, np.: sprawdz.bat recordings\bahrajn-tt_2026-10-26_180000.bin
  exit /b 1
)
cd /d "%~dp0"
py -3 -m boxbox.app --replay "%~1" --speed 0
