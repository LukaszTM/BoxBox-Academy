@echo off
rem Recorder ksztaltu toru: nagrywa sesje z pozycja auta, liczy realny ksztalt toru i pakuje wszystko do ZIP.
rem Uzycie: recorder.bat [nazwa]   -> recorder\nagranie-<tor>-<data>.zip (lub czesci, gdy > 24 MB)
rem Gra: telemetria UDP wl., port 20777. Nie laczyc z trener.bat ani nakladka.bat (jeden port).
rem Jedz co najmniej 2 pelne okrazenia, potem Enter w tym oknie (albo Ctrl+C).
cd /d "%~dp0"
if not exist "boxbox\app.py" cd /d "%~dp0..\.."
rem (skrypt dziala z paczki ZIP albo z tools\package w klonie repozytorium)
set "NAZWA=%*"
if "%NAZWA%"=="" set "NAZWA=ksztalt"
set "NAZWA=%NAZWA: =-%"
py -3 -m boxbox.recorder --name %NAZWA%
pause
