@echo off
title Treasure Hunter App Starter
color 0A

REM ============================================================================
REM  Start-Skript fuer die Treasure Hunter App (Version 2)
REM  - Wechselt automatisch in das korrekte Verzeichnis
REM  - Erstellt eine virtuelle Umgebung (falls nicht vorhanden)
REM  - Installiert die benoetigten Pakete aus requirements.txt
REM  - Startet die Anwendung
REM ============================================================================

echo --- Treasure Hunter App Start-Skript ---
echo.

REM WICHTIG: Wechsle in das Verzeichnis, in dem dieses Skript liegt.
REM Dies stellt sicher, dass alle Dateien (main.py, requirements.txt) gefunden werden.
cd /d "%~dp0"
echo Arbeitsverzeichnis: %cd%
echo.

REM Ueberpruefen, ob Python installiert ist und im PATH ist.
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [FEHLER] Python wurde nicht gefunden.
    echo Bitte installieren Sie Python von https://www.python.org/downloads/
    echo WICHTIG: Waehlen Sie bei der Installation die Option "Add Python to PATH".
    echo.
    pause
    exit /b
)
echo Python-Installation gefunden.
echo.

REM Name des Ordners fuer die virtuelle Umgebung
set VENV_DIR=.venv

REM Ueberpruefen, ob die virtuelle Umgebung bereits existiert
if not exist "%VENV_DIR%\Scripts\activate.bat" (
    echo Erstelle eine neue virtuelle Umgebung in '%VENV_DIR%'. Das kann einen Moment dauern...
    python -m venv %VENV_DIR%
    if %errorlevel% neq 0 (
        echo [FEHLER] Die virtuelle Umgebung konnte nicht erstellt werden.
        pause
        exit /b
    )
    echo Virtuelle Umgebung erfolgreich erstellt.
) else (
    echo Vorhandene virtuelle Umgebung wird verwendet.
)
echo.

REM Aktiviere die virtuelle Umgebung
echo Aktiviere die virtuelle Umgebung...
call "%VENV_DIR%\Scripts\activate.bat"
echo.

REM Installiere die Abhaengigkeiten aus der requirements.txt Datei
echo Installiere oder aktualisiere die Abhaengigkeiten...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [FEHLER] Die Abhaengigkeiten aus requirements.txt konnten nicht installiert werden.
    echo Ueberpruefen Sie Ihre Internetverbindung und die Datei 'requirements.txt'.
    echo.
    pause
    exit /b
)
echo Abhaengigkeiten sind auf dem neuesten Stand.
echo.

REM Starte die Python-Anwendung
echo --- Starte die Treasure Hunter App ---
python main.py
echo.

REM Deaktiviere die virtuelle Umgebung (wird ausgefuehrt, nachdem das App-Fenster geschlossen wurde)
echo Deaktiviere die virtuelle Umgebung...
call "%VENV_DIR%\Scripts\deactivate.bat"

echo.
echo Die Anwendung wurde beendet. Druecken Sie eine beliebige Taste zum Schliessen.
pause >nul
