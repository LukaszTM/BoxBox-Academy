@echo off
rem Test glosnikow bez gry: odtwarza powitanie mechanika.
cd /d "%~dp0"
if not exist "boxbox\app.py" cd /d "%~dp0..\.."
rem (skrypt dziala z paczki ZIP albo z tools\package w klonie repozytorium)
py -3 -m boxbox.voice.player assets\voice misc_hello corner_t4 rule_brake_late_a num_50 rule_brake_late_b
pause
