@echo off
rem Nagrywanie telemetrii F1 25. Uzycie: nagraj.bat <nazwa>   np. nagraj.bat bahrajn-tt
if "%~1"=="" (
  echo Podaj nazwe nagrania, np.: nagraj.bat bahrajn-tt
  exit /b 1
)
cd /d "%~dp0"
py -3 -m boxbox.telemetry.record --name %1
