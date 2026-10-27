@echo off
rem Ekran postepu: krok asyst, czyste okrazenia z rzedu, najlepsze czasy, zakrety opanowane (z bazy data\boxbox.sqlite).
cd /d "%~dp0"
py -3 -m boxbox.app --progress
pause
