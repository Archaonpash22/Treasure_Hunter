import sys
import requests
import json
import os
import traceback # Für detaillierte Fehlerprotokollierung
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QLabel, QProgressBar, QTextEdit, QMessageBox,
    QFormLayout, QComboBox, QDialog, QDialogButtonBox # QDialog für Debug-Fenster
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QObject, QCoreApplication # QCoreApplication für processEvents

# --- Extraktionslogik (aus generischer_extractor.py übernommen und angepasst) ---

class WikipediaExtractorWorker(QObject):
    """
    Die Worker-Klasse, die die eigentliche Extraktionslogik enthält.
    Sie läuft in einem separaten QThread und sendet Signale an die GUI.
    """
    progress_update = pyqtSignal(int, str)
    extraction_finished = pyqtSignal(list, str, str)
    extraction_error = pyqtSignal(str)

    def __init__(self, kultur: str, siedlungstyp_fuer_dateiname: str, suchbegriffe: list[str]):
        super().__init__()
        self.kultur = kultur
        self.siedlungstyp_fuer_dateiname = siedlungstyp_fuer_dateiname
        self.suchbegriffe = suchbegriffe
        self.URL = "https://de.wikipedia.org/w/api.php"
        self.session = requests.Session()

    def do_extraction(self):
        """
        Führt die Wikipedia-API-Aufrufe und die Datenextraktion durch.
        Diese Methode wird vom QThread aufgerufen.
        """
        try:
            self.progress_update.emit(0, "Starte Suche auf Wikipedia...")
            
            srsearch_query = " ODER ".join([f"{self.kultur.lower()} {term}" for term in self.suchbegriffe])
            
            SEARCH_PARAMS = {
                "action": "query",
                "format": "json",
                "list": "search",
                "srsearch": srsearch_query,
                "srlimit": 50,
                "srsort": "relevance",
                "srwhat": "text"
            }

            search_response = self.session.get(url=self.URL, params=SEARCH_PARAMS)
            search_data = search_response.json()

            page_titles = []
            if "query" in search_data and "search" in search_data["query"]:
                for item in search_data["query"]["search"]:
                    page_titles.append(item["title"])
                self.progress_update.emit(5, f"Es wurden {len(page_titles)} potenzielle Seiten gefunden.")
            else:
                self.progress_update.emit(100, "Keine Suchergebnisse gefunden oder unerwartete API-Antwort.")
                self.extraction_finished.emit([], self.kultur, self.siedlungstyp_fuer_dateiname)
                return

            extrahierte_siedlungen = []
            batch_size = 10
            total_pages = len(page_titles)

            for i in range(0, total_pages, batch_size):
                batch_titles = page_titles[i:i + batch_size]
                titles_str = "|".join(batch_titles)

                DETAIL_PARAMS = {
                    "action": "query",
                    "format": "json",
                    "prop": "extracts|coordinates|info",
                    "exintro": True,
                    "explaintext": True,
                    "inprop": "url",
                    "titles": titles_str,
                    "colimit": "max"
                }

                self.progress_update.emit(
                    5 + int(90 * (i / total_pages)),
                    f"Rufe Details für Batch {i//batch_size + 1}/{total_pages//batch_size + (1 if total_pages % batch_size else 0)} ab..."
                )
                
                detail_response = self.session.get(url=self.URL, params=DETAIL_PARAMS)
                detail_data = detail_response.json()

                if "query" in detail_data and "pages" in detail_data["query"]:
                    for page_id, page_info in detail_data["query"]["pages"].items():
                        if page_id == "-1":
                            continue

                        siedlung = {
                            "name": page_info.get("title"),
                            "zusammenfassung": page_info.get("extract"),
                            "url": page_info.get("fullurl"),
                            "lat": None,
                            "lon": None
                        }

                        if "coordinates" in page_info and page_info["coordinates"]:
                            siedlung["lat"] = page_info["coordinates"][0].get("lat")
                            siedlung["lon"] = page_info["coordinates"][0].get("lon")
                        
                        if siedlung["name"] and siedlung["zusammenfassung"] and (siedlung["lat"] is not None):
                            extrahierte_siedlungen.append(siedlung)
                        else:
                            pass
            
            # Entfernt: QCoreApplication.processEvents() hier, da es in Worker-Threads oft Probleme verursachen kann.
            # Die QueuedConnection sollte ausreichend sein, um das Signal sicher zu übermitteln.

            self.progress_update.emit(100, "Extraktion abgeschlossen.")
            # WICHTIG: emit() des Signals muss immer aufgerufen werden, auch wenn die GUI-Slots nicht mehr verbunden sind.
            # Der Fehler tritt auf, wenn das C++-Objekt unter dem Python-Signal bereits ungültig ist.
            self.extraction_finished.emit(extrahierte_siedlungen, self.kultur, self.siedlungstyp_fuer_dateiname)

        except requests.exceptions.RequestException as e:
            self.extraction_error.emit(f"Netzwerkfehler oder API-Problem: {e}")
            self.progress_update.emit(0, "Fehler: Netzwerkproblem.")
        except Exception as e:
            # Sende den vollständigen Traceback bei einem unerwarteten Fehler
            self.extraction_error.emit(f"Ein unerwarteter Fehler ist aufgetreten: {e}\n{traceback.format_exc()}")
            self.progress_update.emit(0, "Fehler: Unerwarteter Fehler.")

