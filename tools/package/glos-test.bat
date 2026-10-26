@echo off
rem Test glosnikow bez gry: odtwarza powitanie mechanika.
cd /d "%~dp0"
py -3 -m boxbox.voice.player assets\voice misc_hello corner_t4 rule_brake_late_a num_50 rule_brake_late_b
pause
