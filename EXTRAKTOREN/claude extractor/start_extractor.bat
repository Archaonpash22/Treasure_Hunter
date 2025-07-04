@echo off
echo ========================================
echo   Treasure Hunter Data Extractor
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python from https://www.python.org/
    pause
    exit /b 1
)

REM Check if virtual environment exists
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Install/upgrade pip
echo Updating pip...
python -m pip install --upgrade pip

REM Install requirements
echo Installing required packages...
pip install -r requirements.txt

REM Run the application
echo.
echo Starting Treasure Hunter Data Extractor...
echo ========================================
python treasure_data_extractor.py

REM Keep window open if there's an error
if errorlevel 1 (
    echo.
    echo Application exited with an error.
    pause
)

deactivate