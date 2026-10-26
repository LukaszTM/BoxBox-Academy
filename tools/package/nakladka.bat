@echo off
rem Nakladka na gre + nagrywanie. Uzycie: nakladka.bat <nazwa-nagrania> <plan>
rem   np. nakladka.bat bahrajn-tt bahrajn-tt      (plany: bahrajn-tt, monza-trening, suzuka-tt-bez-tc, pakiet2026)
rem Gra musi byc w trybie okna bez ramki (Ustawienia graficzne -> Tryb okna), nie w pelnym ekranie.
if "%~2"=="" (
  echo Uzycie: nakladka.bat ^<nazwa-nagrania^> ^<plan^>   np. nakladka.bat bahrajn-tt bahrajn-tt
  echo Plany: bahrajn-tt, monza-trening, suzuka-tt-bez-tc, pakiet2026
  exit /b 1
)
cd /d "%~dp0"
py -3 -m boxbox.ui.overlay --name %1 --plan "plany\%2.json"
