@echo off
rem Kompresja nagrania do wysylki (xz); jesli > 24 MB, dzieli na czesci po 20 MB.
rem Uzycie: spakuj.bat recordings\plik.bin
if "%~1"=="" (
  echo Uzycie: spakuj.bat recordings\plik.bin
  exit /b 1
)
cd /d "%~dp0"
py -3 -m boxbox.tools.pack spakuj "%~1"
