Um den wikidata_gui_extractor.py einfach auszuführen, können Sie eine Batch-Datei (mit der Endung .bat) erstellen.

Inhalt der run_extractor.bat Datei (aktualisiert, um die Konsole offen zu halten und Fehler zu protokollieren):

@echo off
echo Starte Wikidata GUI Extraktor...
echo.

REM Setzt den aktuellen Ordner als Arbeitsverzeichnis
cd /d "%~dp0"
if %errorlevel% neq 0 (
    echo FEHLER: Konnte nicht in den Ordner der Batch-Datei wechseln. Stellen Sie sicher, dass der Pfad gueltig ist.
    goto :end
)

echo Versuche, Python-Version zu ueberpruefen...
python --version > console_output.log 2>&1
if %errorlevel% neq 0 (
    echo.
    echo FEHLER: 'python' Befehl nicht gefunden oder Python nicht im PATH.
    echo Die Ausgabe wurde in 'console_output.log' gespeichert.
    echo.
    echo Alternativer Versuch: Starte mit 'py' Launcher (wenn Python 3 installiert ist)...
    REM Der 'cmd /k' Befehl haelt das Konsolenfenster offen, auch wenn der Befehl fehlschlaegt.
    start "Wikidata Extractor" cmd /k py -3 wikidata_gui_extractor.py
    if %errorlevel% neq 0 (
        echo.
        echo FEHLER: 'py' Befehl ebenfalls nicht gefunden oder Skript konnte nicht gestartet werden.
        echo Bitte ueberpruefen Sie den Dateinamen (wikidata_gui_extractor.py) und ob er im selben Ordner ist.
        echo.
        echo Letzter Versuch: Starte mit explizitem Pfad (falls Python in Standardpfad installiert ist)...
        REM Diesen Pfad muessen Sie moeglicherweise anpassen, z.B. Python39, Python310, etc.
        start "Wikidata Extractor" cmd /k "C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python310\python.exe" wikidata_gui_extractor.py
        echo (Bitte ersetzen Sie 'Python310' durch Ihre tatsaechliche Python-Version, z.B. Python39, Python311, etc.)
        echo.
        echo Wenn keiner der Versuche funktioniert, muessen Sie moeglicherweise Python neu installieren
        echo und sicherstellen, dass die Option "Add Python to PATH" waehrend der Installation aktiviert ist.
    )
) else (
    echo.
    echo 'python' Befehl gefunden. Starte Extraktor...
    REM Der 'cmd /k' Befehl haelt das Konsolenfenster offen, auch wenn der Befehl fehlschlaegt.
    start "Wikidata Extractor" cmd /k python wikidata_gui_extractor.py
)

:end
echo.
echo Skriptausfuehrung beendet. Bitte ueberpruefen Sie die obigen Meldungen auf Fehler.
echo Wenn sich ein neues Fenster geoeffnet hat, schauen Sie dort nach Fehlern.
echo Druecken Sie eine beliebige Taste, um dieses Konsolenfenster zu schliessen...
pause

Wichtige Änderungen und Anleitung:

start "Wikidata Extractor" cmd /k ...: Dies ist die wichtigste Änderung. Anstatt den Python-Befehl direkt auszuführen, verwenden wir start cmd /k. Dies öffnet ein neues Konsolenfenster und führt den Befehl darin aus. Das cmd /k sorgt dafür, dass dieses neue Fenster offen bleibt, nachdem der Befehl ausgeführt wurde, egal ob er erfolgreich war oder nicht. So können Sie die Fehlermeldungen sehen.

> console_output.log 2>&1: Die Ausgabe des python --version-Befehls wird jetzt in die Datei console_output.log umgeleitet. Das ist ein Fallback, falls das Fenster zu schnell schließt oder Sie die Ausgabe später überprüfen möchten.

cd /d "%~dp0" Fehlerprüfung: Eine kleine Fehlerprüfung wurde hinzugefügt, falls der cd Befehl fehlschlägt.

Bitte versuchen Sie es erneut mit diesen Schritten:

Speichern Sie die aktualisierte run_extractor.bat im selben Ordner wie Ihre wikidata_gui_extractor.py-Datei.

Doppelklicken Sie auf run_extractor.bat.

Beobachten Sie:

Ein neues Konsolenfenster sollte sich öffnen. Dieses Fenster sollte offen bleiben.

Schauen Sie in diesem neuen Fenster nach Fehlermeldungen.

Überprüfen Sie auch, ob eine Datei namens console_output.log in Ihrem Ordner erstellt wurde und was darin steht.

Die Fehlermeldungen in diesem neuen Fenster oder in der Log-Datei sind entscheidend, um das Problem zu identifizieren. Bitte teilen Sie mir genau mit, was in diesem Fenster oder in der Log-Datei steht.