# --- Debug-Fenster ---

class DebugWindow(QDialog):
    """
    Ein separates Fenster zur Anzeige detaillierter Debug-Informationen.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Debug-Konsole")
        self.setGeometry(200, 200, 700, 500) # Größer für mehr Details

        layout = QVBoxLayout(self)
        self.log_display = QTextEdit()
        self.log_display.setReadOnly(True)
        self.log_display.setFontPointSize(9) # Kleinere Schrift für mehr Inhalt
        layout.addWidget(self.log_display)

        # Optional: Button zum Leeren der Konsole
        clear_button = QPushButton("Log leeren")
        clear_button.clicked.connect(self.log_display.clear)
        layout.addWidget(clear_button)

    def log_message(self, message: str):
        """Fügt eine Nachricht zur Debug-Konsole hinzu."""
        self.log_display.append(message)
        self.log_display.verticalScrollBar().setValue(self.log_display.verticalScrollBar().maximum())

# --- GUI-Anwendung ---

class ExtractorGUI(QWidget):
    """
    Die Haupt-GUI-Anwendung für den Wikipedia-Extraktor.
    """
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Wikipedia Siedlungs-Extraktor")
        self.setGeometry(100, 100, 600, 450)

        self.extractor_thread = None
        self.extractor_worker = None # Referenz auf den Worker

        self.debug_window = DebugWindow(self) # Instanz des Debug-Fensters
        # Verbinde die aboutToQuit-Signal der Anwendung, um das Debug-Fenster zu schließen
        QApplication.instance().aboutToQuit.connect(self.debug_window.close)

        # NEU: Umleitung von sys.excepthook für unhandled Exceptions
        self._original_excepthook = sys.excepthook
        sys.excepthook = self._custom_excepthook

        self.init_ui()
        self.add_log("Anwendung gestartet. Debug-Fenster ist bereit.")


    def _custom_excepthook(self, exc_type, exc_value, exc_traceback):
        """
        Benutzerdefinierter Exception-Hook, der unhandled Exceptions abfängt
        und in die Log-Konsolen schreibt.
        """
        if issubclass(exc_type, KeyboardInterrupt):
            # Standardbehandlung für KeyboardInterrupt (z.B. Ctrl+C)
            self._original_excepthook(exc_type, exc_value, exc_traceback)
            return

        error_message = f"Unhandled Exception: {exc_type.__name__}: {exc_value}\n"
        error_message += "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        
        self.add_log(f"FEHLER (Unhandled): {error_message}")
        QMessageBox.critical(self, "Unerwarteter Fehler", "Ein unerwarteter Fehler ist aufgetreten. Details finden Sie in der Debug-Konsole.")
        
        # Sicherstellen, dass der Start-Button wieder aktiviert wird
        self.start_button.setEnabled(True)
        # Referenzen bereinigen, falls der Fehler im Thread auftrat
        # Diese Bereinigung sollte nun über _on_thread_fully_finished erfolgen,
        # aber als Fallback hier belassen, falls der Fehler vor der Thread-Beendigung auftritt.
        self.extractor_worker = None
        self.extractor_thread = None

        # Optional: Original-Hook aufrufen, um das Standardverhalten beizubehalten (z.B. Programm beenden)
        # self._original_excepthook(exc_type, exc_value, exc_traceback)


    def init_ui(self):
        """
        Initialisiert die Benutzeroberfläche der Anwendung.
        """
        main_layout = QVBoxLayout(self)

        input_form_layout = QFormLayout()
        
        self.kultur_input = QLineEdit()
        self.kultur_input.setPlaceholderText("z.B. Kelten, Römer, Mittelalter")
        input_form_layout.addRow("Kultur:", self.kultur_input)

        self.typ_selector = QComboBox()
        self.typ_selector.addItems(["Siedlung", "Schatz", "Münze", "Kastell", "Burg", "Bunker", "Allgemein"])
        self.typ_selector.currentTextChanged.connect(self.update_suchbegriffe_suggestion)
        input_form_layout.addRow("Typ:", self.typ_selector)

        self.suchbegriffe_input = QLineEdit()
        self.suchbegriffe_input.setPlaceholderText("Zusätzliche Suchbegriffe (Komma-separiert)")
        input_form_layout.addRow("Zusätzliche Suchbegriffe:", self.suchbegriffe_input)

        main_layout.addLayout(input_form_layout)

        self.start_button = QPushButton("Extraktion starten")
        self.start_button.clicked.connect(self.start_extraction)
        main_layout.addWidget(self.start_button)

        # NEU: Button zum Öffnen des Debug-Fensters
        self.debug_button = QPushButton("Debug-Fenster öffnen")
        self.debug_button.clicked.connect(self.debug_window.show)
        main_layout.addWidget(self.debug_button)

        self.progress_bar = QProgressBar(self)
        self.progress_bar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(self.progress_bar)

        self.log_console = QTextEdit()
        self.log_console.setReadOnly(True)
        self.log_console.setFixedHeight(150)
        main_layout.addWidget(self.log_console)

        example_label = QLabel("Beispiele:")
        main_layout.addWidget(example_label)

        examples_layout = QHBoxLayout()
        example_button_kelten_siedlung = QPushButton("Kelten Siedlung")
        example_button_kelten_siedlung.clicked.connect(lambda: self.load_example("Kelten", "Siedlung", "Oppidum, Festung"))
        examples_layout.addWidget(example_button_kelten_siedlung)

        example_button_roemer_kastell = QPushButton("Römer Kastell")
        example_button_roemer_kastell.clicked.connect(lambda: self.load_example("Römer", "Kastell", "Legionslager, Militärlager"))
        examples_layout.addWidget(example_button_roemer_kastell)

        example_button_ww2_bunker = QPushButton("WW2 Bunker (DE)")
        example_button_ww2_bunker.clicked.connect(lambda: self.load_example("Zweiter Weltkrieg", "Bunker", "Verteidigungsanlage"))
        examples_layout.addWidget(example_button_ww2_bunker)

        main_layout.addLayout(examples_layout)

        self.add_log("Bereit zur Extraktion. Geben Sie Kriterien ein oder wählen Sie ein Beispiel.")
        self.update_suchbegriffe_suggestion(self.typ_selector.currentText())

    def update_suchbegriffe_suggestion(self, selected_typ: str):
        """
        Aktualisiert die Vorschläge für zusätzliche Suchbegriffe basierend auf dem ausgewählten Typ.
        """
        suggestions = {
            "Siedlung": "Siedlung, Oppidum, Dorf, Stadt",
            "Schatz": "Schatzfund, Hortfund, Depotfund",
            "Münze": "Münzfund, Münzschatz",
            "Kastell": "Kastell, Legionslager, Militärlager",
            "Burg": "Burg, Festung, Schloss",
            "Bunker": "Bunker, Verteidigungsanlage",
            "Allgemein": ""
        }
        self.suchbegriffe_input.setText(suggestions.get(selected_typ, ""))
        self.suchbegriffe_input.setPlaceholderText(f"Zusätzliche Suchbegriffe (Komma-separiert, z.B. {suggestions.get(selected_typ, '')})")

    def load_example(self, kultur, typ_value, additional_suchbegriffe_str):
        """Lädt Beispielwerte in die Eingabefelder."""
        self.kultur_input.setText(kultur)
        self.typ_selector.setCurrentText(typ_value)
        self.suchbegriffe_input.setText(additional_suchbegriffe_str)
        self.add_log(f"Beispiel '{kultur} {typ_value}' geladen.")

    def add_log(self, message: str):
        """
        Fügt eine Nachricht zur Haupt-Log-Konsole und zur Debug-Konsole hinzu.
        """
        self.log_console.append(message)
        self.log_console.verticalScrollBar().setValue(self.log_console.verticalScrollBar().maximum())
        self.debug_window.log_message(f"[{QThread.currentThread().objectName() or 'MainThread'}] {message}")


    def start_extraction(self):
        """
        Startet den Extraktionsprozess in einem separaten Thread.
        Validiert die Eingaben und initialisiert den Thread und den Worker.
        """
        kultur = self.kultur_input.text().strip()
        selected_typ = self.typ_selector.currentText().strip()
        zus_suchbegriffe_str = self.suchbegriffe_input.text().strip()

        if not kultur or not selected_typ:
            QMessageBox.warning(self, "Eingabefehler", "Bitte füllen Sie die Felder 'Kultur' und 'Typ' aus.")
            return

        base_suchbegriffe = []
        if selected_typ == "Siedlung":
            base_suchbegriffe = ["Siedlung", "Oppidum", "Dorf"]
        elif selected_typ == "Schatz":
            base_suchbegriffe = ["Schatzfund", "Hortfund"]
        elif selected_typ == "Münze":
            base_suchbegriffe = ["Münzfund", "Münzschatz"]
        elif selected_typ == "Kastell":
            base_suchbegriffe = ["Kastell", "Legionslager", "Militärlager"]
        elif selected_typ == "Burg":
            base_suchbegriffe = ["Burg", "Festung", "Schloss"]
        elif selected_typ == "Bunker":
            base_suchbegriffe = ["Bunker", "Verteidigungsanlage"]
        elif selected_typ == "Allgemein":
            base_suchbegriffe = []

        suchbegriffe = base_suchbegriffe
        if zus_suchbegriffe_str:
            suchbegriffe.extend([s.strip() for s in zus_suchbegriffe_str.split(',') if s.strip()])
        
        if not suchbegriffe:
            QMessageBox.warning(self, "Eingabefehler", "Bitte geben Sie mindestens einen Suchbegriff ein oder wählen Sie einen Typ, der Basis-Suchbegriffe generiert.")
            return

        siedlungstyp_fuer_dateiname = selected_typ.replace(" ", "_").lower()

        self.start_button.setEnabled(False)
        self.progress_bar.setValue(0)
        self.add_log(f"Starte Extraktion für: Kultur='{kultur}', Typ='{selected_typ}', Suchbegriffe='{', '.join(suchbegriffe)}'")

        # Erstelle Worker und Thread
        self.extractor_thread = QThread()
        self.extractor_thread.setObjectName("ExtractorThread") # Thread benennen für Debugging
        self.extractor_worker = WikipediaExtractorWorker(kultur, siedlungstyp_fuer_dateiname, suchbegriffe)
        self.extractor_worker.setObjectName("ExtractorWorker") # Worker benennen für Debugging
        
        # NEU: Überprüfen und Entfernen des Parents vor dem Verschieben
        # Dies sollte sicherstellen, dass der Worker keinen Parent hat, der im GUI-Thread lebt.
        if self.extractor_worker.parent() is not None:
            self.add_log(f"DEBUG: Worker hat unerwarteten Parent {self.extractor_worker.parent().objectName()} vor dem Verschieben. Setze auf None.")
            self.extractor_worker.setParent(None)

        self.add_log(f"DEBUG: Worker Parent vor moveToThread: {self.extractor_worker.parent()}")
        self.add_log(f"DEBUG: Worker Thread vor moveToThread: {self.extractor_worker.thread()}")
        
        # Verschiebe den Worker in den Thread
        self.extractor_worker.moveToThread(self.extractor_thread)
        
        self.add_log(f"DEBUG: Worker Parent nach moveToThread: {self.extractor_worker.parent()}")
        self.add_log(f"DEBUG: Worker Thread nach moveToThread: {self.extractor_worker.thread()}")


        # Verbinde Signale und Slots
        self.extractor_thread.started.connect(self.extractor_worker.do_extraction)
        
        self.extractor_worker.progress_update.connect(self.update_progress)
        # Verwende Qt.QueuedConnection für die finalen Signale, um sicherzustellen, dass sie im GUI-Thread verarbeitet werden
        # bevor der Thread beendet wird. Dies ist oft robuster als DirectConnection für cross-thread signals.
        self.extractor_worker.extraction_finished.connect(self.handle_extraction_finished, Qt.ConnectionType.QueuedConnection)
        self.extractor_worker.extraction_error.connect(self.handle_extraction_error, Qt.ConnectionType.QueuedConnection)
        
        # WICHTIG: Bereinigung des Workers und des Threads
        # Verbinde die Beendigungssignale des Workers mit dem quit-Signal des Threads
        self.extractor_worker.extraction_finished.connect(self.extractor_thread.quit)
        self.extractor_worker.extraction_error.connect(self.extractor_thread.quit)
        
        # Verbinde das finished-Signal des Threads mit der deleteLater-Methode des Workers und des Threads selbst
        # Dies stellt sicher, dass die Objekte erst gelöscht werden, wenn der Thread vollständig beendet ist.
        self.extractor_thread.finished.connect(self.extractor_worker.deleteLater)
        self.extractor_thread.finished.connect(self.extractor_thread.deleteLater)
        
        # NEU: Verbinde das finished-Signal des Threads mit der Methode zur Bereinigung der Python-Referenzen
        self.extractor_thread.finished.connect(self._on_thread_fully_finished)

        self.extractor_thread.start()

    def update_progress(self, value: int, message: str):
        """Aktualisiert den Fortschrittsbalken und die Log-Konsole."""
        self.progress_bar.setValue(value)
        self.add_log(message)

    def handle_extraction_finished(self, data: list, kultur: str, siedlungstyp_fuer_dateiname: str):
        """
        Wird aufgerufen, wenn die Extraktion abgeschlossen ist.
        Speichert die Daten und reaktiviert den Start-Button.
        """
        self.add_log(f"Extraktion abgeschlossen. {len(data)} Einträge gefunden.")
        if data:
            self.save_to_json(data, kultur, siedlungstyp_fuer_dateiname)
        else:
            self.add_log("Keine Daten zum Speichern vorhanden.")
        
        self.start_button.setEnabled(True)
        # ENTFERNT: Referenzen auf Worker und Thread werden NICHT hier auf None gesetzt
        # Dies geschieht nun in _on_thread_fully_finished, wenn der Thread wirklich beendet ist.


    def handle_extraction_error(self, error_message: str):
        """
        Wird aufgerufen, wenn ein Fehler während der Extraktion auftritt.
        Zeigt eine Fehlermeldung an und reaktiviert den Start-Button.
        """
        self.add_log(f"Fehler bei der Extraktion: {error_message}")
        QMessageBox.critical(self, "Extraktionsfehler", error_message)
        
        self.start_button.setEnabled(True)
        # ENTFERNT: Referenzen auf Worker und Thread werden NICHT hier auf None gesetzt
        # Dies geschieht nun in _on_thread_fully_finished, wenn der Thread wirklich beendet ist.

    def _on_thread_fully_finished(self):
        """
        Diese Methode wird aufgerufen, wenn der QThread sein 'finished'-Signal sendet.
        Sie ist der letzte Schritt der Bereinigung und setzt die Python-Referenzen auf None.
        """
        self.add_log("DEBUG: Thread hat finished-Signal gesendet. Bereinige Python-Referenzen.")
        self.extractor_worker = None
        self.extractor_thread = None


    def save_to_json(self, daten: list, kultur: str, siedlungstyp_fuer_dateiname: str):
        """
        Speichert die extrahierten Daten in einer JSON-Datei.
        """
        dateiname = f"{kultur.lower()}_{siedlungstyp_fuer_dateiname}.json"
        try:
            with open(dateiname, 'w', encoding='utf-8') as f:
                json.dump(daten, f, indent=4, ensure_ascii=False)
            self.add_log(f"Daten erfolgreich in '{dateiname}' gespeichert.")
        except IOError as e:
            self.add_log(f"Fehler beim Speichern der Daten in '{dateiname}': {e}")
            QMessageBox.critical(self, "Speicherfehler", f"Fehler beim Speichern der Daten: {e}")

# --- Hauptausführung ---

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ExtractorGUI()
    window.show()
    sys.exit(app.exec())
