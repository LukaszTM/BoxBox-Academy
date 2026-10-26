@echo off
rem Trener na zywo z glosem mechanika. Uzycie: trener.bat [nazwa nagrania]
rem Gra: telemetria UDP wlaczona (port 20777). Nie uruchamiaj jednoczesnie nakladka.bat ani nagraj.bat (jeden port UDP).
rem Zatrzymanie: Ctrl+C w terminalu -> tabela zakretow i obciazenie CPU.
cd /d "%~dp0"
set "NAZWA=%*"
if "%NAZWA%"=="" set "NAZWA=sesja"
set "NAZWA=%NAZWA: =-%"
py -3 -m boxbox.app --mode coach --record %NAZWA%
