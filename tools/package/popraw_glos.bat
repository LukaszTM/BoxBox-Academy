@echo off
rem Poprawka wymowy: ElevenLabs czyta koncowke "-uj" jako "-uc" (hamuj -> hamuc).
rem Te zdania dostaly nowe brzmienie; skrypt kasuje stare klipy i generuje je ponownie (8 klipow, ok. 500 znakow).
cd /d "%~dp0"
for %%k in (misc_step_abs_off misc_step_tc_off eng_rain_now eng_gap_behind_close eng_pit_next_lap eng_rain_coming eng_gap_ahead_close misc_no_reference) do (
  del /q "assets\voice\raw\%%k.wav" 2>nul
  del /q "assets\voice\%%k.wav" 2>nul
)
call wygeneruj_glos.bat
