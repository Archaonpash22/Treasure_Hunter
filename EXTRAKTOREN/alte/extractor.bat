@echo off
REM Diese Batch-Datei startet den GUI Wikipedia Extraktor.
REM Stellen Sie sicher, dass Python installiert und im PATH verfügbar ist.
REM Stellen Sie außerdem sicher, dass die PyQt6- und requests-Bibliotheken installiert sind (pip install PyQt6 requests).
REM Benennen Sie diese Datei als z.B. 'start_gui_extractor.bat' und legen Sie sie im selben Verzeichnis ab wie 'gui_extractor.py'.

REM Der Name Ihres Python-GUI-Extraktor-Skripts
SET PYTHON_GUI_SCRIPT=gui_extractor.py

REM Überprüfen, ob das Python-Skript existiert
IF NOT EXIST "%PYTHON_GUI_SCRIPT%" (
    echo Fehler: Das Python-Skript "%PYTHON_GUI_SCRIPT%" wurde nicht gefunden.
    echo Bitte stellen Sie sicher, dass die Datei im selben Verzeichnis liegt und korrekt benannt ist.
    pause
    EXIT /B 1
)

echo Starte den GUI Wikipedia Extraktor...
echo.

REM Startet das Python-Skript, das die GUI öffnet
python "%PYTHON_GUI_SCRIPT%"

echo GUI Extraktor wurde geschlossen.
pause
