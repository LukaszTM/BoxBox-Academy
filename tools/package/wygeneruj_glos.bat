@echo off
rem Generuje brakujace klipy glosu mechanika i inzyniera przez ElevenLabs (jednorazowo),
rem potem naklada efekt radia. Wynik: assets\voice\*.wav (surowe w assets\voice\raw).
rem Klipy, ktore juz sa w assets\voice, sa pomijane (nie zuzywaja znakow).
rem Potrzebne: klucz API (ElevenLabs -> profil -> API keys) i ID glosu (Voices -> glos -> "Copy voice ID").
rem Klucza nie wpisuj do zadnego pliku ani nie wklejaj na czacie.
cd /d "%~dp0"
if "%ELEVENLABS_API_KEY%"=="" set /p ELEVENLABS_API_KEY=Klucz API ElevenLabs: 
if "%ELEVENLABS_VOICE_ID%"=="" set /p ELEVENLABS_VOICE_ID=ID glosu (np. Piotr - Neutral and Mature): 
py -3 wygeneruj_glos.py phrases.csv assets\voice\raw --done-dir assets\voice --dry-run
echo.
set /p ODP=Generowac? (t/n): 
if /i not "%ODP%"=="t" exit /b 0
py -3 wygeneruj_glos.py phrases.csv assets\voice\raw --done-dir assets\voice
if errorlevel 1 (
  echo Generowanie przerwane bledem. Uruchom ponownie, wygenerowane klipy zostana pominiete.
  pause
  exit /b 1
)
echo.
echo Efekt radia...
py -3 -m boxbox.voice.radio assets\voice\raw assets\voice --skip-existing
echo.
echo Gotowe. Spakuj folder assets\voice\raw do ZIP i przeslij (zeby klipy trafily do repozytorium).
pause
