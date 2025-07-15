@echo off
REM This batch file installs the required Python packages and runs the GitHub Uploader application.

ECHO Installing dependencies from requirements.txt...
pip install -r requirements.txt

ECHO.
ECHO Launching the GitHub Uploader...
python github_uploader.py

REM The 'pause' command keeps the window open after the script exits,
REM so you can see any final messages or errors.
pause
