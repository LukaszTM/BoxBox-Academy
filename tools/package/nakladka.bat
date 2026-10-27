@echo off
rem Nakladka na gre + nagrywanie. Uzycie: nakladka.bat <nazwa nagrania, moze byc kilka slow>
rem   np. nakladka.bat monza trening z AI   -> nagranie monza-trening-z-AI, plan dobrany po slowie "monza"
rem   Plan recznie: nakladka.bat --plan suzuka-tt-bez-tc suzuka proba 2
rem   Plany: bahrajn-tt, monza-trening, suzuka-tt-bez-tc, pakiet2026
rem   Wieksze napisy: ustaw ponizej SKALA (np. 1.3); bez przezroczystosci: ALPHA=1.0
rem Gra musi byc w trybie okna bez ramki (Ustawienia graficzne -> Tryb okna), nie w pelnym ekranie.
if "%~1"=="" (
  echo Uzycie: nakladka.bat ^<nazwa nagrania^>   np. nakladka.bat monza trening
  echo Plany: bahrajn-tt, monza-trening, suzuka-tt-bez-tc, pakiet2026
  exit /b 1
)
cd /d "%~dp0"
if not exist "boxbox\app.py" cd /d "%~dp0..\.."
rem (skrypt dziala z paczki ZIP albo z tools\package w klonie repozytorium)
set SKALA=1.0
set ALPHA=0.97
if /i "%~1"=="--plan" (
  py -3 -m boxbox.ui.overlay --scale %SKALA% --alpha %ALPHA% --plan %2 --name %3 %4 %5 %6 %7 %8 %9
) else (
  py -3 -m boxbox.ui.overlay --scale %SKALA% --alpha %ALPHA% --name %*
)
