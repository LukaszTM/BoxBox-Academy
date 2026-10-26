@echo off
rem Generuje klipy glosu mechanika przez ElevenLabs (jednorazowo). Wynik: assets\voice\raw\*.wav
rem Potrzebne: klucz API (ElevenLabs -> profil -> API keys) i ID glosu (Voices -> glos -> ID / "Copy voice ID").
cd /d "%~dp0"
if "%ELEVENLABS_API_KEY%"=="" set /p ELEVENLABS_API_KEY=Klucz API ElevenLabs: 
if "%ELEVENLABS_VOICE_ID%"=="" set /p ELEVENLABS_VOICE_ID=ID glosu (np. Piotr - Neutral and Mature): 
py -3 wygeneruj_glos.py phrases.csv assets\voice\raw --dry-run
echo.
set /p ODP=Generowac? (t/n): 
if /i not "%ODP%"=="t" exit /b 0
py -3 wygeneruj_glos.py phrases.csv assets\voice\raw
echo.
echo Gotowe. Spakuj folder assets\voice\raw do ZIP i przeslij.
pause
