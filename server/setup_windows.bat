@echo off
echo ============================================
echo  Murmur Whisper Server - Windows Setup
echo ============================================
echo.

cd /d "%~dp0"

echo Aanmaken van virtual environment...
python -m venv venv
if errorlevel 1 (
    echo FOUT: Python niet gevonden. Installeer Python 3.11+ en voeg toe aan PATH.
    pause
    exit /b 1
)

echo Installeren van dependencies...
venv\Scripts\pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo FOUT: pip install mislukt.
    pause
    exit /b 1
)

echo.
if not exist .env (
    copy .env.example .env
    echo .env aangemaakt. Open .env en vul je MURMUR_API_KEY in.
) else (
    echo .env bestaat al.
)

echo.
echo Setup voltooid!
echo Vergeet niet je .env in te vullen voor je de server start.
pause
