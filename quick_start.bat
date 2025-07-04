@echo off
echo Slouching Detector - Quick Launch
echo =================================

REM Change to the script directory
cd /d "%~dp0"

REM Check if virtual environment exists
if not exist ".venv" (
    echo  Virtual environment not found!
    echo Please run setup first using start.bat
    pause
    exit /b 1
)

REM Check if .env file exists
if not exist ".env" (
    echo  Configuration file not found!
    echo Please run setup first using start.bat
    pause
    exit /b 1
)

echo  Environment ready - Launching GUI...
.venv\Scripts\python.exe gui_app.py

if %errorlevel% neq 0 (
    echo  Application encountered an error
    echo Check the console output above for details
    pause
    exit /b 1
)

echo  Application closed successfully
