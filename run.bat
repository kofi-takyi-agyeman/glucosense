@echo off
title GlucoSense — Local Server
echo.
echo  ==========================================
echo   GlucoSense — Starting Backend Server
echo  ==========================================
echo.

cd /d "%~dp0backend"

:: Check Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Python not found. Install Python 3.10+ from https://python.org
    pause
    exit /b 1
)

:: Install dependencies
echo  [1/3] Installing dependencies...
pip install --upgrade -r requirements.txt --quiet

:: Train model if model.pkl is missing or if train flag passed
if not exist "model.pkl" (
    echo  [2/3] model.pkl not found — training model now...
    python train_model.py
) else (
    echo  [2/3] model.pkl found — skipping training.
    echo        ^(Run "python train_model.py" to retrain manually^)
)

:: Start Flask
echo  [3/3] Starting Flask on http://localhost:5000
echo.
echo  Open your browser to:
echo    http://localhost:5000  ^(API^)
echo.
echo  Then open the frontend manually:
echo    %~dp0frontend\pages\login.html
echo.
echo  Press Ctrl+C to stop the server.
echo.
python app.py
pause
