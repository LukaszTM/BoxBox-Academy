@echo off
rem Trener na zywo z glosem mechanika i nakladka na gre. Uzycie: trener.bat [nazwa nagrania]
rem   trener.bat monza partia1        -> nagranie monza-partia1 w recordings\, nakladka wlaczona
rem   Bez nakladki: ustaw NAKLADKA=0 ponizej. Wieksze napisy: SKALA=1.3.
rem Gra: telemetria UDP wlaczona (port 20777), tryb okna bez ramki (nakladka musi byc widoczna).
rem Nie uruchamiaj jednoczesnie nakladka.bat ani nagraj.bat (jeden program na port UDP).
rem Zakonczenie: Esc na nakladce albo Ctrl+C w terminalu -> tabela zakretow, postep i obciazenie CPU.
cd /d "%~dp0"
set "NAZWA=%*"
if "%NAZWA%"=="" set "NAZWA=sesja"
set "NAZWA=%NAZWA: =-%"
set VOLUME=1.5
set NAKLADKA=1
set SKALA=1.0
set OPCJE=
if "%NAKLADKA%"=="1" set OPCJE=--overlay --scale %SKALA%
py -3 -m boxbox.app --mode coach --record %NAZWA% --volume %VOLUME% %OPCJE%
echo.
py -3 -m boxbox.app --progress
pause
