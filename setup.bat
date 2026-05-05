@echo off
echo === Wispr Clone Setup ===

python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Install Python 3.10+ from https://python.org
    pause
    exit /b 1
)

echo Creating virtual environment...
python -m venv venv

echo Activating venv and installing dependencies...
call venv\Scripts\activate.bat
pip install --upgrade pip
pip install -r requirements.txt

echo.
echo Setup complete!
echo.
echo Next steps:
echo   1. Copy .env.example to .env and add your ANTHROPIC_API_KEY
echo   2. Run:  venv\Scripts\activate  ^&^&  python main.py
echo.
pause
