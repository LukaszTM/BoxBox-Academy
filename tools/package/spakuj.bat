@echo off
rem Kompresja do wysylki (xz); jesli > 24 MB, dzieli na czesci po 20 MB.
rem Uzycie: spakuj.bat recordings\plik.bin        (nagranie)
rem         spakuj.bat assets\voice\raw          (caly folder klipow -> raw.tar.xz + czesci)
if "%~1"=="" (
  echo Uzycie: spakuj.bat recordings\plik.bin  albo  spakuj.bat assets\voice\raw
  exit /b 1
)
cd /d "%~dp0"
if not exist "boxbox\app.py" cd /d "%~dp0..\.."
rem (skrypt dziala z paczki ZIP albo z tools\package w klonie repozytorium)
py -3 -m boxbox.tools.pack spakuj "%~1"
