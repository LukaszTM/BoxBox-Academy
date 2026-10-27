@echo off
rem Ekran postepu: krok asyst, czyste okrazenia z rzedu, najlepsze czasy, zakrety opanowane (z bazy data\boxbox.sqlite).
cd /d "%~dp0"
if not exist "boxbox\app.py" cd /d "%~dp0..\.."
rem (skrypt dziala z paczki ZIP albo z tools\package w klonie repozytorium)
py -3 -m boxbox.app --progress
pause
