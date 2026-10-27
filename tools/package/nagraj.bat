@echo off
rem Nagrywanie telemetrii F1 25 (bez nakladki). Uzycie: nagraj.bat <nazwa, moze byc kilka slow>
if "%~1"=="" (
  echo Podaj nazwe nagrania, np.: nagraj.bat bahrajn-tt
  exit /b 1
)
cd /d "%~dp0"
if not exist "boxbox\app.py" cd /d "%~dp0..\.."
rem (skrypt dziala z paczki ZIP albo z tools\package w klonie repozytorium)
set "NAZWA=%*"
set "NAZWA=%NAZWA: =-%"
py -3 -m boxbox.telemetry.record --name %NAZWA%
