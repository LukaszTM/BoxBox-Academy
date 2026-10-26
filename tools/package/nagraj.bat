@echo off
rem Nagrywanie telemetrii F1 25 (bez nakladki). Uzycie: nagraj.bat <nazwa, moze byc kilka slow>
if "%~1"=="" (
  echo Podaj nazwe nagrania, np.: nagraj.bat bahrajn-tt
  exit /b 1
)
cd /d "%~dp0"
set "NAZWA=%*"
set "NAZWA=%NAZWA: =-%"
py -3 -m boxbox.telemetry.record --name %NAZWA%
