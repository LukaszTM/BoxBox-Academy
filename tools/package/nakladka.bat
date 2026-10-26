@echo off
rem Nakladka na gre + nagrywanie. Uzycie: nakladka.bat <nazwa nagrania, moze byc kilka slow>
rem   np. nakladka.bat monza trening z AI   -> nagranie monza-trening-z-AI, plan dobrany po slowie "monza"
rem   Plan recznie: nakladka.bat --plan suzuka-tt-bez-tc suzuka proba 2
rem   Plany: bahrajn-tt, monza-trening, suzuka-tt-bez-tc, pakiet2026
rem Gra musi byc w trybie okna bez ramki (Ustawienia graficzne -> Tryb okna), nie w pelnym ekranie.
if "%~1"=="" (
  echo Uzycie: nakladka.bat ^<nazwa nagrania^>   np. nakladka.bat monza trening
  echo Plany: bahrajn-tt, monza-trening, suzuka-tt-bez-tc, pakiet2026
  exit /b 1
)
cd /d "%~dp0"
if /i "%~1"=="--plan" (
  py -3 -m boxbox.ui.overlay --plan %2 --name %3 %4 %5 %6 %7 %8 %9
) else (
  py -3 -m boxbox.ui.overlay --name %*
)
