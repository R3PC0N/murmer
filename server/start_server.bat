@echo off
cd /d "%~dp0"

if not exist venv\Scripts\python.exe (
    echo Venv niet gevonden. Voer eerst setup_windows.bat uit.
    pause
    exit /b 1
)

echo Murmur Whisper Server starten...
venv\Scripts\python.exe faster_whisper_server.py
